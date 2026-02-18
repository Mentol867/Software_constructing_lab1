from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps
import os
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.getenv('SECRET_KEY')

from models import db, User, Car, Booking, Review, Maintenance

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def role_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in roles:
                flash('Доступ заборонено. Недостатньо прав.', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/')
def index():
    try:
        from services.ranking_service import calculate_popular_cars
        
        all_cars = Car.query.all()
        all_reviews = Review.query.all()
        
        popular_cars = calculate_popular_cars(all_cars, all_reviews, limit=4)
    except Exception as e:
        print(f"Помилка при розрахунку популярних автомобілів: {e}")
        popular_cars = Car.query.limit(4).all()
        
    return render_template('index.html', cars=popular_cars)

@app.route('/cars')
def cars():
    class_filter = request.args.get('class')
    query = Car.query.filter(Car.status != 'Maintenance') 
    
    if class_filter and class_filter != 'Всі':
        query = query.filter_by(car_class=class_filter)
        
    all_cars = query.all()
    
    today = datetime.now().date()
    for car in all_cars:
        active_booking = Booking.query.filter(
            Booking.car_id == car.id,
            Booking.status == 'Confirmed',
            Booking.start_date <= today,
            Booking.end_date >= today
        ).first()
        car.is_booked_now = True if active_booking else False
    
    return render_template('fleet.html', cars=all_cars, current_filter=class_filter)

@app.route('/car/<int:car_id>')
def car_details(car_id):
    car = Car.query.get_or_404(car_id)
    
    reviews = Review.query.filter_by(car_id=car.id).order_by(Review.created_at.desc()).all()
    avg_rating = 0
    if reviews:
        avg_rating = round(sum(r.rating for r in reviews) / len(reviews), 1)
        
    return render_template('car_details.html', car=car, reviews=reviews, avg_rating=avg_rating)

@app.route('/booking/<int:car_id>', methods=['GET', 'POST'])
def booking(car_id):
    car = Car.query.get_or_404(car_id)
    if request.method == 'POST':
        if not current_user.is_authenticated:
            flash('Ви не авторизовані, логінуйтесь.', 'warning')
            return redirect(url_for('login', next=request.url))

        from services.booking_service import process_booking
        success, result = process_booking(current_user.id, car, request.form)
        
        if success:
             return redirect(url_for('success'))
        else:
             flash(result, 'danger')
             return render_template('booking.html', car=car)

    today_str = datetime.now().strftime('%Y-%m-%d')
    return render_template('booking.html', car=car, today=today_str)

@app.route('/success')
def success():
    return render_template('success.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        from services.auth_service import authenticate_user
        success, message, user = authenticate_user(request.form['email'], request.form['password'])
        
        if success:
            login_user(user)
            flash(message, 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash(message, 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        from services.auth_service import register_user
        success, message, user = register_user(request.form)
        
        if success:
            login_user(user)
            flash(message, 'success')
            return redirect(url_for('dashboard'))
        else:
            flash(message, 'warning' if 'вже' in message else 'danger')
            return render_template('register.html')
            
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Ви вийшли з системи.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.start_date.desc()).all()
    return render_template('dashboard.html', bookings=bookings)

@app.route('/review/add/<int:booking_id>', methods=['POST'])
@login_required
def add_review(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    from services.review_service import create_review
    success, message = create_review(current_user.id, booking, request.form)
    
    if success:
        flash(message, 'Успіх')
    else:
        flash(message, 'Помилка')
        
    return redirect(url_for('dashboard'))

@app.route('/manage/cars')
@login_required
@role_required(['admin', 'manager'])
def manage_cars():
    cars = Car.query.all()
    return render_template('manage_cars.html', cars=cars)

app.config['UPLOAD_FOLDER'] = 'static/uploads/cars'
import os
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

@app.route('/manage/car/add', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager'])
def add_car():
    if request.method == 'POST':
        from services.car_service import create_car
        success, result = create_car(request.form, request.files, app.config['UPLOAD_FOLDER'])
        
        if success:
            flash('Автомобіль успішно додано!', 'Успіх')
            return redirect(url_for('manage_cars'))
        else:
            flash(f'Помилка додавання автомобіля: {result}', 'Помилка')

    return render_template('edit_car.html', car=None)

@app.route('/manage/car/edit/<int:car_id>', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager'])
def edit_car(car_id):
    car = Car.query.get_or_404(car_id)
    if request.method == 'POST':
        from services.car_service import update_car
        success, result = update_car(car, request.form, request.files, app.config['UPLOAD_FOLDER'])
        
        if success:
             flash('Автомобіль успішно оновлено!', 'Успіх')
             return redirect(url_for('manage_cars'))
        else:
             flash(f'Помилка оновлення автомобіля: {result}', 'Помилка')
            
    return render_template('edit_car.html', car=car)

@app.route('/manage/bookings')
@login_required
@role_required(['manager'])
def manage_bookings():
    filter_status = request.args.get('status')
    if filter_status:
        bookings = Booking.query.filter_by(status=filter_status).order_by(Booking.start_date.desc()).all()
    else:
        bookings = Booking.query.order_by(Booking.start_date.desc()).all()
    today = datetime.now().date()
    return render_template('manage_bookings.html', bookings=bookings, today=today)

@app.route('/manage/booking/update/<int:booking_id>/<action>')
@login_required
@role_required(['manager'])
def update_booking_status(booking_id, action):
    booking = Booking.query.get_or_404(booking_id)
    from services.booking_service import update_booking_status
    success, message, category = update_booking_status(booking, action)
    flash(message, category)
    
    db.session.commit()
    return redirect(url_for('manage_bookings'))

@app.route('/manage/users')
@login_required
@role_required(['admin'])
def manage_users():
    users = User.query.order_by(User.id).all()
    return render_template('manage_users.html', users=users)

@app.route('/manage/user/<int:user_id>/role', methods=['POST'])
@login_required
@role_required(['admin'])
def update_user_role(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Ви не можете змінити власну роль.', 'warning')
        return redirect(url_for('manage_users'))
        
    new_role = request.form.get('role')
    if new_role in ['user', 'manager', 'admin']:
        user.role = new_role
        db.session.commit()
        flash(f'Роль для {user.username} оновлено на {new_role}.', 'success')
    else:
        flash('Вибрано недійсну роль.', 'danger')
    return redirect(url_for('manage_users'))

@app.route('/manage/user/<int:user_id>/block/<action>')
@login_required
@role_required(['admin'])
def toggle_user_block(user_id, action):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Ви не можете заблокувати самого себе.', 'warning')
        return redirect(url_for('manage_users'))

    if action == 'block':
        user.is_blocked = True
        flash(f'Користувача {user.username} заблоковано.', 'danger')
    elif action == 'unblock':
        user.is_blocked = False
        flash(f'Користувача {user.username} розблоковано.', 'success')
    
    db.session.commit()
    return redirect(url_for('manage_users'))

@app.route('/manage/statistics')
@login_required
@role_required(['admin'])
def statistics():
    from services.statistics_service import get_statistics_context
    context = get_statistics_context(request.args)
    return render_template('statistics.html', **context)

@app.route('/manage/maintenance')
@login_required
@role_required(['admin', 'manager'])
def manage_maintenance():
    car_id = request.args.get('car_id')
    if car_id:
        records = Maintenance.query.filter_by(car_id=car_id).order_by(Maintenance.date.desc()).all()
        selected_car = Car.query.get(car_id)
    else:
        records = Maintenance.query.order_by(Maintenance.date.desc()).all()
        selected_car = None
    
    cars = Car.query.all()
    return render_template('manage_maintenance.html', records=records, cars=cars, selected_car=selected_car)

@app.route('/manage/maintenance/add', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager'])
def add_maintenance():
    if request.method == 'POST':
        try:
            car_id = int(request.form['car_id'])
            date_str = request.form['date']
            description = request.form['description']
            cost = float(request.form['cost'])
            
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            record = Maintenance(
                car_id=car_id,
                date=date,
                description=description,
                cost=cost
            )
            db.session.add(record)
            db.session.commit()
            flash('Запис про обслуговування додано!', 'success')
            return redirect(url_for('manage_maintenance', car_id=car_id))
        except Exception as e:
            flash(f'Помилка: {str(e)}', 'danger')
    
    cars = Car.query.all()
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('add_maintenance.html', cars=cars, today=today)

@app.route('/manage/maintenance/delete/<int:record_id>')
@login_required
@role_required(['admin'])
def delete_maintenance(record_id):
    record = Maintenance.query.get_or_404(record_id)
    car_id = record.car_id
    db.session.delete(record)
    db.session.commit()
    flash('Запис видалено!', 'success')
    return redirect(url_for('manage_maintenance', car_id=car_id))

@app.route('/manage/car/delete/<int:car_id>')
@login_required
@role_required(['admin'])
def delete_car(car_id):
    car = Car.query.get_or_404(car_id)
    from services.car_service import delete_car
    success, message = delete_car(car)
    flash('Автомобіль успішно видалено!', 'success' if success else 'danger')
    return redirect(url_for('manage_cars'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)