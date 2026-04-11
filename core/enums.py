from enum import Enum


class UserRole(str, Enum):
    USER = "user"
    DRIVER = "driver"
    DISPATCHER = "dispatcher"
    MANAGER = "manager"


class DriverStatus(str, Enum):
    PENDING_VERIFICATION = "pending_verification"
    VERIFIED = "verified"
    REJECTED = "rejected"
    BLOCKED = "blocked"


class TripDirection(str, Enum):
    A_TO_B = "a_to_b"   # from_name → to_name
    B_TO_A = "b_to_a"   # to_name → from_name


class TripStatus(str, Enum):
    COLLECTING = "collecting"       # driver waiting at station, accepting bookings
    DEPARTED = "departed"           # driver started moving
    COMPLETED = "completed"         # trip finished
    CANCELLED = "cancelled"


class BookingStatus(str, Enum):
    ACTIVE = "active"
    PICKED_UP = "picked_up"         # driver marked this passenger as picked up
    CANCELLED = "cancelled"


