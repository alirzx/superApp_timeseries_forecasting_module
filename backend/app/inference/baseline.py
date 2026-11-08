"""Transparent non-ML reference model. Never mislabeled as Granite."""
import numpy as np

class SeasonalNaive:
    name = 'seasonal-naive'
    context_length = 2
    prediction_length = 30
    revision = 'deterministic-v1'
    loaded = True

    def forecast(self, values: np.ndarray, horizon: int, seasonal_period: int = 7):
        if len(values) < 2:
            raise ValueError('At least two historical observations required')
        season = min(max(1, seasonal_period), len(values))
        reference = values[-season:]
        point = np.array([reference[i % season] for i in range(horizon)], dtype=np.float64)
        return point, None
