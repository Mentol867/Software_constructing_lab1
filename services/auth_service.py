import re
from models import db, User

def register_user(form_data):
    username = form_data['username']
    email = form_data['email']
    password = form_data['password']
    
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return False, 'Невірна адреса електронної пошти.', None
    
    if User.query.filter_by(email=email).first():
        return False, 'Електронна пошта вже зареєстрована.', None

    new_user = User(username=username, email=email)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()
    return True, 'Реєстрація успішна! Ласкаво просимо.', new_user

def authenticate_user(email, password):
    user = User.query.filter_by(email=email).first()
    if user and user.check_password(password):
        if user.is_blocked:
             return False, 'Ваш акаунт було заблоковано. Будь ласка, зверніться до служби підтримки.', None
        return True, 'Вхід успішний!', user
    return False, 'Невірна адреса електронної пошти або пароль.', None
