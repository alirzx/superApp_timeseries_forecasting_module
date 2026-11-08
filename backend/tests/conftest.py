import os
os.environ['APP_ENV']='test'
os.environ['API_AUTH_ENABLED']='false'
import pytest
from app.core.config import Settings
from app.main import create_app
from app.inference.baseline import SeasonalNaive

class FakeGranite:
    name='granite-ttm-r3'
    context_length=512
    prediction_length=30
    revision='f'*40
    loaded=True
    error=None
    def forecast(self, values, horizon, seasonal_period=7):
        import numpy as np
        return np.repeat(values[-1], horizon), np.stack([np.repeat(values[-1]-5,horizon), np.repeat(values[-1]+5,horizon)], axis=1)

@pytest.fixture
def fake_model():
    return FakeGranite()

@pytest.fixture
def settings(monkeypatch):
    monkeypatch.setenv('APP_ENV','test')
    monkeypatch.setenv('API_AUTH_ENABLED','false')
    return Settings.load()

@pytest.fixture
def app(settings, fake_model):
    return create_app(settings=settings, granite=fake_model, baseline=SeasonalNaive())

@pytest.fixture
def sample_rows():
    import csv
    from pathlib import Path
    p=Path(__file__).resolve().parents[2]/'datasets/sample/sample-energy.csv'
    return list(csv.DictReader(p.open()))
