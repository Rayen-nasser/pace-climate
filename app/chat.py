import os

DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
DAY_ALIASES = {"mon": "monday", "tue": "tuesday", "wed": "wednesday", "thu": "thursday", "fri": "friday", "sat": "saturday", "sun": "sunday"}


def _resolve_day(q, days_data):
    ql = q.lower()
    today_idx = None
    for i, d in enumerate(days_data):
        import datetime
        date_obj = datetime.date.fromisoformat(d["date"])
        if date_obj == datetime.date.today():
            today_idx = i
            break

    if "tomorrow" in ql and today_idx is not None and today_idx + 1 < len(days_data):
        return days_data[today_idx + 1]
    if "today" in ql and today_idx is not None:
        return days_data[today_idx]

    for day_name in DAYS:
        if day_name in ql:
            import datetime
            target = datetime.datetime.strptime(day_name.capitalize(), "%A").weekday()
            for d in days_data:
                date_obj = datetime.date.fromisoformat(d["date"])
                if date_obj.weekday() == target:
                    return d

    for alias, full in DAY_ALIASES.items():
        if alias in ql:
            import datetime
            target = datetime.datetime.strptime(full.capitalize(), "%A").weekday()
            for d in days_data:
                date_obj = datetime.date.fromisoformat(d["date"])
                if date_obj.weekday() == target:
                    return d

    return days_data[0] if days_data else None


def _build_forecast_context(days):
    lines = ["Here is the 7-day running forecast:"]
    for d in days:
        lines.append(
            f"- {d['date']}: {d['weather_desc']}, temp {d['temp_used']}°C, "
            f"rain {d['precip_prob']}%, wind {d['wind_max']} km/h, "
            f"score {d['score']}/100 ({d['label']}). {d.get('explanation', '')}"
        )
    return "\n".join(lines)


def answer_question(q: str, days: list, run_count: int):
    if not days:
        return "No forecast data available."

    groq_api_key = os.environ.get("GROQ_API_KEY")
    if groq_api_key:
        try:
            from groq import Groq
            client = Groq(api_key=groq_api_key)
            context = _build_forecast_context(days)
            model_hint = ""
            if run_count >= 20:
                model_hint = (
                    f"The user has logged {run_count} runs, so an ML model has been trained "
                    "on their personal history. The scores shown already incorporate their "
                    "personal preferences (30% rules, 70% ML). Mention this if relevant."
                )
            else:
                model_hint = (
                    f"The user has logged {run_count} runs. After 20 runs, scores "
                    "will include their personal ML model. Mention this only if asked."
                )

            system_prompt = (
                "You are PaceClimate, an AI running weather advisor. "
                "Answer questions only based on the forecast data provided below. "
                "Be concise (2-4 sentences). Give a clear yes/no or recommendation. "
                "Use temperature in Celsius. Do not make up data.\n\n"
                f"{context}\n\n{model_hint}"
            )

            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": q},
                ],
                temperature=0.3,
                max_tokens=300,
            )
            return resp.choices[0].message.content.strip()
        except Exception:
            pass

    return _fallback_answer(q, days, run_count)


def _fallback_answer(q, days, run_count):
    day = _resolve_day(q, days)
    if not day:
        day = days[0]

    score = day.get("score", 50)
    label = day.get("label", "Unknown")
    explanation = day.get("explanation", "")

    parts = []
    if "thanks" in q.lower() or "thank" in q.lower():
        return "You're welcome! Happy running!"

    if "run" in q.lower() or "running" in q.lower() or "jog" in q.lower():
        if score >= 80:
            parts.append(f"Yes, {day['date']} looks great for running!")
        elif score >= 60:
            parts.append(f"{day['date']} should be decent for running.")
        elif score >= 40:
            parts.append(f"Not ideal, but you could run on {day['date']}.")
        else:
            parts.append(f"I'd skip {day['date']} — conditions aren't great.")
        parts.append(f"Score: {score}/100 ({label}).")
        if run_count < 20:
            parts.append(f"(I'll give better advice after you log {20 - run_count} more runs!)")
        else:
            parts.append(f"Based on your {run_count} logged runs.")
        if explanation:
            parts.append(explanation)
        return " ".join(parts)

    if "score" in q.lower() or "rating" in q.lower() or "how" in q.lower():
        parts.append(f"{day['date']} scores {score}/100 ({label}).")
        if explanation:
            parts.append(explanation)
        return " ".join(parts)

    if "best" in q.lower() or "top" in q.lower():
        best = max(days, key=lambda d: d["score"])
        return f"The best day to run this week is {best['date']} with a score of {best['score']}/100. {best.get('explanation', '')}"

    return f"On {day['date']}, it's {day.get('weather_desc', 'unknown')} with a running score of {score}/100. {explanation}"
