"""Data quality checks before trading."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import pandas as pd


@dataclass
class DataQualityReport:
    passed: bool
    issues: List[str]
    score: float  # 0-100

    def summary(self) -> str:
        if self.passed:
            return f"Data quality OK (score {self.score:.0f})"
        return "; ".join(self.issues)


def check_ohlcv(df: pd.DataFrame, min_bars: int = 30) -> DataQualityReport:
    issues: List[str] = []
    if df is None or df.empty:
        return DataQualityReport(False, ["No data"], 0)
    if len(df) < min_bars:
        issues.append(f"Only {len(df)} bars (need {min_bars})")
    if df["Close"].isna().sum() > len(df) * 0.1:
        issues.append("Excessive missing Close prices")
    if "Volume" in df.columns and (df["Volume"] == 0).mean() > 0.3:
        issues.append("Many zero-volume bars")
    gaps = df.index.to_series().diff().dt.days.max()
    if gaps and gaps > 5:
        issues.append(f"Large gap detected ({gaps} days)")
    score = max(0, 100 - len(issues) * 25)
    return DataQualityReport(len(issues) == 0, issues, score)
