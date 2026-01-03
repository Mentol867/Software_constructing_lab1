from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps

app = Flask(__name__)

# Konfiguratsia bazy danykh
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:137948625awD@localhost:5432/flask_db?client_encoding=utf8'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'super_secret_key_for_car_rental' # Dlya sessiy ta flesh povidomlen

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- HELPERS ---

def role_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in roles:
                flash('Access denied. Insufficient permissions.', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- MODELS ---

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='user') # 'admin', 'manager', 'user'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Car(db.Model):
    __tablename__ = 'cars'
    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    price_per_day = db.Column(db.Integer, nullable=False)
    transmission = db.Column(db.String(20), nullable=False) # 'Automatic', 'Manual'
    fuel_type = db.Column(db.String(20), nullable=False) # 'Petrol', 'Diesel', 'Electric'
    seats = db.Column(db.Integer, nullable=False)
    image_url = db.Column(db.String(200), default='https://placehold.co/600x400/1a1a1a/gold?text=Car+Image') # Placeholder
    is_available = db.Column(db.Boolean, default=True)
    description = db.Column(db.Text)
    car_class = db.Column(db.String(50), default='Economy')  # Economy, Business, Premium, SUV
    status = db.Column(db.String(20), default='Available')   # Available, Booked, Maintenance
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=True) 
    
    location = db.relationship('Location', backref='cars')

class Location(db.Model):
    __tablename__ = 'locations'
    id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.String(50), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    max_capacity = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<Location {self.city} - {self.address}>'

class Booking(db.Model):
    __tablename__ = 'bookings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) 
    car_id = db.Column(db.Integer, db.ForeignKey('cars.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='New') # New, Confirmed, Canceled

    user = db.relationship('User', backref='bookings')
    car = db.relationship('Car', backref='bookings')

# --- ROUTES ---

@app.route('/')
def index():
    popular_cars = Car.query.limit(4).all()
    return render_template('index.html', cars=popular_cars)

@app.route('/cars')
def cars():
    class_filter = request.args.get('class')
    query = Car.query.filter(Car.status != 'Maintenance') 
    
    if class_filter and class_filter != 'Всі':
        query = query.filter_by(car_class=class_filter)
        
    all_cars = query.all()
    
    # Check current availability dynamically
    today = datetime.now().date()
    for car in all_cars:
        active_booking = Booking.query.filter(
            Booking.car_id == car.id,
            Booking.status != 'Canceled',
            Booking.start_date <= today,
            Booking.end_date >= today
        ).first()
        car.is_booked_now = True if active_booking else False
    
    return render_template('fleet.html', cars=all_cars, current_filter=class_filter)

@app.route('/car/<int:car_id>')
def car_details(car_id):
    car = Car.query.get_or_404(car_id)
    return render_template('car_details.html', car=car)

@app.route('/booking/<int:car_id>', methods=['GET', 'POST'])
def booking(car_id):
    car = Car.query.get_or_404(car_id)
    if request.method == 'POST':
        if not current_user.is_authenticated:
            flash('Please log in to book a car.', 'warning')
            return redirect(url_for('login', next=request.url))

        start_date_str = request.form['start_date']
        end_date_str = request.form['end_date']
        name = request.form['name']
        phone = request.form['phone']
        
        # Phone validation (simple regex for digits and possible +)
        import re
        if not re.match(r'^\+?[\d\s-]{10,15}$', phone):
             flash('Invalid phone number format.', 'danger')
             return render_template('booking.html', car=car)
        
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
            if start_date < datetime.now().date():
                flash('Start date cannot be in the past.', 'danger')
                return render_template('booking.html', car=car)
                
            if end_date <= start_date:
                flash('End date must be after start date.', 'danger')
                return render_template('booking.html', car=car)

            # Check overlap
            overlapping_bookings = Booking.query.filter(
                Booking.car_id == car.id,
                Booking.status != 'Canceled',
                Booking.end_date > start_date,
                Booking.start_date < end_date
            ).first()
            
            if overlapping_bookings:
                 flash('Car is already booked for these dates.', 'danger')
                 return render_template('booking.html', car=car)

            days = (end_date - start_date).days
            total_price = days * car.price_per_day

            new_booking = Booking(
                car_id=car.id,
                user_id=current_user.id,
                start_date=start_date,
                end_date=end_date,
                total_price=total_price,
                customer_name=name,
                customer_phone=phone
            )
            
            # Optionally update car status to 'Booked' if it's for NOW (this is a bit complex as bookings vary in time)
            # For this simple app, we won't toggle the 'status' column automatically on every booking because a car can be booked for next month.
            # The 'status' column is likely for manual overrides (Maintenance) or immediate status.
            
            db.session.add(new_booking)
            db.session.commit()
            return redirect(url_for('success'))
        except ValueError:
             flash('Invalid date format.', 'danger')

    today_str = datetime.now().strftime('%Y-%m-%d')
    return render_template('booking.html', car=car, today=today_str)

@app.route('/success')
def success():
    return render_template('success.html')

# --- AUTH ROUTES ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('Login successful!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        import re
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash('Invalid email address.', 'danger')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'warning')
        else:
            new_user = User(username=username, email=email)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            flash('Registration successful! Welcome.', 'success')
            return redirect(url_for('dashboard'))
            
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.start_date.desc()).all()
    return render_template('dashboard.html', bookings=bookings)

