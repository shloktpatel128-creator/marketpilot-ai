"""Feature engineering — delegates to institutional indicator suite."""

from __future__ import annotations

import pandas as pd

from services.indicators import compute_institutional_indicators, latest_indicator_snapshot

# Re-export for backward compatibility
add_features = compute_institutional_indicators
get_indicator_snapshot = latest_indicator_snapshot
