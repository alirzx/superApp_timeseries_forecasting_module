"""Super App Module 05. Only designated local Granite checkpoint is eligible for pretrained inference."""
import asyncio
import csv
import io
import json
import logging
import math
import secrets
from contextlib import asynccontextmanager
from datetime import datetime
from time import perf_counter

from fastapi import FastAPI, Depends, HTTPException, Header, UploadFile, File, Form, Request
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from app.api.schemas import ForecastRequest, ForecastResponse, BatchRequest, BacktestRequest, BacktestResponse, Point
from app.core.config import Settings
from app.inference.granite import GraniteTTMR3
from app.inference.baseline import SeasonalNaive
from app.services.forecast import ForecastService, BusyError

log = logging.getLogger('superapp.forecast')
logging.basicConfig(level='INFO', format='%(levelname)s %(name)s %(message)s')


def create_app(settings: Settings | None = None, granite=None, baseline=None):
    config = settings or Settings.load()
    model = granite or GraniteTTMR3(config.model_path, config.cpu_threads, config.model_revision)
    service = ForecastService(model, baseline or SeasonalNaive(), config)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Model load failure MUST leave readiness unhealthy, not trigger fake forecasts.
        if hasattr(model, 'load'):
            await asyncio.to_thread(model.load)
        yield

    app = FastAPI(title='SuperApp | Time-Series Forecasting', version='0.1.0', lifespan=lifespan,
                  docs_url='/docs' if config.app_env != 'production' else None,
                  redoc_url=None, openapi_url='/openapi.json' if config.app_env != 'production' else None)
    app.state.service = service
    app.state.settings = config

    async def require_key(x_api_key: str | None = Header(default=None)):
        if config.api_auth_enabled and not secrets.compare_digest(x_api_key or '', config.api_token):
            raise HTTPException(status_code=401, detail='Invalid API key')

    @app.exception_handler(BusyError)
    async def busy_handler(request: Request, exc: BusyError):
        from fastapi.responses import JSONResponse
        return JSONResponse({'detail':str(exc)}, status_code=429, headers={'Retry-After':'3'})

    @app.get('/health/live')
    async def live():
        return {'status':'alive','service':'time-series-forecasting'}

    @app.get('/health/ready')
    async def ready():
        if not service.engines['granite-ttm-r3'].loaded:
            raise HTTPException(503, detail='Granite model not loaded; run model setup and restart')
        return {'status':'ready','default_model':'granite-ttm-r3','device':'cpu'}

    @app.get('/v1/models', dependencies=[Depends(require_key)])
    async def models():
        return {'default':'granite-ttm-r3','models':[{'id':v.name,'loaded':v.loaded,
                    'revision':v.revision,'context_length':v.context_length,
                    'prediction_length':v.prediction_length,
                    'error':None if v.loaded else getattr(v,'error','Model not loaded')} for v in service.engines.values()]}

    @app.post('/v1/forecast', response_model=ForecastResponse, dependencies=[Depends(require_key)])
    async def forecast(body: ForecastRequest):
        return await service.forecast(body)

    @app.post('/v1/forecast/batch', response_model=list[ForecastResponse], dependencies=[Depends(require_key)])
    async def batch(body: BatchRequest):
        if len(body.series) > config.max_batch_series:
            raise HTTPException(422, detail='Too many independent series')
        # sequential within bounded inference reservation; prevent unbounded fanout
        return await service.limited(lambda:[service._run(req) for req in body.series])

    @app.post('/v1/forecast/backtest', response_model=BacktestResponse, dependencies=[Depends(require_key)])
    async def backtest(body: BacktestRequest):
        return await service.backtest(body)

    @app.post('/v1/forecast/file', response_model=ForecastResponse, dependencies=[Depends(require_key)])
    async def forecast_file(file: UploadFile = File(...), timestamp_column: str = Form('timestamp'),
             value_column: str = Form('value'), model_name: str = Form('granite-ttm-r3'),
             frequency: str = Form('D'), horizon: int = Form(12), seasonal_period: int = Form(7)):
        if not file.filename or not file.filename.lower().endswith(('.csv','.json')):
            raise HTTPException(422, detail='Only CSV and JSON files supported')
        if any(not c.isidentifier() for c in [timestamp_column, value_column]):
            raise HTTPException(422, detail='Invalid column identifier')
        if file.content_type and file.content_type not in ('text/csv','text/plain','application/json','application/octet-stream','application/vnd.ms-excel'):
            raise HTTPException(415, detail='Unsupported content type')
        limit = config.max_upload_mb*1024*1024
        raw = await file.read(limit+1)
        await file.close()
        if len(raw) > limit:
            raise HTTPException(413, detail='File too large')
        try:
            text = raw.decode('utf-8-sig')
            if file.filename.lower().endswith('.csv'):
                rows = csv.DictReader(io.StringIO(text, newline=''))
                if not rows.fieldnames or timestamp_column not in rows.fieldnames or value_column not in rows.fieldnames:
                    raise ValueError('Missing timestamp/value columns')
                entries=[]
                for record in rows:
                    if len(entries) >= config.max_rows:
                        raise ValueError('Too many data rows')
                    entries.append({'timestamp':record[timestamp_column], 'value':record[value_column]})
            else:
                parsed = json.loads(text)
                if not isinstance(parsed,list) or len(parsed) > config.max_rows:
                    raise ValueError('JSON must be a bounded list of records')
                entries=[{'timestamp':p[timestamp_column],'value':p[value_column]} for p in parsed]
            body = ForecastRequest.model_validate({'points':entries,'frequency':frequency,'horizon':horizon,
                                                   'model':model_name,'seasonal_period':seasonal_period})
        except (ValueError, KeyError, TypeError, ValidationError, UnicodeDecodeError) as exc:
            raise HTTPException(422, detail=f'Invalid input file: {str(exc)[:200]}') from exc
        return await service.forecast(body)

    @app.get('/metrics', response_class=PlainTextResponse, dependencies=[Depends(require_key)])
    async def metrics():
        elapsed=list(service.timings)
        lines=['# TYPE forecast_requests_total counter',f'forecast_requests_total {service.inference_count}',
               '# TYPE forecast_errors_total counter',f'forecast_errors_total {service.error_count}',
               '# TYPE forecast_granite_ready gauge',f'forecast_granite_ready {int(model.loaded)}',
               '# TYPE forecast_latency_milliseconds gauge',f'forecast_latency_milliseconds {round(elapsed[-1],3) if elapsed else 0}']
        return '\n'.join(lines)+'\n'

    return app


app = create_app()
