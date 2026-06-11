import sys
import os
import json
import random
import asyncio
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal, init_db
from app.services.run_history import log_run
from app.services.weather import fetch_historical_weather
from app.services.trainer import train_model
from app.models import User, UserPreference, UserGoal, RunLog, MlModel
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

LAT = 34.425
LON = 8.784

RUN_TEMPLATES = {
    "easy":     {"pace": 5.8, "hard": False, "label": "Easy run"},
    "tempo":    {"pace": 4.8, "hard": True,  "label": "Tempo run"},
    "interval": {"pace": 4.2, "hard": True,  "label": "Interval session"},
    "long_run": {"pace": 5.5, "hard": False, "label": "Long run"},
    "race":     {"pace": 3.9, "hard": True,  "label": "Race effort"},
    "recovery": {"pace": 6.5, "hard": False, "label": "Recovery jog"},
}

TOUGH_REASONS_LIST = ["rain", "wind", "heat", "humidity", "tired", "injury", "hills", "stress"]


def pick_run_type(date, prev_type, fatigue, streak):
    dow = date.weekday()
    if dow == 5:
        if fatigue < 3:
            return "long_run"
        return "easy"
    if dow == 6:
        if streak >= 3 or fatigue >= 3:
            return "recovery"
        return "easy"
    if fatigue >= 4:
        return "recovery"
    roll = random.random()
    if roll < 0.25:
        return "tempo"
    elif roll < 0.45:
        return "interval"
    elif roll < 0.70:
        return "easy"
    return "easy"


def compute_weather_quality(ws):
    score = 5
    tmax = ws.get("temp_max", 25)
    if tmax > 37: score -= 3
    elif tmax > 33: score -= 2
    elif tmax > 30: score -= 1
    elif tmax < 12: score -= 1
    elif tmax < 8:  score -= 2
    precip = ws.get("precip_sum", 0)
    if precip > 8:   score -= 3
    elif precip > 3: score -= 2
    elif precip > 0.5: score -= 1
    wind = ws.get("wind_max", 10)
    if wind > 35: score -= 3
    elif wind > 25: score -= 2
    elif wind > 18: score -= 1
    code = ws.get("weather_code", 0)
    if code >= 95: score -= 3
    elif code >= 80: score -= 2
    elif code >= 61: score -= 1
    elif code == 3: score -= 0
    return max(0, min(5, score))


def pick_tough_reasons(rating, ws, fatigue):
    if rating > 2:
        return []
    reasons = []
    if ws.get("precip_sum", 0) > 0.5:
        reasons.append("rain")
    if ws.get("wind_max", 10) > 20:
        reasons.append("wind")
    tmax = ws.get("temp_max", 25)
    if tmax > 32:
        reasons.append("heat")
    if ws.get("dew_point", 0) > 16:
        reasons.append("humidity")
    if fatigue >= 3:
        reasons.append("tired")
    if rating == 1 and random.random() < 0.25:
        reasons.append("injury")
    while len(reasons) < 2:
        extra = random.choice(TOUGH_REASONS_LIST)
        if extra not in reasons:
            reasons.append(extra)
    return reasons


