from sqlalchemy import text
from datetime import datetime, timedelta
from collections import defaultdict
from flask import flash
from models import db, Car, Location, Booking, Maintenance

def get_statistics_context(request_args):
    # 1. Отримання локацій та вільних місць (Складний SQL-запит)
    locations_query = text("""
        SELECT 
            l.id, 
            l.city, 
            l.address, 
            l.max_capacity,
            (SELECT COUNT(*) FROM cars c WHERE c.location_id = l.id) as total_fleet,
            (
                SELECT COUNT(*) 
                FROM bookings b 
                JOIN cars c ON b.car_id = c.id
                WHERE c.location_id = l.id 
                AND b.status IN ('Confirmed', 'New') 
                AND CURRENT_DATE BETWEEN b.start_date AND b.end_date
            ) as cars_on_trip
        FROM locations l
    """)
    
    locations_data = db.session.execute(locations_query).fetchall()
    
    stats_data = []
    for loc in locations_data:
        occupied_at_station = loc.total_fleet - loc.cars_on_trip
        occupied_at_station = max(0, occupied_at_station)
        free_spots = loc.max_capacity - occupied_at_station
        
        stats_data.append({
            'city': loc.city,
            'address': loc.address,
            'max_capacity': loc.max_capacity,
            'total_fleet': loc.total_fleet,
            'cars_on_trip': loc.cars_on_trip,
            'free_spots': free_spots
        })

    # 2. Отримання параметрів фільтрації
    filter_loc_id = request_args.get('location_id')
    filter_period = request_args.get('period', 'month')
    filter_class = request_args.get('car_class')
    filter_metric = request_args.get('metric', 'income')
    filter_car_id = request_args.get('maintenance_car_id')

    # Розрахунок діапазону дат
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)
    aggregation_type = 'day'

    if filter_period == 'week':
        start_date = end_date - timedelta(weeks=1)
        aggregation_type = 'day'
    elif filter_period == '2weeks':
        start_date = end_date - timedelta(weeks=2)
        aggregation_type = 'day'
    elif filter_period == 'month':
        start_date = end_date - timedelta(days=30)
        aggregation_type = 'week'
    elif filter_period == '3months':
        start_date = end_date - timedelta(days=90)
        aggregation_type = 'week'
    elif filter_period == '6months':
        start_date = end_date - timedelta(days=180)
        aggregation_type = 'month'
    elif filter_period == 'year':
        start_date = end_date - timedelta(days=365)
        aggregation_type = 'month'

    # 3. Графік доходів/бронювань
    base_sql = """
        SELECT b.start_date, b.total_price, b.id
        FROM bookings b
        JOIN cars c ON b.car_id = c.id
        WHERE b.status IN ('Confirmed', 'Completed')
        AND b.start_date >= :start_date
        AND b.start_date <= :end_date
    """
    
    params = {'start_date': start_date, 'end_date': end_date}

    if filter_loc_id and filter_loc_id != 'all':
        base_sql += " AND c.location_id = :loc_id"
        params['loc_id'] = int(filter_loc_id)

    if filter_class and filter_class != 'all':
        base_sql += " AND c.car_class = :car_class"
        params['car_class'] = filter_class
        
    base_sql += " ORDER BY b.start_date ASC"
    
    raw_data = db.session.execute(text(base_sql), params).fetchall()
    
    aggregated_data = defaultdict(float if filter_metric == 'income' else int)
    
    for row in raw_data:
        b_date = row[0]
        val = row[1] if filter_metric == 'income' else 1
        
        if aggregation_type == 'day':
            key = b_date.strftime('%Y-%m-%d')
        elif aggregation_type == 'week':
            isoyear, isoweek, isoday = b_date.isocalendar()
            key = f"W{isoweek}-{isoyear}"
        elif aggregation_type == 'month':
            key = b_date.strftime('%Y-%m')
            
        aggregated_data[key] += val

    if aggregation_type == 'week':
        temp_data = defaultdict(float if filter_metric == 'income' else int)
        for row in raw_data:
            b_date = row[0]
            val = row[1] if filter_metric == 'income' else 1
            isoyear, isoweek, isoday = b_date.isocalendar()
            key = f"{isoyear}-W{isoweek:02d}"
            temp_data[key] += val
        aggregated_data = temp_data

    sorted_keys = sorted(aggregated_data.keys())
    days = sorted_keys
    values = [aggregated_data[k] for k in sorted_keys]
    
    plot_url = None
    try:
        from plotting import generate_income_plot
        plot_url = generate_income_plot(days, values, f"{filter_metric.capitalize()} / {filter_period}")
    except ImportError:
        flash('Matplotlib не встановлено.', 'warning')
    except Exception as e:
        print(f"Помилка побудови графіка: {e}")

    # 4. Статистика обслуговування (Maintenance)
    maintenance_plot_url = None
    maintenance_summary_url = None
    selected_maintenance_car = None
    
    # Отримання всіх авто для випадаючого списку
    all_cars = Car.query.all()
    
    # Підсумок: Загальні витрати на обслуговування по кожному авто
    try:
        from plotting import generate_maintenance_summary_plot, generate_maintenance_plot
        
        # Отримання списку авто з записами про обслуговування
        cars_with_maintenance = db.session.execute(text("""
            SELECT c.id, c.brand, c.model, c.year, COALESCE(SUM(m.cost), 0) as total_cost
            FROM cars c
            LEFT JOIN maintenance m ON c.id = m.car_id
            GROUP BY c.id, c.brand, c.model, c.year
            HAVING COALESCE(SUM(m.cost), 0) > 0
            ORDER BY total_cost DESC
            LIMIT 10
        """)).fetchall()
        
        if cars_with_maintenance:
            car_names = [f"{row[1]} {row[2]}" for row in cars_with_maintenance]
            total_costs = [row[4] for row in cars_with_maintenance]
            maintenance_summary_url = generate_maintenance_summary_plot(car_names, total_costs)
        
        # Графік обслуговування для конкретного авто
        if filter_car_id and filter_car_id != 'all':
            selected_maintenance_car = Car.query.get(int(filter_car_id))
            if selected_maintenance_car:
                records = Maintenance.query.filter_by(car_id=int(filter_car_id)).order_by(Maintenance.date.asc()).all()
                if records:
                    dates = [r.date.strftime('%d.%m.%Y') for r in records]
                    costs = [r.cost for r in records]
                    car_name = f"{selected_maintenance_car.brand} {selected_maintenance_car.model}"
                    maintenance_plot_url = generate_maintenance_plot(dates, costs, car_name)
                    
    except Exception as e:
        print(f"Помилка побудови графіка обслуговування: {e}")

    # Отримання всіх локацій для випадаючого списку фільтра
    all_locations = Location.query.all()
    
    # Отримання всіх класів автомобілів
    car_classes_rows = db.session.execute(text("SELECT DISTINCT car_class FROM cars")).fetchall()
    all_car_classes = [row[0] for row in car_classes_rows]

    return {
        'location_stats': stats_data,
        'plot_url': plot_url,
        'locations': all_locations,
        'current_loc': filter_loc_id,
        'current_period': filter_period,
        'current_class': filter_class,
        'current_metric': filter_metric,
        'car_classes': all_car_classes,
        # Обслуговування (Maintenance)
        'maintenance_plot_url': maintenance_plot_url,
        'maintenance_summary_url': maintenance_summary_url,
        'all_cars': all_cars,
        'current_maintenance_car': filter_car_id,
        'selected_maintenance_car': selected_maintenance_car
    }
