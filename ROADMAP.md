# PaceClimate Roadmap

## Phase A ✓ — Session Feedback
- [x] `sleep_hours`, `pre_run_energy`, `muscle_soreness`, `perceived_effort`, `run_type`

## Phase B ✓ — Derivative Features
- [x] `days_since_last_run`, `recent_7d_distance`, `recent_7d_run_count`, `heat_index`

## Phase C ✓ — Better Environmental Data
- [x] AQI, UV index, dew point (37 ML features)

## Phase D ✓ — Athlete Services
- [x] Recovery recommendation banner
- [x] Training load display (7d/30d stats)
- [x] Goal setting (weekly km/runs targets)

## Phase E ✓ — Push Notifications (FCM)
- [x] Firebase Cloud Messaging integration (backend)
- [x] `DeviceToken` + `ScheduledNotification` models (with `time` field)
- [x] Background checker loop (every 60s, sends at correct time)
- [x] 🔔 Remind button on forecast cards
- [x] Service worker for background push delivery
- [x] Schedule/cancel endpoints + UI
- [x] Time picker modal (presets: 7AM, 1PM, 5PM, 7PM + custom)
- [x] "My Reminders" section listing all scheduled notifications with delete

## Pending
- Route suggestion: flat vs hilly based on energy + weather
- SVG clothing graphic for forecast cards
- iOS/Android native apps
