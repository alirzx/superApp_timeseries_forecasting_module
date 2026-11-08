from datetime import datetime,timedelta,timezone
import pytest
from fastapi import HTTPException
from app.api.schemas import Point
from app.preprocessing.series import prepare

def rows(skip=()):
    return [Point(timestamp=datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(days=i),value=float(i)) for i in range(100) if i not in skip]

def test_regular_daily():
    p=prepare(rows(),'D',10000,.05)
    assert len(p.values)==100 and not p.warnings

def test_interpolation_only_in_history():
    p=prepare(rows(skip=(10,)),'D',10000,.05)
    assert p.values[10]==10 and len(p.warnings)==1

def test_excessive_gaps_rejected():
    with pytest.raises(HTTPException):
        prepare(rows(skip=range(10,30)),'D',10000,.05)

def test_daily_hourly_mismatch_rejected():
    with pytest.raises(HTTPException):
        prepare(rows(),'h',100,0.0)
