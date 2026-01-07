from models import db, Review

def create_review(user_id, booking, form_data):
    if booking.user_id != user_id:
        return False, 'Помилка авторизації.'
        
    if booking.status != 'Completed':
        return False, 'Ви можете залишити відгук лише про завершене бронювання.'
        
    if booking.review:
        return False, 'Ви вже залишили відгук для цього бронювання.'
        
    rating = form_data.get('rating')
    comment = form_data.get('comment')
    
    try:
        rating = int(rating)
        if not (1 <= rating <= 10):
            raise ValueError
    except (TypeError, ValueError):
        return False, 'Оцінка має бути від 1 до 10.'

    new_review = Review(
        user_id=user_id,
        car_id=booking.car_id,
        booking_id=booking.id,
        rating=rating,
        comment=comment
    )
    
    db.session.add(new_review)
    db.session.commit()
    return True, 'Дякуємо за ваш відгук!'
