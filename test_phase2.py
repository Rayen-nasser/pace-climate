"""Test Phase 2 modules directly (no server needed)."""
import sys, os, json
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Init DB
from app.database import init_db, get_db, CURRENT_USER_ID
from app.models import User, RunLog, MlModel
from app.history import log_run, get_history, get_run_count
from app.trainer import train_model, load_model, predict_score
from app.chat import answer_question

init_db()
db = next(get_db())

# Ensure default user
user = db.query(User).filter_by(id=CURRENT_USER_ID).first()
if not user:
    db.add(User(id=CURRENT_USER_ID, username="default"))
    db.commit()

errors = []

def check(name, ok, detail=""):
    if ok:
        print(f"  OK  {name}")
    else:
        errors.append(f"{name}: {detail}")
        print(f"  FAIL {name}: {detail}")

# 1. Log runs
for i in range(20):
    log_run(db, f"2026-06-{i+1:02d}", 5.0 + i*0.2, 30 - i//5, 5 - i%3, f"run #{i+1}")
check("log 20 runs", get_run_count(db) == 20, f"got {get_run_count(db)}")

# 2. Get history
history = get_history(db)
check("history length", len(history) == 20)

# 3. Train model
model = train_model(db)
check("train model", model is not None)

# 4. Verify model entry saved
ml_entry = db.query(MlModel).filter_by(user_id=CURRENT_USER_ID).first()
check("model saved to DB", ml_entry is not None and ml_entry.run_count == 20)

# 5. Predict score
mock_day = {
    "temp_max": 30, "temp_min": 20,
    "precip_sum": 0, "precip_prob": 10,
    "wind_max": 12, "weather_code": 0
}
score = predict_score(db, mock_day)
check("predict score", score is not None and 0 <= score <= 100, f"got {score}")

# 6. Chat
days = [{"date": "2026-06-08", "score": 85, "label": "Great", "explanation": "Nice weather", "weather_desc": "Clear"}]
answer = answer_question("Is Thursday good for running?", days, 20)
check("chat answer not empty", len(answer) > 0)
check("chat mentions score", "85" in answer or "score" in answer)

# 7. Chat with few runs
answer2 = answer_question("Is Thursday good for running?", days, 5)
check("chat mentions low runs", "more runs" in answer2.lower(), f"got: {answer2[:80]}")

db.close()
print(f"\n{'='*40}")
if errors:
    print(f"FAILED: {len(errors)} errors")
    for e in errors:
        print(f"  {e}")
else:
    print("ALL TESTS PASSED")
