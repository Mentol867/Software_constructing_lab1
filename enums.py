from enum import Enum

class UserRole(Enum):
    ADMIN = 'admin'
    MANAGER = 'manager'
    USER = 'user'

class BookingStatus(Enum):
    NEW = 'New'
    CONFIRMED = 'Confirmed'
    COMPLETED = 'Completed'

class CarStatus(Enum):
    AVAILABLE = 'Available'
    MAINTENANCE = 'Maintenance'
    BOOKED = 'Booked'