# --- MANAGER / ADMIN ROUTES ---

@app.route('/manage/cars')
@login_required
@role_required(['admin', 'manager'])
def manage_cars():
    cars = Car.query.all()
    return render_template('manage_cars.html', cars=cars)

app.config['UPLOAD_FOLDER'] = 'static/uploads/cars'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Ensure upload directory exists
import os
from werkzeug.utils import secure_filename

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

@app.route('/manage/car/add', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager'])
def add_car():
    if request.method == 'POST':
        try:
            brand = request.form['brand']
            model = request.form['model']
            year = int(request.form['year'])
            price = int(request.form['price'])
            transmission = request.form['transmission']
            fuel = request.form['fuel']
            seats = int(request.form['seats'])
            description = request.form['description']
            car_class = request.form['car_class']
            status = request.form['status']
            
            # Handle Image Upload
            image_url = None
            if 'image_file' in request.files:
                file = request.files['image_file']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    # Use timestamp to avoid name collisions
                    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                    filename = f"{timestamp}_{filename}"
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    image_url = url_for('static', filename=f'uploads/cars/{filename}')
            
            # Fallback to URL input if no file uploaded
            if not image_url and request.form.get('image_url'):
                image_url = request.form['image_url']
            
            new_car = Car(
                brand=brand, model=model, year=year, price_per_day=price,
                transmission=transmission, fuel_type=fuel, seats=seats,
                image_url=image_url, description=description,
                car_class=car_class, status=status
            )
            db.session.add(new_car)
            db.session.commit()
            flash('Car added successfully!', 'success')
            return redirect(url_for('manage_cars'))
        except Exception as e:
            flash(f'Error adding car: {str(e)}', 'danger')

    return render_template('edit_car.html', car=None)

@app.route('/manage/car/edit/<int:car_id>', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager'])
def edit_car(car_id):
    car = Car.query.get_or_404(car_id)
    if request.method == 'POST':
        try:
            car.brand = request.form['brand']
            car.model = request.form['model']
            car.year = int(request.form['year'])
            car.price_per_day = int(request.form['price'])
            car.transmission = request.form['transmission']
            car.fuel_type = request.form['fuel']
            car.seats = int(request.form['seats'])
            car.description = request.form['description']
            car.car_class = request.form['car_class']
            car.status = request.form['status']
            
            # Handle Image Upload
            if 'image_file' in request.files:
                file = request.files['image_file']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                    filename = f"{timestamp}_{filename}"
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    car.image_url = url_for('static', filename=f'uploads/cars/{filename}')
            
            # Update image_url from text input if provided (and no file uploaded this time, or to overwrite)
            if request.form.get('image_url') and request.form['image_url'] != car.image_url:
                 car.image_url = request.form['image_url']
            
            db.session.commit()
            flash('Car updated successfully!', 'success')
            return redirect(url_for('manage_cars'))
        except Exception as e:
            flash(f'Error updating car: {str(e)}', 'danger')
            
    return render_template('edit_car.html', car=car)

@app.route('/manage/bookings')
@login_required
@role_required(['admin', 'manager'])
def manage_bookings():
    filter_status = request.args.get('status')
    if filter_status:
        bookings = Booking.query.filter_by(status=filter_status).order_by(Booking.start_date.desc()).all()
    else:
        bookings = Booking.query.order_by(Booking.start_date.desc()).all()
    return render_template('manage_bookings.html', bookings=bookings)

@app.route('/manage/booking/update/<int:booking_id>/<action>')
@login_required
@role_required(['admin', 'manager'])
def update_booking_status(booking_id, action):
    booking = Booking.query.get_or_404(booking_id)
    if action == 'confirm':
        booking.status = 'Confirmed'
        # Optional: set car status to Booked? 
        # booking.car.status = 'Booked' # If we want to strictly lock it
        flash(f'Booking #{booking.id} confirmed.', 'success')
    elif action == 'cancel':
        booking.status = 'Canceled'
        flash(f'Booking #{booking.id} canceled.', 'warning')
    elif action == 'complete':
        booking.status = 'Completed'
        flash(f'Booking #{booking.id} marked as completed.', 'success')
    
    db.session.commit()
    return redirect(url_for('manage_bookings'))

@app.route('/manage/car/delete/<int:car_id>')
@login_required
@role_required(['admin']) # Only Admin can delete
def delete_car(car_id):
    car = Car.query.get_or_404(car_id)
    db.session.delete(car)
    db.session.commit()
    flash('Car deleted successfully!', 'success')
    return redirect(url_for('manage_cars'))

if __name__ == '__main__':
    app.run(debug=True)