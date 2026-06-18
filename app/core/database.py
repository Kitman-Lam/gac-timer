import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from app.core.models import (
    AppSetting,
    Meeting,
    MeetingTemplate,
    MeetingTopic,
    PhaseRecord,
    TemplateTopic,
)


class DatabaseManager:
    _instance: Optional["DatabaseManager"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_path: Optional[str] = None):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True

        if db_path is None:
            # 优先使用 LOCALAPPDATA（用户有完全读写权限）
            localappdata_env = os.environ.get("LOCALAPPDATA")
            print(f"[DB INIT] LOCALAPPDATA env: {localappdata_env}")
            if localappdata_env:
                appdata = Path(localappdata_env) / "会帮手"
                print(f"[DB INIT] Using LOCALAPPDATA path: {appdata}")
            else:
                # 兜底使用 APPDATA
                appdata_env = os.environ.get("APPDATA")
                print(f"[DB INIT] LOCALAPPDATA not found, falling back to APPDATA: {appdata_env}")
                if appdata_env:
                    appdata = Path(appdata_env) / "会帮手"
                else:
                    appdata = Path.home() / "AppData" / "Local" / "会帮手"

            try:
                appdata.mkdir(parents=True, exist_ok=True)
                print(f"[DB INIT] Created appdata dir: {appdata}")
            except Exception as e:
                print(f"[DB INIT] Failed to create appdata dir: {e}")
                # 最后兜底：用户目录
                appdata = Path.home() / "会帮手"
                print(f"[DB INIT] Trying user home fallback: {appdata}")
                try:
                    appdata.mkdir(parents=True, exist_ok=True)
                except Exception as e2:
                    print(f"[DB INIT] Home fallback also failed: {e2}")
        else:
            appdata = Path(db_path).parent
            appdata.mkdir(parents=True, exist_ok=True)

        if db_path is None:
            self._db_path = str(appdata / "gac_timer.db")
        else:
            self._db_path = db_path
        print(f"[DB INIT] Final db_path: {self._db_path}")

        self._local = None
        self._create_tables()

    @contextmanager
    def _get_connection(self):
        import sys
        print(f"[DB] Attempting to connect to: {self._db_path}")
        db_dir = os.path.dirname(self._db_path)
        print(f"[DB] DB directory: {db_dir}")
        print(f"[DB] Directory exists: {os.path.exists(db_dir)}")
        print(f"[DB] Is directory: {os.path.isdir(db_dir)}")
        if os.path.exists(db_dir):
            print(f"[DB] Directory writable: {os.access(db_dir, os.W_OK)}")

        try:
            os.makedirs(db_dir, exist_ok=True)
            print(f"[DB] Directory ensured/created")
        except Exception as e:
            print(f"[DB] Cannot create directory: {e}")

        try:
            conn = sqlite3.connect(self._db_path, timeout=30)
            print(f"[DB] Connection established")
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.row_factory = sqlite3.Row
        except Exception as e:
            print(f"[DB ERROR] Cannot connect: {e}")
            raise
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
            print(f"[DB] Connection closed")

    def _create_tables(self):
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS meeting_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS template_topics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    template_id INTEGER NOT NULL,
                    sort_order INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    presentation_minutes INTEGER NOT NULL DEFAULT 10,
                    qa_minutes INTEGER NOT NULL DEFAULT 10,
                    FOREIGN KEY (template_id) REFERENCES meeting_templates(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS meetings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'draft',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    current_topic_index INTEGER DEFAULT 0,
                    current_phase TEXT DEFAULT 'presentation'
                );

                CREATE TABLE IF NOT EXISTS meeting_topics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    meeting_id INTEGER NOT NULL,
                    sort_order INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    presentation_minutes INTEGER NOT NULL,
                    qa_minutes INTEGER NOT NULL,
                    FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS phase_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic_id INTEGER NOT NULL,
                    phase TEXT NOT NULL,
                    planned_seconds INTEGER NOT NULL,
                    actual_seconds REAL NOT NULL DEFAULT 0,
                    overtime_seconds REAL NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'pending',
                    started_at TEXT,
                    paused_at TEXT,
                    completed_at TEXT,
                    paused_elapsed REAL NOT NULL DEFAULT 0,
                    FOREIGN KEY (topic_id) REFERENCES meeting_topics(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
            """)
        # 初始化默认配置（保证新默认值生效）
        self._init_default_settings()

    def _init_default_settings(self):
        """确保所有默认配置都正确写入数据库（但不会覆盖用户已有配置）"""
        import json
        
        # 新的默认值
        new_default_times = {
            "presentation_minutes": 10,
            "qa_minutes": 10,
        }
        new_default_sounds = {
            "warning": "custom_TPBTLOW",
            "warning_minutes": 3,
            "timeup": "custom_over",
            "timeup_scope_qa": False,
            "timeup_scope_presentation": True,
            "overtime": "voice",
            "overtime_minutes": 5,
            "overtime_scope_qa": True,
            "overtime_scope_presentation": False,
            "overtime_voice_text": "已进行",
        }
        new_default_display = {
            "opacity": 85,
            "float_size": "medium",
            "show_topic_name": True,
        }
        
        # 检查是否需要升级默认配置
        # 如果 schema_version 不存在或者小于 1.25，说明是旧版本，强制更新默认值
        schema_version = self.get_setting("schema_version")
        
        # 判断是否需要升级
        should_upgrade = (
            not schema_version or 
            float(schema_version) < 1.25
        )
        
        if should_upgrade:
            # 这次：直接强制更新所有默认值！不保留旧的！
            self.set_setting("defaults", json.dumps(new_default_times))
            self.set_setting("sounds", json.dumps(new_default_sounds))
            self.set_setting("display", json.dumps(new_default_display))
        
        # 设置 schema 版本（下次我们可以用这个检测是否需要升级配置）
        self.set_setting("schema_version", "1.25")
    
    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def create_meeting(self, name: str, status: str = "draft") -> Meeting:
        now = self._now_iso()
        with self._get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO meetings (name, status, created_at, updated_at, current_topic_index, current_phase) VALUES (?, ?, ?, ?, 0, 'presentation')",
                (name, status, now, now),
            )
            return Meeting(
                id=cursor.lastrowid,
                name=name,
                status=status,
                created_at=now,
                updated_at=now,
                current_topic_index=0,
                current_phase="presentation",
            )

    def get_meeting(self, meeting_id: int) -> Optional[Meeting]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,)).fetchone()
            if row is None:
                return None
            return Meeting(**dict(row))

    def update_meeting(self, meeting: Meeting) -> None:
        now = self._now_iso()
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE meetings SET name = ?, status = ?, updated_at = ?, current_topic_index = ?, current_phase = ? WHERE id = ?",
                (meeting.name, meeting.status, now, meeting.current_topic_index, meeting.current_phase, meeting.id),
            )

    def delete_meeting(self, meeting_id: int) -> None:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM meetings WHERE id = ?", (meeting_id,))

    def list_meetings(self, status: Optional[str] = None) -> List[Meeting]:
        with self._get_connection() as conn:
            if status is not None:
                rows = conn.execute("SELECT * FROM meetings WHERE status = ? ORDER BY created_at DESC", (status,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM meetings ORDER BY created_at DESC").fetchall()
            return [Meeting(**dict(r)) for r in rows]

    def create_topic(self, meeting_id: int, sort_order: int, name: str, presentation_minutes: int = 10, qa_minutes: int = 5) -> MeetingTopic:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO meeting_topics (meeting_id, sort_order, name, presentation_minutes, qa_minutes) VALUES (?, ?, ?, ?, ?)",
                (meeting_id, sort_order, name, presentation_minutes, qa_minutes),
            )
            return MeetingTopic(
                id=cursor.lastrowid,
                meeting_id=meeting_id,
                sort_order=sort_order,
                name=name,
                presentation_minutes=presentation_minutes,
                qa_minutes=qa_minutes,
            )

    def get_topics_by_meeting(self, meeting_id: int) -> List[MeetingTopic]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM meeting_topics WHERE meeting_id = ? ORDER BY sort_order", (meeting_id,)).fetchall()
            return [MeetingTopic(**dict(r)) for r in rows]

    def update_topic(self, topic: MeetingTopic) -> None:
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE meeting_topics SET sort_order = ?, name = ?, presentation_minutes = ?, qa_minutes = ? WHERE id = ?",
                (topic.sort_order, topic.name, topic.presentation_minutes, topic.qa_minutes, topic.id),
            )

    def delete_topic(self, topic_id: int) -> None:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM meeting_topics WHERE id = ?", (topic_id,))

    def reorder_topics(self, meeting_id: int, topic_ids: List[int]) -> None:
        with self._get_connection() as conn:
            for order, tid in enumerate(topic_ids):
                conn.execute("UPDATE meeting_topics SET sort_order = ? WHERE id = ? AND meeting_id = ?", (order, tid, meeting_id))

    def create_phase_record(self, topic_id: int, phase: str, planned_seconds: int) -> PhaseRecord:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO phase_records (topic_id, phase, planned_seconds, actual_seconds, overtime_seconds, status, started_at, paused_at, completed_at, paused_elapsed) VALUES (?, ?, ?, 0, 0, 'pending', NULL, NULL, NULL, 0)",
                (topic_id, phase, planned_seconds),
            )
            return PhaseRecord(
                id=cursor.lastrowid,
                topic_id=topic_id,
                phase=phase,
                planned_seconds=planned_seconds,
            )

    def get_phase_records_by_topic(self, topic_id: int) -> List[PhaseRecord]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM phase_records WHERE topic_id = ?", (topic_id,)).fetchall()
            return [PhaseRecord(**dict(r)) for r in rows]

    def update_phase_record(self, record: PhaseRecord) -> None:
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE phase_records SET actual_seconds = ?, overtime_seconds = ?, status = ?, started_at = ?, paused_at = ?, completed_at = ?, paused_elapsed = ? WHERE id = ?",
                (record.actual_seconds, record.overtime_seconds, record.status, record.started_at, record.paused_at, record.completed_at, record.paused_elapsed, record.id),
            )

    def get_phase_records_by_meeting(self, meeting_id: int) -> List[PhaseRecord]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT pr.* FROM phase_records pr JOIN meeting_topics mt ON pr.topic_id = mt.id WHERE mt.meeting_id = ?",
                (meeting_id,),
            ).fetchall()
            return [PhaseRecord(**dict(r)) for r in rows]

    def create_template(self, name: str) -> MeetingTemplate:
        now = self._now_iso()
        with self._get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO meeting_templates (name, created_at, updated_at) VALUES (?, ?, ?)",
                (name, now, now),
            )
            return MeetingTemplate(id=cursor.lastrowid, name=name, created_at=now, updated_at=now)

    def get_template(self, template_id: int) -> Optional[MeetingTemplate]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM meeting_templates WHERE id = ?", (template_id,)).fetchone()
            if row is None:
                return None
            return MeetingTemplate(**dict(row))

    def list_templates(self) -> List[MeetingTemplate]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM meeting_templates ORDER BY created_at DESC").fetchall()
            return [MeetingTemplate(**dict(r)) for r in rows]

    def template_name_exists(self, name: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM meeting_templates WHERE name = ?", (name,)
            )
            return cursor.fetchone()[0] > 0

    def delete_template(self, template_id: int) -> None:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM meeting_templates WHERE id = ?", (template_id,))

    def update_template(self, template_id: int, name: str) -> None:
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE meeting_templates SET name = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
                (name, template_id),
            )

    def create_template_topic(self, template_id: int, sort_order: int, name: str, presentation_minutes: int = 10, qa_minutes: int = 5) -> TemplateTopic:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO template_topics (template_id, sort_order, name, presentation_minutes, qa_minutes) VALUES (?, ?, ?, ?, ?)",
                (template_id, sort_order, name, presentation_minutes, qa_minutes),
            )
            return TemplateTopic(
                id=cursor.lastrowid,
                template_id=template_id,
                sort_order=sort_order,
                name=name,
                presentation_minutes=presentation_minutes,
                qa_minutes=qa_minutes,
            )

    def get_template_topics(self, template_id: int) -> List[TemplateTopic]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM template_topics WHERE template_id = ? ORDER BY sort_order", (template_id,)).fetchall()
            return [TemplateTopic(**dict(r)) for r in rows]

    def delete_template_topics(self, template_id: int) -> None:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM template_topics WHERE template_id = ?", (template_id,))

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
            if row is None:
                return default
            return row["value"]

    def set_setting(self, key: str, value: str) -> None:
        with self._get_connection() as conn:
            conn.execute("INSERT INTO app_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = ?", (key, value, value))
