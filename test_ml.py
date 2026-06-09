import os, sys, asyncio
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.getcwd())

from app.database import init_db, get_db, CURRENT_USER_ID
from app.models import User, RunLog
from app.history import log_run, get_run_count
from app.trainer import train_model, predict_score, _extract_features, _get_user_averages
from app.weather import fetch_historical_weather
from datetime import datetime, timedelta

init_db()
db = next(get_db())
if not db.query(User).filter_by(id=CURRENT_USER_ID).first():
    db.add(User(id=CURRENT_USER_ID, username="default"))
    db.commit()

async def test():
    today = datetime.now()

    # Log 20 runs with effort data
    for i in range(20):
        day = (today - timedelta(days=20 - i)).strftime("%Y-%m-%d")
        w = await fetch_historical_weather(34.425, 8.784, day)
        log_run(db, day, 5.0 + i * 0.3, 30 - i // 5, 5 - i % 3,
                f"run #{i+1}", w,
                avg_hr=140 + i, max_hr=170 + i, elevation_gain=10 + i * 2)
        print(f"  {day}: dist={5.0+i*0.3:.1f} pace={(30-i//5)/(5.0+i*0.3):.1f} avg_hr={140+i} elev={10+i*2}")

    # Test feature extraction
    logs = db.query(RunLog).order_by(RunLog.date).all()
    avg = _get_user_averages(db)
    print(f"\nUser averages: dist={avg['distance_km']} pace={avg['pace']} avg_hr={avg['avg_hr']}")

    feats = _extract_features(logs[0], avg)
    print(f"Feature vector ({len(feats)} features):")
    from app.trainer import FEATURE_NAMES
    for name, val in zip(FEATURE_NAMES, feats):
        print(f"  {name}: {val}")

    # Train model
    model = train_model(db)
    print(f"\nModel trained: {model is not None}")

    # Predict with default (user averages)
    pred_default = predict_score(db, {
        "temp_max": 30, "temp_min": 20,
        "precip_sum": 0, "precip_prob": 10,
        "wind_max": 15, "weather_code": 0
    })
    print(f"Prediction (avg effort): {pred_default}")

    # Predict with planned harder effort
    pred_hard = predict_score(db, {
        "temp_max": 30, "temp_min": 20,
        "precip_sum": 0, "precip_prob": 10,
        "wind_max": 15, "weather_code": 0
    }, planned_distance=15.0, planned_duration=75)
    print(f"Prediction (15km, 75min): {pred_hard}")

    # Verify they differ
    if pred_default != pred_hard:
        print("OK: effort changes the prediction!")
    else:
        print("WARNING: effort did not change prediction")

asyncio.run(test())
db.close()