def generate_run(date, ws, fatigue, prev_type):
    wq = compute_weather_quality(ws)
    run_type = pick_run_type(date, prev_type, fatigue, 0)

    tmpl = RUN_TEMPLATES[run_type]
    base_dist = {"long_run": random.uniform(12, 17),
                 "recovery": random.uniform(3, 5),
                 "interval": random.uniform(5, 8)}.get(run_type, random.uniform(4, 9))

    wf = 0.5 + (wq / 5) * 0.5
    ff = max(0.55, 1.0 - fatigue * 0.07)
    distance = round(base_dist * wf * ff, 1)
    distance = max(2.0, min(20.0, distance))

    tmax = ws.get("temp_max", 25)
    temp_factor = 1.0 + max(0, (tmax - 26) * 0.015)
    pace = tmpl["pace"] * temp_factor
    duration = round(distance * pace)

    base = wq + 1
    fp = max(0, fatigue - 2) * 0.4
    rating = round(base - fp + random.uniform(-0.5, 0.5))
    rating = max(1, min(5, rating))

    base_hr = random.randint(130, 155)
    hf = 0.9 if run_type == "easy" else (1.25 if run_type in ("interval", "race") else 1.05)
    avg_hr = round(base_hr * hf)
    max_hr = round(avg_hr + random.randint(18, 38))

    elev = round(random.uniform(3, 50), 1)

    tough_reasons = pick_tough_reasons(rating, ws, fatigue)

    sleep = round(random.uniform(6.0, 8.5), 1)
    if fatigue >= 3:
        sleep = round(random.uniform(5.0, 7.0), 1)
    if run_type in ("interval", "race"):
        sleep = round(max(4.5, sleep - random.uniform(0.3, 1.0)), 1)

    pre_run_energy = max(1, min(5, round(random.uniform(2.5, 5) - max(0, fatigue - 1.5) * 0.3)))
    muscle_soreness = max(1, min(4, round(random.uniform(1, 2.5) + fatigue * 0.25)))
    perceived_effort = max(1, min(10, round(
        (7 if tmpl["hard"] else 4.5) + max(0, tmax - 28) * 0.15 + max(0, fatigue - 1.5) * 0.25 + random.uniform(-1, 1)
    )))

    return {
        "distance_km": distance,
        "duration_min": duration,
        "rating": rating,
        "run_type": run_type,
        "avg_hr": avg_hr,
        "max_hr": max_hr,
        "elevation_gain": elev,
        "tough_reasons": json.dumps(tough_reasons) if tough_reasons else None,
        "sleep_hours": sleep,
        "pre_run_energy": pre_run_energy,
        "muscle_soreness": muscle_soreness,
        "perceived_effort": perceived_effort,
        "weather_snapshot": ws,
    }


