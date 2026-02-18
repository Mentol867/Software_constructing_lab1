from enum import Enum

class UserRole(Enum):
    ADMIN = 'admin'
    MANAGER = 'manager'
    USER = 'user'

class BookingStatus(Enum):
    NEW = 'New'
    CONFIRMED = 'Confirmed'
    CANCELED = 'Canceled' # Spelling matches usage in booking_service.py
    COMPLETED = 'Completed'

class CarStatus(Enum):
    AVAILABLE = 'Available'
    MAINTENANCE = 'Maintenance'
    BOOKED = 'Booked'
