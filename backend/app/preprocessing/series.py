"""Data guardrails. Never fill missing labels across a backtest split."""
import math
from dataclasses import dataclass
import pandas as pd
import numpy as np
from fastapi import HTTPException
from app.api.schemas import Point, Frequency

@dataclass
class Prepared:
    timestamps: list[pd.Timestamp]
    values: np.ndarray
    frequency: Frequency
    warnings: list[str]


def prepare(points: list[Point], frequency: Frequency, max_rows: int, missing_fraction: float) -> Prepared:
    if len(points) > max_rows:
        raise HTTPException(422, detail='Too many observations')
    # All inputs normalized to UTC; naive ISO values are interpreted as UTC.
    times = pd.to_datetime([p.timestamp for p in points], utc=True, errors='raise')
    idx = pd.DatetimeIndex(times)
    if idx.has_duplicates:
        raise HTTPException(422, detail='Duplicate timestamps are not allowed')
    if not idx.is_monotonic_increasing:
        raise HTTPException(422, detail='Timestamps must be strictly increasing')
    if len(idx) < 2:
        raise HTTPException(422, detail='At least two observations required')
    freq = 'h' if frequency == 'h' else 'D'
    expected = pd.date_range(start=idx[0], end=idx[-1], freq=freq, tz='UTC')
    if len(expected) < len(idx) or len(expected) > max_rows:
        raise HTTPException(422, detail='Invalid frequency or time span exceeds row limit')
    if not idx.isin(expected).all():
        raise HTTPException(422, detail='Timestamps do not align to the requested frequency')
    values = np.asarray([p.value for p in points], dtype=np.float64)
    if not np.isfinite(values).all() or np.max(np.abs(values)) > 1e12:
        raise HTTPException(422, detail='Non-finite or excessively large values')
    series = pd.Series(values, index=idx).reindex(expected)
    missing = int(series.isna().sum())
    if missing / len(series) > missing_fraction:
        raise HTTPException(422, detail='Too many missing timestamps: lower gap count or resample data')
    warns = []
    if missing:
        # Interpolation is confined to the observed history passed into this call.
        # Do NOT prepare all rows before selecting a backtesting train/holdout split.
        series = series.interpolate(method='time', limit_direction='both')
        warns.append(f'{missing} missing historical timestamp(s) interpolated')
    return Prepared(timestamps=list(expected), values=series.to_numpy(dtype=np.float64), frequency=frequency, warnings=warns)


def future_timestamps(last: pd.Timestamp, horizon: int, freq: Frequency) -> list[pd.Timestamp]:
    offset = pd.Timedelta(hours=1) if freq == 'h' else pd.Timedelta(days=1)
    return [last + i * offset for i in range(1, horizon + 1)]


def as_points(data: Prepared) -> list[Point]:
    return [Point(timestamp=t.to_pydatetime(), value=float(v)) for t, v in zip(data.timestamps, data.values)]
