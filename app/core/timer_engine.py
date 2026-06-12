import time
from typing import List, Optional

from PySide6.QtCore import QObject, QTimer, Signal

from app.core.database import DatabaseManager
from app.core.models import Meeting, MeetingTopic, PhaseRecord


class TimerEngine(QObject):
    IDLE = "idle"
    COUNTDOWN = "countdown"
    OVERTIME = "overtime"
    PAUSED_CD = "paused_countdown"
    PAUSED_OT = "paused_overtime"

    state_changed = Signal(str)
    overtime_started = Signal()
    warning_threshold_reached = Signal()

    WARNING_THRESHOLD_SECONDS = 30

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = self.IDLE
        self._planned_seconds = 0
        self._accumulated_elapsed = 0.0
        self._segment_start: Optional[float] = None
        self._overtime_triggered = False
        self._warning_triggered = False

    @property
    def state(self) -> str:
        return self._state

    @property
    def planned_seconds(self) -> int:
        return self._planned_seconds

    @property
    def elapsed_seconds(self) -> float:
        if self._state == self.IDLE:
            return 0.0
        if self._segment_start is not None:
            return self._accumulated_elapsed + (time.perf_counter() - self._segment_start)
        return self._accumulated_elapsed

    @property
    def paused_elapsed(self) -> float:
        if self._state in (self.PAUSED_CD, self.PAUSED_OT):
            return self._accumulated_elapsed
        return 0.0

    def start(self, planned_seconds: int):
        self._planned_seconds = planned_seconds
        self._accumulated_elapsed = 0.0
        self._segment_start = time.perf_counter()
        self._overtime_triggered = False
        self._warning_triggered = False
        self._state = self.COUNTDOWN
        self.state_changed.emit(self._state)

    def pause(self):
        if self._state == self.COUNTDOWN:
            self._accumulated_elapsed += time.perf_counter() - self._segment_start
            self._segment_start = None
            self._state = self.PAUSED_CD
            self.state_changed.emit(self._state)
        elif self._state == self.OVERTIME:
            self._accumulated_elapsed += time.perf_counter() - self._segment_start
            self._segment_start = None
            self._state = self.PAUSED_OT
            self.state_changed.emit(self._state)

    def resume(self):
        if self._state == self.PAUSED_CD:
            self._segment_start = time.perf_counter()
            self._state = self.COUNTDOWN
            self.state_changed.emit(self._state)
        elif self._state == self.PAUSED_OT:
            self._segment_start = time.perf_counter()
            self._state = self.OVERTIME
            self.state_changed.emit(self._state)

    def reset(self):
        self._state = self.IDLE
        self._planned_seconds = 0
        self._accumulated_elapsed = 0.0
        self._segment_start = None
        self._overtime_triggered = False
        self._warning_triggered = False
        self.state_changed.emit(self._state)

    def restore_paused(self, planned_seconds: int, elapsed: float):
        self._planned_seconds = planned_seconds
        self._accumulated_elapsed = elapsed
        self._segment_start = None
        self._overtime_triggered = elapsed >= planned_seconds
        self._warning_triggered = (
            elapsed < planned_seconds
            and (planned_seconds - elapsed) <= self.WARNING_THRESHOLD_SECONDS
        )
        if elapsed >= planned_seconds:
            self._state = self.PAUSED_OT
        else:
            self._state = self.PAUSED_CD
        self.state_changed.emit(self._state)

    def tick(self) -> dict:
        if self._state == self.IDLE:
            return {
                "state": self.IDLE,
                "planned_seconds": 0,
                "remaining_seconds": 0.0,
                "overtime_seconds": 0.0,
                "actual_seconds": 0.0,
                "progress": 0.0,
                "is_countdown": False,
                "is_overtime": False,
                "is_paused": False,
            }

        elapsed = self.elapsed_seconds
        remaining = max(0.0, self._planned_seconds - elapsed)
        overtime = max(0.0, elapsed - self._planned_seconds)
        progress = elapsed / self._planned_seconds if self._planned_seconds > 0 else 0.0

        is_countdown = self._state in (self.COUNTDOWN, self.PAUSED_CD)
        is_overtime = self._state in (self.OVERTIME, self.PAUSED_OT)
        is_paused = self._state in (self.PAUSED_CD, self.PAUSED_OT)

        if is_countdown and remaining <= self.WARNING_THRESHOLD_SECONDS and not self._warning_triggered:
            self._warning_triggered = True
            self.warning_threshold_reached.emit()

        if self._state == self.COUNTDOWN and elapsed >= self._planned_seconds:
            self._state = self.OVERTIME
            is_countdown = False
            is_overtime = True
            if not self._overtime_triggered:
                self._overtime_triggered = True
                self.overtime_started.emit()
            self.state_changed.emit(self._state)

        return {
            "state": self._state,
            "planned_seconds": self._planned_seconds,
            "remaining_seconds": remaining,
            "overtime_seconds": overtime,
            "actual_seconds": elapsed,
            "progress": progress,
            "is_countdown": is_countdown,
            "is_overtime": is_overtime,
            "is_paused": is_paused,
        }


