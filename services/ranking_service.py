def calculate_popular_cars(cars, reviews, limit=4, threshold_m=2):
    if not reviews:
        return cars[:limit]

    C = sum(r.rating for r in reviews) / len(reviews)
    m = threshold_m

    scored_cars = []
    for car in cars:
        car_reviews = [r for r in reviews if r.car_id == car.id]
        v = len(car_reviews)
        
        if v == 0:
            score = 0
        else:
            R = sum(r.rating for r in car_reviews) / v
            score = (v / (v + m)) * R + (m / (v + m)) * C

        car.popularity_score = score
        scored_cars.append(car)

    scored_cars.sort(key=lambda x: x.popularity_score, reverse=True)
    
    return scored_cars[:limit]
