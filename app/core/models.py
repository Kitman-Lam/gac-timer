from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MeetingTemplate:
    id: Optional[int] = None
    name: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass
class TemplateTopic:
    id: Optional[int] = None
    template_id: int = 0
    sort_order: int = 0
    name: str = ""
    presentation_minutes: int = 10
    qa_minutes: int = 5


@dataclass
class Meeting:
    id: Optional[int] = None
    name: str = ""
    status: str = "draft"
    created_at: str = ""
    updated_at: str = ""
    current_topic_index: int = 0
    current_phase: str = "presentation"


@dataclass
class MeetingTopic:
    id: Optional[int] = None
    meeting_id: int = 0
    sort_order: int = 0
    name: str = ""
    presentation_minutes: int = 10
    qa_minutes: int = 5


@dataclass
class PhaseRecord:
    id: Optional[int] = None
    topic_id: int = 0
    phase: str = "presentation"
    planned_seconds: int = 0
    actual_seconds: float = 0
    overtime_seconds: float = 0
    status: str = "pending"
    started_at: Optional[str] = None
    paused_at: Optional[str] = None
    completed_at: Optional[str] = None
    paused_elapsed: float = 0.0


@dataclass
class AppSetting:
    key: str = ""
    value: str = ""
