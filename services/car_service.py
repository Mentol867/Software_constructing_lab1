import os
from werkzeug.utils import secure_filename
from datetime import datetime
from flask import url_for
from models import db, Car

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def handle_image_upload(file, upload_folder):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{timestamp}_{filename}"
        file.save(os.path.join(upload_folder, filename))
        return url_for('static', filename=f'uploads/cars/{filename}')
    return None

def create_car(form_data, files, upload_folder):
    try:
        brand = form_data['brand']
        model = form_data['model']
        year = int(form_data['year'])
        price = int(form_data['price'])
        transmission = form_data['transmission']
        fuel = form_data['fuel']
        seats = int(form_data['seats'])
        description = form_data['description']
        car_class = form_data['car_class']
        status = form_data['status']
        
        # Обробка завантаження зображення
        image_url = None
        if 'image_file' in files:
            image_url = handle_image_upload(files['image_file'], upload_folder)
        
        # Використати URL, якщо файл не було завантажено
        if not image_url and form_data.get('image_url'):
            image_url = form_data['image_url']
        
        new_car = Car(
            brand=brand, model=model, year=year, price_per_day=price,
            transmission=transmission, fuel_type=fuel, seats=seats,
            image_url=image_url, description=description,
            car_class=car_class, status=status
        )
        db.session.add(new_car)
        db.session.commit()
        return True, new_car
    except Exception as e:
        return False, str(e)

def update_car(car, form_data, files, upload_folder):
    try:
        car.brand = form_data['brand']
        car.model = form_data['model']
        car.year = int(form_data['year'])
        car.price_per_day = int(form_data['price'])
        car.transmission = form_data['transmission']
        car.fuel_type = form_data['fuel']
        car.seats = int(form_data['seats'])
        car.description = form_data['description']
        car.car_class = form_data['car_class']
        car.status = form_data['status']
        
        # Обробка завантаження зображення
        if 'image_file' in files:
            new_image_url = handle_image_upload(files['image_file'], upload_folder)
            if new_image_url:
                car.image_url = new_image_url
        
        # Оновлення image_url з текстового поля, якщо надано (і файл не був завантажений цього разу, або для перезапису)
        if form_data.get('image_url') and form_data['image_url'] != car.image_url:
                car.image_url = form_data['image_url']
        
        db.session.commit()
        return True, car
    except Exception as e:
        return False, str(e)

def delete_car(car):
    try:
        db.session.delete(car)
        db.session.commit()
        return True, None
    except Exception as e:
        return False, str(e)
