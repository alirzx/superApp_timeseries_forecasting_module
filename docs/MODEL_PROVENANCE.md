# Model provenance and release gates

**Primary model:** `ibm-granite/granite-timeseries-ttm-r3`.
**Project:** https://huggingface.co/ibm-granite/granite-timeseries-ttm-r3
**Implementation:** https://github.com/ibm-granite/granite-tsfm
**Model license (card):** Apache-2.0; reconfirm at each release.

The selected released checkpoint has `context_length=512`,
`prediction_length=30`, `num_input_channels=1`, internal `scaling="std"`,
and `multi_quantile_head=true` with 0.1..0.9 quantile levels.
The final inference adapter calls the genuine `TinyTimeMixerForPrediction`
class from `granite-tsfm==0.3.12` on CPU.

`backend/scripts/prepare_model.py` resolves a remote revision to its exact
40-character commit SHA and creates a local hash manifest. In production,
set `MODEL_REVISION` to the exact SHA from that manifest; the API refuses
mismatched prepared artifacts. The manifest is an integrity check, not a
cryptographic signature of IBM or Hugging Face.

## Release gates

1. `make model` and `make model-verify` on a network-enabled computer.
2. `python scripts/model_smoke.py` using **real** R3 weights.
3. Run API smoke and benchmark with an actual CPU Docker container.
4. Validate quantile ordering and numerical accuracy on real datasets.
5. Measure p50/p95 and peak RSS at 1/2/4 concurrent requests.
6. Confirm package/license/security review and authenticated HTTPS ingress.

Do not claim full pretrained end-to-end acceptance if only the synthetic
sample and injected fake adapter tests have run.
