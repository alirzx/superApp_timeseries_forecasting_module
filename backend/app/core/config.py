"""Minimal, explicit environment configuration; no secrets baked into images."""
from dataclasses import dataclass
import os
from pathlib import Path


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name, str(default)).strip().lower()
    if value not in {'true', 'false', '1', '0', 'yes', 'no'}:
        raise ValueError(f'{name} must be true or false')
    return value in {'true', '1', 'yes'}


@dataclass(frozen=True)
class Settings:
    app_env: str
    api_auth_enabled: bool
    api_token: str
    model_id: str
    model_revision: str
    model_path: Path
    cpu_threads: int
    max_rows: int
    max_upload_mb: int
    max_batch_series: int
    max_concurrent_inference: int
    max_queue_wait_seconds: float
    max_missing_fraction: float
    max_backtest_windows: int

    @classmethod
    def load(cls):
        s = cls(
            app_env=os.getenv('APP_ENV', 'development'),
            api_auth_enabled=_bool('API_AUTH_ENABLED', True),
            api_token=os.getenv('API_TOKEN', ''),
            model_id=os.getenv('MODEL_ID', 'ibm-granite/granite-timeseries-ttm-r3'),
            model_revision=os.getenv('MODEL_REVISION','').strip(),
            model_path=Path(os.getenv('MODEL_PATH', '/models/granite-ttm-r3')).resolve(),
            cpu_threads=int(os.getenv('CPU_THREADS', '2')),
            max_rows=int(os.getenv('MAX_ROWS', '10000')),
            max_upload_mb=int(os.getenv('MAX_UPLOAD_MB', '5')),
            max_batch_series=int(os.getenv('MAX_BATCH_SERIES', '8')),
            max_concurrent_inference=int(os.getenv('MAX_CONCURRENT_INFERENCE', '1')),
            max_queue_wait_seconds=float(os.getenv('MAX_QUEUE_WAIT_SECONDS', '10')),
            max_missing_fraction=float(os.getenv('MAX_MISSING_FRACTION', '0.05')),
            max_backtest_windows=int(os.getenv('MAX_BACKTEST_WINDOWS', '3')),
        )
        if s.app_env not in {'development','production','test'}:
            raise ValueError('APP_ENV must be development, production or test')
        if s.model_revision and (len(s.model_revision) != 40 or any(c not in '0123456789abcdef' for c in s.model_revision)):
            raise ValueError('MODEL_REVISION must be immutable 40-character SHA')
        if s.app_env == 'production' and not s.model_revision:
            raise ValueError('Production requires MODEL_REVISION pin')
        if s.app_env == 'production' and not s.api_auth_enabled:
            raise ValueError('Production API authentication cannot be disabled')
        if s.api_auth_enabled and (len(s.api_token) < 24 or s.api_token.startswith('REPLACE_')):
            raise ValueError('API_TOKEN must be at least 24 characters when auth is enabled')
        if any(x < 1 for x in [s.cpu_threads,s.max_rows,s.max_upload_mb,s.max_batch_series,s.max_concurrent_inference,s.max_backtest_windows]):
            raise ValueError('Resource limits must be positive')
        if not 0 <= s.max_missing_fraction <= 0.2:
            raise ValueError('MAX_MISSING_FRACTION must be between 0 and 0.2')
        return s
