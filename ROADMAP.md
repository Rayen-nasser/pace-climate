# PaceClimate Roadmap

## Phase A ✓ — Session Feedback (add to model + log form)
- [x] `sleep_hours` (float) — hours slept before run
- [x] `pre_run_energy` (int 1-5) — subjective energy level
- [x] `muscle_soreness` (int 1-5) — subjective soreness
- [x] `perceived_effort` / RPE (int 1-10) — how hard it felt
- [x] `run_type` (easy/tempo/interval/long_run/race/recovery)

## Phase B ✓ — Derivative Features (computed from existing data)
- [x] `days_since_last_run` — rest/recovery indicator
- [x] `recent_7d_distance` — training load (km)
- [x] `recent_7d_run_count` — training frequency
- [x] `heat_index` — feels-like temp offset

## Phase C ✓ — Better Environmental Data
- [x] AQI (Air Quality Index) — fetched from Open-Meteo Air Quality API, shown in forecast cards
- [x] UV index — added to weather params, shown in forecast cards
- [x] Dew point — added to weather params, used as ML feature

*Features: 34→37*

## Phase D ✓ — Athlete Services
- [x] Recovery recommendation — banner analyzes sleep/soreness/RPE/volume → "rest day" / "easy day" / "ready"
- [x] Training load display — 7d volume + runs, monthly volume in header stats bar
- [x] Goal setting — editable weekly km/runs targets with progress % in stats bar

*Pending:* Route suggestion (flat vs hilly based on energy + weather)
