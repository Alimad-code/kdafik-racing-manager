"""Shared pit-lane timing assumptions for live racing and strategy planning."""

# The virtual lane is calibrated to seven seconds of driving at the pit-speed limit.
PIT_LANE_LENGTH_METERS = 154.0
PIT_LANE_SPEED_MPS = 22.0
PIT_SERVICE_POINT_METERS = PIT_LANE_LENGTH_METERS / 2

# Expected value of the live-service distribution:
# 80% of 2.2–3.0 s, 17% of 3.1–4.8 s, and 3% of 5.0–9.0 s stops.
EXPECTED_PIT_SERVICE_SECONDS = 2.9615
