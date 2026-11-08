# Development workflow

- Python 3.11, Node 22, Docker Compose v2.
- Tests: `PYTHONPATH=backend pytest backend/tests -q`.
- Keep production model inference offline; never download at request time.
- Never silently substitute `seasonal-naive` for Granite results.
- Register new models through a dedicated adapter and explicit API model ID.
- Pin model revision and record checksums. Include new benchmarks for changes.
- Do not log uploaded raw time-series data or expose API tokens in the browser.
- No CI file is included in this delivery, as requested.
