import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
import pickle
import os

MODEL_PATH = os.path.join(os.path.dirname(__file__), "occupancy_model.pkl")

def build_features(screening_date, start_time, movie_major_studio, movie_release_date, theater_max_occupancy, is_3d, has_fancy_sound):
    import datetime

    if isinstance(screening_date, str):
        screening_date = datetime.date.fromisoformat(screening_date)
    if isinstance(movie_release_date, str):
        movie_release_date = datetime.date.fromisoformat(movie_release_date)
    if isinstance(start_time, str):
        h, m = start_time.split(":")[:2]
        hour = int(h)
    else:
        hour = start_time.hour

    days_since_release = (screening_date - movie_release_date).days
    day_of_week = screening_date.weekday()
    is_weekend = 1 if day_of_week >= 4 else 0
    is_evening = 1 if hour >= 18 else 0
    is_matinee = 1 if hour < 14 else 0

    return [
        day_of_week,
        is_weekend,
        hour,
        is_evening,
        is_matinee,
        int(bool(movie_major_studio)),
        max(0, days_since_release),
        theater_max_occupancy,
        int(bool(is_3d)),
        int(bool(has_fancy_sound)),
    ]

def train_model(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT
            s.screening_date,
            s.start_time,
            m.major_studio,
            m.release_date,
            t.max_occupancy,
            t.is_3d,
            t.has_fancy_sound,
            COALESCE(SUM(ts.ticket_quantity), 0) AS tickets_sold
        FROM screening s
        JOIN movie m ON m.movie_id = s.movie_id
        JOIN theater t ON t.theater_id = s.theater_id
        LEFT JOIN ticket_sale ts ON ts.screening_id = s.screening_id
        GROUP BY s.screening_id, s.screening_date, s.start_time,
                 m.major_studio, m.release_date,
                 t.max_occupancy, t.is_3d, t.has_fancy_sound
    """)
    rows = cur.fetchall()

    if len(rows) < 3:
        return None

    X, y = [], []
    for row in rows:
        feats = build_features(row[0], row[1], row[2], row[3], row[4], row[5], row[6])
        X.append(feats)
        y.append(float(row[7]))

    model = RandomForestRegressor(n_estimators=50, random_state=42)
    model.fit(X, y)

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)

    return model

def load_model():
    if os.path.exists(MODEL_PATH):
        with open(MODEL_PATH, "rb") as f:
            return pickle.load(f)
    return None

def predict_occupancy(screening_date, start_time, major_studio, release_date, max_occupancy, is_3d, has_fancy_sound):
    model = load_model()
    if model is None:
        return int(max_occupancy * 0.6)
    feats = build_features(screening_date, start_time, major_studio, release_date, max_occupancy, is_3d, has_fancy_sound)
    pred = model.predict([feats])[0]
    return min(int(round(pred)), max_occupancy)

def generate_optimal_schedule(conn, days_ahead=7):
    import datetime
    cur = conn.cursor()

    cur.execute("SELECT movie_id, title, major_studio, release_date FROM movie ORDER BY title")
    movies = cur.fetchall()

    cur.execute("SELECT theater_id, theater_name, max_occupancy, is_3d, has_fancy_sound FROM theater")
    theaters = cur.fetchall()

    import datetime
    today = datetime.date.today()
    time_slots = ["11:00", "14:00", "17:00", "20:00"]

    schedule = []
    for day_offset in range(days_ahead):
        date = today + datetime.timedelta(days=day_offset)
        theater_slot_used = {}

        scored = []
        for movie in movies:
            for theater in theaters:
                for slot in time_slots:
                    key = (theater[0], slot)
                    if key in theater_slot_used:
                        continue
                    pred = predict_occupancy(
                        date, slot, movie[2], movie[3],
                        theater[2], theater[3], theater[4]
                    )
                    from app import calculate_price_manual
                    price = calculate_price_manual(theater[3], theater[4], movie[2], movie[3], date)
                    revenue = pred * price
                    scored.append((revenue, pred, price, date, slot, movie, theater))

        scored.sort(key=lambda x: -x[0])
        used_theater_slots = set()
        for item in scored:
            revenue, pred, price, date, slot, movie, theater = item
            key = (theater[0], slot)
            if key not in used_theater_slots:
                used_theater_slots.add(key)
                schedule.append({
                    "date": str(date),
                    "slot": slot,
                    "movie_id": movie[0],
                    "movie_title": movie[1],
                    "theater_id": theater[0],
                    "theater_name": theater[1],
                    "predicted_tickets": pred,
                    "max_occupancy": theater[2],
                    "price": round(price, 2),
                    "predicted_revenue": round(revenue, 2),
                })

    return schedule
