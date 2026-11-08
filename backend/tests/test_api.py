import asyncio
import io
from datetime import datetime, timedelta, timezone
import httpx
import pytest

async def request(app, method, path, **kwargs):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as c:
        return await c.request(method,path,**kwargs)

@pytest.mark.asyncio
async def test_live_ready_models(app):
    assert (await request(app,'GET','/health/live')).status_code==200
    assert (await request(app,'GET','/health/ready')).status_code==200
    models=(await request(app,'GET','/v1/models')).json()['models']
    assert models[0]['loaded'] is True and models[0]['context_length']==512

@pytest.mark.asyncio
async def test_real_contract_with_injected_model(app, sample_rows):
    req={'points':sample_rows,'horizon':12,'frequency':'h','model':'granite-ttm-r3'}
    r=await request(app,'POST','/v1/forecast',json=req)
    assert r.status_code==200, r.text
    data=r.json()
    assert len(data['forecast'])==12
    assert data['quantiles_available'] is True
    assert data['forecast'][0]['q10'] <= data['forecast'][0]['value'] <= data['forecast'][0]['q90']
    assert data['observations_used']==512
    assert data['forecast'][0]['timestamp']>data['history'][-1]['timestamp']

@pytest.mark.asyncio
async def test_uploaded_csv_file(app):
    from pathlib import Path
    source=Path(__file__).resolve().parents[2]/'datasets/sample/sample-energy.csv'
    r=await request(app,'POST','/v1/forecast/file',files={'file':('energy.csv',source.read_bytes(),'text/csv')},data={'frequency':'h','horizon':'24','model_name':'granite-ttm-r3'})
    assert r.status_code==200,r.text
    assert len(r.json()['forecast'])==24

@pytest.mark.asyncio
async def test_short_series_baseline(app):
    times=[datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(days=i) for i in range(20)]
    rows=[{'timestamp':x.isoformat(),'value':float(i%7)} for i,x in enumerate(times)]
    r=await request(app,'POST','/v1/forecast',json={'points':rows,'model':'seasonal-naive','horizon':7,'seasonal_period':7})
    assert r.status_code==200,r.text
    assert r.json()['quantiles_available'] is False
    assert [x['value'] for x in r.json()['forecast']]==[6.,0.,1.,2.,3.,4.,5.]

@pytest.mark.asyncio
async def test_invalid_gap_duplicate_and_short_granite(app):
    start=datetime(2026,1,1,tzinfo=timezone.utc)
    rows=[{'timestamp':(start+timedelta(days=i)).isoformat(),'value':float(i)} for i in range(20)]
    req={'points':rows,'model':'granite-ttm-r3','horizon':5}
    r=await request(app,'POST','/v1/forecast',json=req)
    assert r.status_code==422
    req['model']='seasonal-naive'
    req['points'][3]['timestamp']=req['points'][2]['timestamp']
    r=await request(app,'POST','/v1/forecast',json=req)
    assert r.status_code==422 and 'Duplicate' in r.text

@pytest.mark.asyncio
async def test_backtest(app, sample_rows):
    r=await request(app,'POST','/v1/forecast/backtest',json={'points':sample_rows,'model':'granite-ttm-r3','frequency':'h','horizon':12,'windows':2})
    assert r.status_code==200, r.text
    assert len(r.json()['windows'])==2
    assert r.json()['mean_mae']>=0

@pytest.mark.asyncio
async def test_batch(app, sample_rows):
    base={'points':sample_rows,'model':'granite-ttm-r3','frequency':'h','horizon':6}
    r=await request(app,'POST','/v1/forecast/batch',json={'series':[base,base]})
    assert r.status_code==200,r.text
    assert len(r.json())==2

@pytest.mark.asyncio
async def test_auth(settings, fake_model):
    from dataclasses import replace
    from app.main import create_app
    secure=replace(settings,api_auth_enabled=True,api_token='x'*32)
    a=create_app(settings=secure, granite=fake_model)
    assert (await request(a,'GET','/v1/models')).status_code==401
    assert (await request(a,'GET','/v1/models',headers={'X-API-Key':'x'*32})).status_code==200

@pytest.mark.asyncio
async def test_model_unavailable(settings):
    from app.main import create_app
    class Unavailable:
        name='granite-ttm-r3'; loaded=False; revision=None; error='missing'; context_length=512; prediction_length=30
    a=create_app(settings=settings,granite=Unavailable())
    row=[{'timestamp':(datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(hours=i)).isoformat(),'value':float(i)} for i in range(520)]
    assert (await request(a,'GET','/health/ready')).status_code==503
    r=await request(a,'POST','/v1/forecast',json={'points':row,'frequency':'h'})
    assert r.status_code==503

@pytest.mark.asyncio
async def test_unexpected_file_columns(app):
    r=await request(app,'POST','/v1/forecast/file',files={'file':('bad.csv',b'a,b\n1,2\n','text/csv')})
    assert r.status_code==422