class MeetingTimerController(QObject):
    meeting_started = Signal()
    meeting_completed = Signal()
    phase_changed = Signal(int, str)
    timer_updated = Signal(dict)

    AUTO_SAVE_INTERVAL_MS = 5000
    TICK_INTERVAL_MS = 50

    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self._db = db_manager
        self._engine = TimerEngine(self)
        self._current_meeting: Optional[Meeting] = None
        self._current_topics: List[MeetingTopic] = []
        self._current_topic_index = 0
        self._current_phase = "presentation"
        self._current_phase_record: Optional[PhaseRecord] = None
        self._last_save_time: Optional[float] = None

        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(self.TICK_INTERVAL_MS)
        self._tick_timer.timeout.connect(self._on_tick)

    @property
    def engine(self) -> TimerEngine:
        return self._engine

    def start_meeting(self, meeting_id: int):
        meeting = self._db.get_meeting(meeting_id)
        if meeting is None:
            return

        self._current_meeting = meeting
        self._current_meeting.status = "in_progress"
        self._current_meeting.current_topic_index = 0
        self._current_meeting.current_phase = "presentation"
        self._db.update_meeting(self._current_meeting)

        self._current_topics = self._db.get_topics_by_meeting(meeting_id)
        if not self._current_topics:
            return

        self._current_topic_index = 0
        self._current_phase = "presentation"

        self._ensure_phase_records()

        topic = self._current_topics[0]
        planned = topic.presentation_minutes * 60
        self._current_phase_record = self._find_phase_record(topic.id, "presentation")
        if self._current_phase_record:
            self._current_phase_record.status = "in_progress"
            self._current_phase_record.started_at = DatabaseManager._now_iso()
            self._db.update_phase_record(self._current_phase_record)

        self._engine.start(planned)
        self._tick_timer.start()
        print("[DEBUG TimerEngine] _tick_timer started, interval=", self._tick_timer.interval())
        self._last_save_time = time.perf_counter()
        self.meeting_started.emit()
        self.phase_changed.emit(self._current_topic_index, self._current_phase)

    def next_phase(self):
        if self._current_meeting is None:
            return

        self._complete_current_phase_record()

        next_topic_index = self._current_topic_index
        next_phase = self._current_phase

        if self._current_phase == "presentation":
            next_phase = "qa"
        else:
            next_topic_index += 1
            next_phase = "presentation"

        if next_topic_index >= len(self._current_topics):
            self.complete_meeting()
            return

        self._current_topic_index = next_topic_index
        self._current_phase = next_phase

        topic = self._current_topics[self._current_topic_index]
        planned = self._get_planned_seconds(topic, self._current_phase)

        self._current_phase_record = self._find_phase_record(topic.id, self._current_phase)
        if self._current_phase_record:
            if self._current_phase_record.status == "pending":
                self._current_phase_record.status = "in_progress"
                self._current_phase_record.started_at = DatabaseManager._now_iso()
                self._db.update_phase_record(self._current_phase_record)

        self._engine.start(planned)
        self._update_meeting_progress()
        self.phase_changed.emit(self._current_topic_index, self._current_phase)

    def prev_phase(self):
        if self._current_meeting is None:
            return

        self._save_current_phase()

        prev_topic_index = self._current_topic_index
        prev_phase = self._current_phase

        if self._current_phase == "qa":
            prev_phase = "presentation"
        else:
            prev_topic_index -= 1
            if prev_topic_index < 0:
                return
            prev_phase = "qa"

        self._current_topic_index = prev_topic_index
        self._current_phase = prev_phase

        topic = self._current_topics[self._current_topic_index]
        planned = self._get_planned_seconds(topic, self._current_phase)

        self._current_phase_record = self._find_phase_record(topic.id, self._current_phase)
        if self._current_phase_record:
            elapsed = self._current_phase_record.paused_elapsed
            self._current_phase_record.status = "paused"
            self._current_phase_record.paused_at = DatabaseManager._now_iso()
            self._current_phase_record.completed_at = None
            self._db.update_phase_record(self._current_phase_record)
            self._engine.restore_paused(planned, elapsed)
        else:
            self._engine.restore_paused(planned, 0.0)

        self._update_meeting_progress()
        self.phase_changed.emit(self._current_topic_index, self._current_phase)

    def pause_resume(self):
        if self._engine.state in (TimerEngine.COUNTDOWN, TimerEngine.OVERTIME):
            self._engine.pause()
            if self._current_phase_record:
                self._current_phase_record.paused_elapsed = self._engine.paused_elapsed
                self._current_phase_record.status = "paused"
                self._current_phase_record.paused_at = DatabaseManager._now_iso()
                self._db.update_phase_record(self._current_phase_record)
        elif self._engine.state in (TimerEngine.PAUSED_CD, TimerEngine.PAUSED_OT):
            self._engine.resume()
            if self._current_phase_record:
                self._current_phase_record.status = "in_progress"
                self._db.update_phase_record(self._current_phase_record)

    def reset_current_phase(self):
        if not self._current_topics:
            return
        if self._current_topic_index >= len(self._current_topics):
            return

        self._engine.reset()

        if self._current_phase_record:
            self._current_phase_record.actual_seconds = 0.0
            self._current_phase_record.overtime_seconds = 0.0
            self._current_phase_record.paused_elapsed = 0.0
            self._current_phase_record.status = "pending"
            self._current_phase_record.started_at = None
            self._current_phase_record.paused_at = None
            self._current_phase_record.completed_at = None
            self._db.update_phase_record(self._current_phase_record)

    def start_current_phase(self):
        if not self._current_topics:
            return
        if self._current_topic_index >= len(self._current_topics):
            return

        topic = self._current_topics[self._current_topic_index]
        planned = self._get_planned_seconds(topic, self._current_phase)
        self._engine.start(planned)

        if self._current_phase_record:
            self._current_phase_record.status = "in_progress"
            self._current_phase_record.started_at = DatabaseManager._now_iso()
            self._current_phase_record.paused_at = None
            self._current_phase_record.completed_at = None
            self._db.update_phase_record(self._current_phase_record)

    def refresh_topics(self):
        if self._current_meeting is None:
            return
        current_topic_id = None
        if self._current_topics and self._current_topic_index < len(self._current_topics):
            current_topic_id = self._current_topics[self._current_topic_index].id
        self._current_topics = self._db.get_topics_by_meeting(self._current_meeting.id)
        if current_topic_id is not None:
            for i, topic in enumerate(self._current_topics):
                if topic.id == current_topic_id:
                    self._current_topic_index = i
                    break

    def get_current_info(self) -> dict:
        if self._current_meeting is None:
            return {
                "meeting_name": "",
                "topic_name": "",
                "phase": "",
                "topic_index": 0,
                "total_topics": 0,
                "is_active": False,
            }

        topic = (
            self._current_topics[self._current_topic_index]
            if self._current_topics and self._current_topic_index < len(self._current_topics)
            else None
        )

        return {
            "meeting_name": self._current_meeting.name,
            "topic_name": topic.name if topic else "",
            "phase": self._current_phase,
            "topic_index": self._current_topic_index,
            "total_topics": len(self._current_topics),
            "is_active": True,
        }

    def complete_meeting(self):
        if self._current_meeting is None:
            return

        if self._current_phase_record and self._current_phase_record.status != "completed":
            self._complete_current_phase_record()

        self._current_meeting.status = "completed"
        self._db.update_meeting(self._current_meeting)

        self._tick_timer.stop()
        self._engine.reset()

        self._current_meeting = None
        self._current_topics = []
        self._current_topic_index = 0
        self._current_phase = "presentation"
        self._current_phase_record = None

        self.meeting_completed.emit()

    def auto_save(self):
        if self._current_meeting is None:
            return
        self._save_current_phase()
        self._update_meeting_progress()

    def recover_meeting(self, meeting_id: int):
        meeting = self._db.get_meeting(meeting_id)
        if meeting is None or meeting.status != "in_progress":
            return

        self._current_meeting = meeting
        self._current_topics = self._db.get_topics_by_meeting(meeting_id)
        self._current_topic_index = meeting.current_topic_index
        self._current_phase = meeting.current_phase

        if not self._current_topics or self._current_topic_index >= len(self._current_topics):
            return

        topic = self._current_topics[self._current_topic_index]
        planned = self._get_planned_seconds(topic, self._current_phase)

        self._current_phase_record = self._find_phase_record(topic.id, self._current_phase)
        if self._current_phase_record and self._current_phase_record.paused_elapsed > 0:
            self._engine.restore_paused(planned, self._current_phase_record.paused_elapsed)
        else:
            self._engine.start(planned)

        self._tick_timer.start()
        self._last_save_time = time.perf_counter()
        self.phase_changed.emit(self._current_topic_index, self._current_phase)

    def _on_tick(self):
        try:
            tick_data = self._engine.tick()
            self.timer_updated.emit(tick_data)
        except Exception as e:
            print("[DEBUG] _on_tick EXCEPTION:", e)
            import traceback
            traceback.print_exc()

        if self._last_save_time is not None:
            elapsed_ms = (time.perf_counter() - self._last_save_time) * 1000
            if elapsed_ms >= self.AUTO_SAVE_INTERVAL_MS:
                self.auto_save()
                self._last_save_time = time.perf_counter()

    def _save_current_phase(self):
        if self._current_phase_record is None:
            return
        elapsed = self._engine.elapsed_seconds
        overtime = max(0.0, elapsed - self._current_phase_record.planned_seconds)
        self._current_phase_record.actual_seconds = elapsed
        self._current_phase_record.overtime_seconds = overtime
        self._current_phase_record.paused_elapsed = elapsed
        self._db.update_phase_record(self._current_phase_record)

    def _complete_current_phase_record(self):
        if self._current_phase_record is None:
            return
        elapsed = self._engine.elapsed_seconds
        overtime = max(0.0, elapsed - self._current_phase_record.planned_seconds)
        self._current_phase_record.actual_seconds = elapsed
        self._current_phase_record.overtime_seconds = overtime
        self._current_phase_record.paused_elapsed = elapsed
        self._current_phase_record.status = "completed"
        self._current_phase_record.completed_at = DatabaseManager._now_iso()
        self._db.update_phase_record(self._current_phase_record)

    def _update_meeting_progress(self):
        if self._current_meeting is None:
            return
        self._current_meeting.current_topic_index = self._current_topic_index
        self._current_meeting.current_phase = self._current_phase
        self._db.update_meeting(self._current_meeting)

    def _ensure_phase_records(self):
        for topic in self._current_topics:
            for phase in ("presentation", "qa"):
                existing = self._find_phase_record(topic.id, phase)
                if existing is None:
                    planned = self._get_planned_seconds(topic, phase)
                    self._db.create_phase_record(topic.id, phase, planned)

    def _find_phase_record(self, topic_id: int, phase: str) -> Optional[PhaseRecord]:
        records = self._db.get_phase_records_by_topic(topic_id)
        for record in records:
            if record.phase == phase:
                return record
        return None

    @staticmethod
    def _get_planned_seconds(topic: MeetingTopic, phase: str) -> int:
        if phase == "presentation":
            return topic.presentation_minutes * 60
        return topic.qa_minutes * 60
