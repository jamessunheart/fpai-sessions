"""
Task Automation Framework - Data Models
"""

from enum import Enum
from datetime import datetime
from typing import Optional, Dict, List
from pydantic import BaseModel, Field


class TaskType(str, Enum):
    """Types of tasks the system can handle"""
    SERVICE_SIGNUP = "service_signup"
    DNS_CONFIGURATION = "dns_configuration"
    EMAIL_VERIFICATION = "email_verification"
    API_INTEGRATION = "api_integration"
    ACCOUNT_CONFIGURATION = "account_configuration"
    FORM_SUBMISSION = "form_submission"
    GENERIC = "generic"


class TaskStatus(str, Enum):
    """Task lifecycle states"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AutomationLevel(str, Enum):
    """Level of automation possible"""
    FULL = "full"  # No human intervention needed
    SEMI = "semi"  # Human approval/verification required
    MANUAL = "manual"  # Must be done by human


class BlockerType(str, Enum):
    """Types of blockers that prevent automation"""
    CAPTCHA = "captcha"
    EMAIL_VERIFICATION = "email_verification"
    PHONE_VERIFICATION = "phone_verification"
    HUMAN_APPROVAL = "human_approval"
    API_KEY_REQUIRED = "api_key_required"
    SUPPORT_TICKET = "support_ticket"
    PAYMENT_REQUIRED = "payment_required"


class Task(BaseModel):
    """Core task model"""
    id: str = Field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))
    type: TaskType
    service: str  # Service name (e.g., "sendgrid", "mailgun")
    description: str
    status: TaskStatus = TaskStatus.PENDING
    automation_level: Optional[AutomationLevel] = None
    blocker: Optional[BlockerType] = None
    blocker_details: Optional[str] = None
    assigned_to: str = "ai_agent"  # ai_agent, human, hybrid
    priority: int = 5  # 1-10, 10 being highest
    params: Dict = Field(default_factory=dict)
    result: Optional[Dict] = None
    credentials: Optional[Dict] = None  # Will be stored encrypted
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    logs: List[str] = Field(default_factory=list)

    class Config:
        use_enum_values = True

    def add_log(self, message: str):
        """Add timestamped log entry"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.logs.append(f"[{timestamp}] {message}")

    def mark_in_progress(self):
        """Mark task as in progress"""
        self.status = TaskStatus.IN_PROGRESS
        self.started_at = datetime.now()
        self.add_log("Task started")

    def mark_blocked(self, blocker: BlockerType, details: str):
        """Mark task as blocked"""
        self.status = TaskStatus.BLOCKED
        self.blocker = blocker
        self.blocker_details = details
        self.add_log(f"Task blocked: {blocker.value} - {details}")

    def mark_completed(self, result: Dict):
        """Mark task as completed"""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()
        self.result = result
        self.add_log("Task completed successfully")

    def mark_failed(self, error: str):
        """Mark task as failed"""
        self.status = TaskStatus.FAILED
        self.error_message = error
        self.add_log(f"Task failed: {error}")


class ServiceConfig(BaseModel):
    """Configuration for a service integration"""
    name: str
    signup_automation: AutomationLevel
    api_available: bool
    cli_tool: bool
    difficulty: str  # EASY, MEDIUM, HARD
    blockers: List[BlockerType] = Field(default_factory=list)
    signup_url: Optional[str] = None
    api_docs_url: Optional[str] = None
    notes: Optional[str] = None


class TaskAnalysis(BaseModel):
    """AI analysis of a task"""
    task_id: str
    can_automate: bool
    automation_level: AutomationLevel
    estimated_difficulty: str
    estimated_time_minutes: int
    blockers_identified: List[BlockerType] = Field(default_factory=list)
    recommended_approach: str
    steps: List[str] = Field(default_factory=list)
    requirements: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)


class HumanAction(BaseModel):
    """Action required from human"""
    task_id: str
    action_type: str  # "verification", "approval", "input", "captcha"
    description: str
    instructions: str
    url: Optional[str] = None
    screenshot_path: Optional[str] = None
    completed: bool = False
    completed_at: Optional[datetime] = None
    result: Optional[str] = None
