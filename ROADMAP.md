# PaceClimate Roadmap

## Phase A ✓ — Session Feedback (add to model + log form)
Add pre-run context fields so the model knows *why* a run was tough beyond weather.

- [x] `sleep_hours` (float) — hours slept before run
- [x] `pre_run_energy` (int 1-5) — subjective energy level
- [x] `muscle_soreness` (int 1-5) — subjective soreness
- [x] `perceived_effort` / RPE (int 1-10) — how hard it felt
- [x] `run_type` (easy/tempo/interval/long_run/race/recovery)

*Impact:* +5 features (25→30). Fixes model's biggest blind spot.

## Phase B ✓ — Derivative Features (computed from existing data, zero extra input)

- [x] `days_since_last_run` — rest/recovery indicator
- [x] `recent_7d_distance` — training load (km)
- [x] `recent_7d_run_count` — training frequency
- [x] `heat_index` — feels-like temp offset (uses apparent_temp from Open-Meteo)

*Impact:* +4 features (30→34). Free signals from data you already have.

## Phase C — Better Environmental Data

- [ ] Add AQI (Air Quality Index) — free from Open-Meteo Air Quality API
- [ ] Add UV index — free from Open-Meteo
- [ ] Add dew point — more accurate discomfort measure than humidity alone

## Phase D — Athlete Services

- [ ] Recovery recommendation: "You ran hard + slept 5h → take rest day"
- [ ] Training load dashboard: 7d volume trends, monthly comparison
- [ ] Goal setting: target distance / frequency per week with progress
- [ ] Route suggestion: flat vs hilly based on energy + weather
