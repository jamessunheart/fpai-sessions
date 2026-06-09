from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
from enum import Enum
import uuid


class Mode(str, Enum):
    BUILD = "build"
    EARN = "earn"
    CONNECT = "connect"
    RESTORE = "restore"


class Lane(str, Enum):
    TREASURY = "treasury"
    BUILD = "build"
    PROMOTION = "promotion"
    LOVE = "love"


class TicketStatus(str, Enum):
    BACKLOG = "backlog"
    IN_PROGRESS = "in_progress"
    VERIFY = "verify"
    DONE = "done"


class RelationshipHealth(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class TeamRole(str, Enum):
    COS = "chief_of_staff"
    OPS = "ops_builder"
    TREASURY = "treasury_operator"
    MEDIA = "media_operator"


class Condition(BaseModel):
    sleep: int = Field(ge=1, le=10)
    body: int = Field(ge=1, le=10)
    mind: int = Field(ge=1, le=10)


class MorningRitual(BaseModel):
    condition: Condition
    mode: Mode
    primary_lane: Lane
    supporting_lane: Lane
    outcome: str
    next_step: str
    completed_at: Optional[str] = None


class ContentTriad(BaseModel):
    clarity_transmission: bool = False
    proof_post: bool = False
    invitation: bool = False


class SunsetClose(BaseModel):
    wins: str = ""
    tomorrow_outcome: str = ""
    content: ContentTriad = ContentTriad()
    deep_work_minutes: int = 0
    golden_hour_logged: bool = False
    completed_at: Optional[str] = None


class DayRecord(BaseModel):
    date: str
    morning: Optional[MorningRitual] = None
    sunset: Optional[SunsetClose] = None
    tickets_shipped: int = 0
    day_complete: bool = False


class Ticket(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str
    definition_of_done: str = ""
    proof_artifact: str = ""
    verifier: str = ""
    time_estimate: str = ""
    status: TicketStatus = TicketStatus.BACKLOG
    lane: Lane = Lane.BUILD
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None


class RiskTier(BaseModel):
    stable_pct: float = 0
    growth_pct: float = 0
    moonshot_pct: float = 0


class FinancialSnapshot(BaseModel):
    runway_months: float = 0
    yield_week: float = 0
    yield_month: float = 0
    liquid_reserves: float = 0
    exposure: RiskTier = RiskTier()
    moonshot_cap_pct: float = 5.0
    red_flags: list[str] = []
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class RevenueEngine(BaseModel):
    offer_name: str = ""
    deliverable: str = ""
    price: float = 0
    leads: int = 0
    calls: int = 0
    sales: int = 0
    goal_sales: int = 3
    has_landing_page: bool = False
    has_intake_form: bool = False
    has_sales_script: bool = False


class TeamMember(BaseModel):
    role: TeamRole
    assigned_to: str = ""
    current_focus: str = ""
    open_tasks: int = 0
    last_active: str = ""


class RelationshipEntry(BaseModel):
    name: str
    health: RelationshipHealth = RelationshipHealth.GREEN
    last_golden_hour: Optional[str] = None
    pending_repair: bool = False


class OverseerWeek(BaseModel):
    week: int = Field(ge=1, le=4)
    focus: str
    tasks: list[str] = []
    completed: list[bool] = []


class Config(BaseModel):
    deep_work_minutes: int = 35
    revenue_engine: RevenueEngine = RevenueEngine()
    team: list[TeamMember] = []
    relationships: list[RelationshipEntry] = []
    overseer_plan: list[OverseerWeek] = []
    sanctuary_checklist: list[str] = [
        "One desk cleared", "Single device only",
        "No clutter visible", "Ritual playlist on"
    ]
    temple_checklist: list[str] = [
        "No screens", "Low light set",
        "Breathwork done", "Sleep priority set"
    ]
