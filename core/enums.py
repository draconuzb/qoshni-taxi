from enum import Enum


class UserRole(str, Enum):
    USER = "user"
    DRIVER = "driver"


class DriverStatus(str, Enum):
    VERIFIED = "verified"
    BLOCKED = "blocked"


class TripDirection(str, Enum):
    A_TO_B = "a_to_b"
    B_TO_A = "b_to_a"


class TripStatus(str, Enum):
    COLLECTING = "collecting"
    DEPARTED = "departed"
    CANCELLED = "cancelled"


class BookingStatus(str, Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