async def main():
    if len(sys.argv) < 3:
        print("Usage: python seed_runs.py <email> <password>")
        sys.exit(1)

    email = sys.argv[1].strip().lower()
    password = sys.argv[2]

    print(f"Seeding runs for {email} ...")

    init_db()
    db = SessionLocal()

    try:
        user = db.query(User).filter_by(email=email).first()
        if not user:
            user = User(email=email, username=email.split("@")[0],
                        password_hash=pwd_context.hash(password))
            db.add(user)
            db.commit()
            db.refresh(user)
            pref = UserPreference(user_id=user.id)
            db.add(pref)
            goal = UserGoal(user_id=user.id, weekly_distance_km=25.0, weekly_runs=3)
            db.add(goal)
            db.commit()
            print(f"  Created user '{email}' (id={user.id}) with default preferences + goal")
        else:
            existing = db.query(RunLog).filter_by(user_id=user.id).count()
            if existing >= 25:
                print(f"  User already has {existing} runs (>=25). Retraining model...")
                model = train_model(db, user.id)
                if model:
                    print(f"  ✅ Model retrained on {existing} runs")
                else:
                    print("  ⚠️  Could not train model")
                return
            if existing > 0:
                print(f"  Found user (id={user.id}) with {existing} runs — deleting to re-seed fresh")
                db.query(RunLog).filter_by(user_id=user.id).delete()
                db.query(MlModel).filter_by(user_id=user.id).delete()
                db.commit()
            else:
                print(f"  Found user (id={user.id}) with no runs")

        today = datetime.now()
        six_weeks_ago = today - timedelta(weeks=7)

        run_dates = []
        cur = six_weeks_ago
        while cur < today and len(run_dates) < 35:
            dow = cur.weekday()
            p = 0.60 if (today - cur).days // 7 <= 3 else 0.50
            if dow == 5:
                p = 0.85
            elif dow == 6:
                p = 0.40
            elif dow in (0, 2, 4):
                p += 0.10
            if random.random() < min(p, 0.95):
                run_dates.append(cur)
            cur += timedelta(days=1)

        random.Random(42).shuffle(run_dates)
        run_dates = sorted(run_dates[:25])

        print(f"  Fetching weather for {len(run_dates)} dates (Gafsa, Tunisia) ...", flush=True)
        batch_size = 5
        weather_by_date = {}

        for i in range(0, len(run_dates), batch_size):
            batch = run_dates[i:i + batch_size]
            tasks = [fetch_historical_weather(LAT, LON, d.strftime("%Y-%m-%d")) for d in batch]
            results = await asyncio.gather(*tasks)
            for j, ws in enumerate(results):
                ds = batch[j].strftime("%Y-%m-%d")
                if ws and ws.get("temp_max") is not None:
                    weather_by_date[ds] = ws
                else:
                    weather_by_date[ds] = {
                        "temp_max": random.randint(20, 34),
                        "temp_min": random.randint(14, 23),
                        "apparent_max": 0, "apparent_min": 0,
                        "precip_sum": 0 if random.random() < 0.75 else round(random.uniform(0.3, 10), 1),
                        "precip_prob": 0,
                        "wind_max": round(random.uniform(5, 28), 1),
                        "weather_code": 0 if random.random() < 0.55 else random.choice([61, 63, 80, 95]),
                        "uv_index": random.randint(3, 9),
                        "dew_point": random.randint(5, 19),
                        "aqi": random.randint(15, 65),
                    }
            print(f"    batch {i // batch_size + 1}/{(len(run_dates) - 1) // batch_size + 1}  ({len(batch)} dates)", flush=True)

        print(f"  Generating and inserting runs ...", flush=True)
        fatigue = 0.0
        prev_type = None
        inserted = 0

        for d in run_dates:
            ds = d.strftime("%Y-%m-%d")
            ws = weather_by_date.get(ds)
            if not ws:
                continue
            if db.query(RunLog).filter_by(user_id=user.id, date=ds).count() > 0:
                continue

            p = generate_run(d, ws, fatigue, prev_type)
            log = log_run(
                db=db, user_id=user.id, date_str=ds,
                distance_km=p["distance_km"], duration_min=p["duration_min"],
                rating=p["rating"],
                notes=f"Seeded {p['run_type']} run",
                weather_snapshot=p.get("weather_snapshot"),
                avg_hr=p.get("avg_hr"), max_hr=p.get("max_hr"),
                elevation_gain=p.get("elevation_gain"),
                tough_reasons=p.get("tough_reasons"),
                run_type=p.get("run_type"),
                perceived_effort=p.get("perceived_effort"),
                pre_run_energy=p.get("pre_run_energy"),
                sleep_hours=p.get("sleep_hours"),
                muscle_soreness=p.get("muscle_soreness"),
            )
            inserted += 1

            if p["rating"] <= 2:
                fatigue = min(7, fatigue + 2)
            elif p["run_type"] in ("interval", "race", "tempo"):
                fatigue = min(7, fatigue + 0.8)
            else:
                fatigue = max(0, fatigue - 0.6)
            prev_type = p["run_type"]

            emoji = "⭐" if p["rating"] >= 4 else "👍" if p["rating"] >= 3 else "😤"
            parts = [f"  {ds}: {p['distance_km']}km in {p['duration_min']}min  pace ~{round(p['duration_min']/p['distance_km'],1):.1f}min/km"
                     f"  rating {p['rating']} {emoji}  — {p['run_type']}"]
            if p.get("tough_reasons"):
                parts.append(f"  tough: {json.loads(p['tough_reasons'])}")
            print("".join(parts), flush=True)

        if inserted == 0:
            print("  No new runs inserted.")
            return

        total = db.query(RunLog).filter_by(user_id=user.id).count()
        print(f"  Inserted {inserted} new runs  (total: {total})")

        if total >= 20:
            print("  Training ML model ...", flush=True)
            m = train_model(db, user.id)
            if m:
                print(f"  ✅ Model trained on {total} runs!")
            else:
                print("  ⚠️  Model training returned None")
        else:
            print(f"  ℹ️  Need {20 - total} more runs to reach training threshold")

        print(f"\n  Done! Login with {email} at http://localhost:8000")

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
