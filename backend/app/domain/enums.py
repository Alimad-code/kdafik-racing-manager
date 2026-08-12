from enum import StrEnum


class UserRole(StrEnum):
    TEAM_PRINCIPAL = "team-principal"
    RACE_ENGINEER = "race-engineer"
    VIEWER = "viewer"


class SeasonStatus(StrEnum):
    SETUP = "setup"
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"


class StageStatus(StrEnum):
    LOCKED = "locked"
    AVAILABLE = "available"
    COMPLETED = "completed"


class StageSessionType(StrEnum):
    FP1 = "fp1"
    FP2 = "fp2"
    FP3 = "fp3"
    PRACTICE_COMPLETION = "practice-completion"
    QUALIFYING = "qualifying"
    RACE = "race"


class StageSessionStatus(StrEnum):
    LOCKED = "locked"
    AVAILABLE = "available"
    COMPLETED = "completed"


class CarCondition(StrEnum):
    HEALTHY = "healthy"
    DAMAGED = "damaged"
    HEAVILY_DAMAGED = "heavily-damaged"


class BudgetCategory(StrEnum):
    DRIVERS = "drivers"
    TEAM = "team"
    CAR_CONSTRUCTION = "car-construction"
    SETUP = "setup"
    REPAIR = "repair"


class SetupBand(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PracticeSegment(StrEnum):
    FP1 = "fp1"
    FP2 = "fp2"
    FP3 = "fp3"


class PracticeSegmentStatus(StrEnum):
    LOCKED = "locked"
    AVAILABLE = "available"
    COMPLETED = "completed"


class PracticeCompletionStatus(StrEnum):
    LOCKED = "locked"
    AVAILABLE = "available"
    COMPLETED = "completed"


class SessionType(StrEnum):
    PRACTICE = "practice"
    QUALIFYING = "qualifying"
    RACE = "race"


class TrackProfile(StrEnum):
    SPEED = "speed"
    BALANCED = "balanced"
    TECHNICAL = "technical"


class TrackSegmentType(StrEnum):
    STRAIGHT = "straight"
    HIGH_SPEED_CORNER = "high-speed-corner"
    LOW_SPEED_CORNER = "low-speed-corner"
    PIT_LANE = "pit-lane"


class ResultStatus(StrEnum):
    CLASSIFIED = "classified"
    NO_TIME = "no-time"
    DNF = "dnf"
    DNS = "dns"
    DISQUALIFIED = "disqualified"


class RaceEventType(StrEnum):
    CLEAN_RACE = "clean-race"
    DRIVER_MISTAKE = "driver-mistake"
    DAMAGE = "damage"
    DNF = "dnf"
    NO_TIME = "no-time"
    TECHNICAL_ISSUE = "technical-issue"


class EventSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
