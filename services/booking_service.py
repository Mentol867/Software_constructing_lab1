from datetime import datetime
import re
from models import db, Booking
from enums import BookingStatus, CarStatus

def validate_phone(phone):
    return bool(re.match(r'^\+?[\d\s-]{10,15}$', phone))

def process_booking(user_id, car, form_data):
    start_date_str = form_data['start_date']
    end_date_str = form_data['end_date']
    name = form_data['name']
    phone = form_data['phone']
    
    if not validate_phone(phone):
        return False, 'Невірний формат номера телефону.'
    
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        if start_date < datetime.now().date():
            return False, 'Дата початку не може бути в минулому.'
            
        if end_date <= start_date:
            return False, 'Дата закінчення повинна бути після дати початку.'

        overlapping_bookings = Booking.query.filter(
            Booking.car_id == car.id,
            Booking.status.notin_([BookingStatus.CANCELED.value, BookingStatus.COMPLETED.value]),
            Booking.end_date > start_date,
            Booking.start_date < end_date
        ).first()
        
        if overlapping_bookings:
            return False, 'Автомобіль уже заброньовано на ці дати.'

        days = (end_date - start_date).days
        total_price = days * car.price_per_day

        new_booking = Booking(
            car_id=car.id,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            total_price=total_price,
            customer_name=name,
            customer_phone=phone
        )

        db.session.add(new_booking)
        db.session.commit()
        return True, new_booking
    except ValueError:
            return False, 'Невірний формат дати.'
    except Exception as e:
        return False, str(e)

def update_booking_status(booking, action):
    message = ''
    category = 'success'
    
    if action == 'confirm':
        booking.status = BookingStatus.CONFIRMED.value
        booking.car.status = CarStatus.BOOKED.value
        message = f'Бронювання #{booking.id} підтверджено.'
    elif action == 'cancel':
        booking.status = BookingStatus.CANCELED.value
        booking.car.status = CarStatus.AVAILABLE.value
        message = f'Бронювання #{booking.id} скасовано.'
        category = 'warning'
    elif action == 'complete':
        booking.status = BookingStatus.COMPLETED.value
        booking.car.status = CarStatus.AVAILABLE.value
        message = f'Бронювання #{booking.id} позначено як завершене.'
    else:
        return False, 'Недійсна дія', 'danger'
    
    db.session.commit()
    return True, message, category
