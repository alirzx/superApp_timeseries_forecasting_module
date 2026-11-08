import asyncio
from dataclasses import dataclass
from time import perf_counter
from collections import deque
import numpy as np
from fastapi import HTTPException
from app.api.schemas import ForecastRequest, ForecastResponse, ForecastPoint, BacktestRequest, BacktestResponse, WindowMetrics
from app.preprocessing.series import prepare, as_points, future_timestamps

class BusyError(Exception):
    pass

class ForecastService:
    def __init__(self, granite, baseline, settings):
        self.engines = {granite.name: granite, baseline.name: baseline}
        self.settings = settings
        self.semaphore = asyncio.Semaphore(settings.max_concurrent_inference)
        self.timings = deque(maxlen=1000)
        self.inference_count = 0
        self.error_count = 0

    async def limited(self, fn):
        try:
            await asyncio.wait_for(self.semaphore.acquire(), timeout=self.settings.max_queue_wait_seconds)
        except asyncio.TimeoutError as exc:
            raise BusyError('Inference capacity exceeded') from exc
        try:
            return await asyncio.to_thread(fn)
        finally:
            self.semaphore.release()

    def select(self, name):
        engine = self.engines[name]
        if not engine.loaded:
            raise HTTPException(503, detail={'message':'Requested pretrained model unavailable', 'model':name})
        return engine

    def _run(self, request: ForecastRequest) -> ForecastResponse:
        start = perf_counter()
        try:
            engine = self.select(request.model)
            p = prepare(request.points, request.frequency, self.settings.max_rows, self.settings.max_missing_fraction)
            if request.horizon > engine.prediction_length:
                raise HTTPException(422, detail='Horizon exceeds checkpoint capability')
            if len(p.values) < engine.context_length:
                raise HTTPException(422, detail=f'{request.model} requires {engine.context_length} regular observations')
            prediction, quantiles = engine.forecast(p.values, request.horizon, request.seasonal_period)
            pred_times = future_timestamps(p.timestamps[-1], request.horizon, request.frequency)
            forecasts = []
            for i, ts in enumerate(pred_times):
                forecasts.append(ForecastPoint(timestamp=ts.to_pydatetime(), value=float(prediction[i]),
                    q10=float(quantiles[i,0]) if quantiles is not None else None,
                    q90=float(quantiles[i,1]) if quantiles is not None else None))
            elapsed = (perf_counter()-start)*1000
            self.timings.append(elapsed)
            self.inference_count += 1
            return ForecastResponse(model=engine.name, model_revision=engine.revision, frequency=request.frequency,
                horizon=request.horizon, observations_used=min(len(p.values), engine.context_length if engine.name == 'granite-ttm-r3' else len(p.values)),
                history=as_points(p)[-120:], forecast=forecasts, warnings=p.warnings,
                latency_ms=round(elapsed,2), quantiles_available=quantiles is not None)
        except Exception:
            self.error_count += 1
            raise

    async def forecast(self, req: ForecastRequest):
        return await self.limited(lambda: self._run(req))

    def _backtest(self, req: BacktestRequest) -> BacktestResponse:
        """Holdout windows split FIRST; training-side interpolation cannot read held-out values."""
        engine = self.select(req.model)
        # Validate global timestamps without interpolation crossing holdout boundaries.
        # For each fold, prepare() on training slice and require holdout timestamps to be regular.
        n = len(req.points)
        if n > self.settings.max_rows or req.windows > self.settings.max_backtest_windows:
            raise HTTPException(422, detail='Backtest limits exceeded')
        min_train = engine.context_length
        if n < min_train + req.windows*req.horizon:
            raise HTTPException(422, detail=f'Need at least {min_train + req.windows*req.horizon} rows for backtesting')
        # strict complete series in backtest to avoid interpolation-in-labels
        from app.preprocessing.series import prepare
        full = prepare(req.points, req.frequency, self.settings.max_rows, 0.0)
        season = req.seasonal_period
        results=[]
        for i in range(req.windows,0,-1):
            train_end = n - i*req.horizon
            train = full.values[:train_end]
            target = full.values[train_end:train_end+req.horizon]
            prediction, _ = engine.forecast(train, req.horizon, season)
            e = target - prediction
            denom = (np.abs(target)+np.abs(prediction)) / 2
            smape = float(np.mean(np.divide(np.abs(e),denom,out=np.zeros_like(e),where=denom>1e-10))*100)
            baseline = np.mean(np.abs(np.diff(train, n=1)))
            results.append(WindowMetrics(start=full.timestamps[train_end].to_pydatetime(),
                 end=full.timestamps[train_end + req.horizon - 1].to_pydatetime(),
                 mae=float(np.mean(np.abs(e))), rmse=float(np.sqrt(np.mean(e**2))),
                 smape=smape, mase=float(np.mean(np.abs(e))/baseline) if baseline>1e-10 else None))
        self.inference_count += req.windows
        return BacktestResponse(model=engine.name, windows=results,
            mean_mae=float(np.mean([x.mae for x in results])),
            mean_rmse=float(np.mean([x.rmse for x in results])),
            mean_smape=float(np.mean([x.smape for x in results])), warnings=[])

    async def backtest(self, req: BacktestRequest):
        return await self.limited(lambda:self._backtest(req))
