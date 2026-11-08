# Architecture and choices

```
React RTL / CSV preview → Nginx (/api key injected) → FastAPI
                                                  → input validation + UTC regularization
                                                  → bounded inference lock
                                                      ├── Granite TTM-R3 CPU adapter
                                                      └── seasonal-naive reference
                                                  → chronological timestamp postprocessing
                                                  → quantile metadata if emitted
                                                  → JSON / dashboard
```

- Two long-running containers: API and UI.
- No training, no GPU, no inference cloud, no message broker or database.
- Model weights prepared separately and mounted read-only.
- All state is in the request; keep source data out of access logs.
- R3 is a univariate checkpoint; batch means *independent* series, not native multivariate.
- Statistical reference output is always labeled, never presented as pretrained output.
- Quantile outputs follow IBM's `[batch, quantile, horizon, channel]` convention.
- Model's config contains internal standard scaling. We do not externally normalize
  the context again, and do not scale using any future values.
- Rolling chronological backtest retains an expanding training window. Test labels
  are never included in the forecast input. Series with gaps are rejected in backtests.
- Readiness of **the system** depends on actual Granite, while the API liveness
  remains available for diagnosis if the model is missing.
- Python 3.11 and package `granite-tsfm==0.3.12` are the intended R3 implementation.
- The default model revision is resolved once from HF during explicit setup,
  and recorded with per-file digests in `manifest.json`.

## Validated / not validated

Validated here: Python compile, mocked adapter contract tests, API validation,
file handling, baseline, backtesting, authentication.
Not validated here: actual IBM weight download, CPU inference (requires weights
and matching packages), Docker Compose startup, Vite build (registry unavailable),
model quality benchmark, commercial release readiness.
