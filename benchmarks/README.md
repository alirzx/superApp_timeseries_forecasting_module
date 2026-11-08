# Benchmark protocol

Use the exact server CPU and production container limits. Run `python scripts/model_smoke.py` first.
Then run `python scripts/smoke_api.py --model granite-ttm-r3` with the API running.
For real capacity, measure cold model loading, p50/p95 request latency, peak RSS,
CPU throttling, and success rate at concurrency 1/2/4. Do not raise API worker
count until RAM/throughput impact is measured. Compare forecasting accuracy with
seasonal-naive using chronological backtesting. Never score on synthetic data alone.
