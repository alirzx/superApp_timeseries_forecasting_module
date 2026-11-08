from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
import math

ModelName = Literal['granite-ttm-r3', 'seasonal-naive']
Frequency = Literal['h', 'D']

class Point(BaseModel):
    model_config = ConfigDict(extra='forbid')
    timestamp: datetime
    value: float

    @field_validator('value')
    @classmethod
    def finite(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError('Values must be finite')
        return v

class ForecastRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    points: list[Point] = Field(min_length=2, max_length=10000)
    horizon: int = Field(default=12, ge=1, le=30)
    frequency: Frequency = 'D'
    model: ModelName = 'granite-ttm-r3'
    seasonal_period: int = Field(default=7, ge=1, le=168)

class BatchRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    series: list[ForecastRequest] = Field(min_length=1, max_length=32)

class BacktestRequest(ForecastRequest):
    windows: int = Field(default=3, ge=1, le=10)

class ForecastPoint(BaseModel):
    timestamp: datetime
    value: float
    q10: float | None = None
    q90: float | None = None

class ForecastResponse(BaseModel):
    model: str
    model_revision: str | None
    frequency: Frequency
    horizon: int
    observations_used: int
    history: list[Point]
    forecast: list[ForecastPoint]
    warnings: list[str]
    latency_ms: float
    quantiles_available: bool

class WindowMetrics(BaseModel):
    start: datetime
    end: datetime
    mae: float
    rmse: float
    smape: float
    mase: float | None

class BacktestResponse(BaseModel):
    model: str
    windows: list[WindowMetrics]
    mean_mae: float
    mean_rmse: float
    mean_smape: float
    warnings: list[str]
