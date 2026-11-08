"""IBM Granite TTM-R3 CPU adapter. No network access or model substitution at runtime."""
import hashlib
import json
import logging
import os
from pathlib import Path
import numpy as np

log = logging.getLogger(__name__)


class GraniteTTMR3:
    name = 'granite-ttm-r3'
    context_length = 512
    prediction_length = 30

    def __init__(self, model_dir: Path, threads: int = 2, expected_revision: str = ""):
        self.model_dir = Path(model_dir)
        self.threads = threads
        self.expected_revision = expected_revision
        self._model = None
        self.revision = None
        self.error = None

    @property
    def loaded(self):
        return self._model is not None

    def load(self):
        """Startup is offline. Require prepare_model.py output and verify its manifest."""
        try:
            from tsfm_public.models.tinytimemixer import TinyTimeMixerForPrediction
            import torch
            from app.core.model_integrity import verify_model

            revision = verify_model(self.model_dir)
            if self.expected_revision and revision != self.expected_revision:
                raise ValueError('Model revision differs from MODEL_REVISION')
            torch.set_num_threads(self.threads)
            model = TinyTimeMixerForPrediction.from_pretrained(str(self.model_dir), local_files_only=True)
            if int(model.config.context_length) != 512 or int(model.config.prediction_length) != 30:
                raise ValueError('Unexpected checkpoint context/horizon; expected 512/30')
            # The chosen checkpoint is univariate; do not claim covariate inference.
            if int(model.config.num_input_channels) != 1:
                raise ValueError('Unexpected number of input channels')
            model.to('cpu').eval()
            self._model = model
            self.revision = revision
            self.error = None
            log.info('Granite R3 model initialized (offline, cpu)')
        except Exception as exc:
            self._model = None
            self.error = f'{type(exc).__name__}: {exc}'
            log.warning('Granite model unavailable: %s', self.error)

    def forecast(self, values: np.ndarray, horizon: int, seasonal_period: int = 7):
        if not self.loaded:
            raise RuntimeError('Granite checkpoint not ready. Run model preparation and restart API.')
        if len(values) < self.context_length:
            raise ValueError(f'Granite requires at least {self.context_length} regular observations')
        if horizon > self.prediction_length:
            raise ValueError(f'Granite checkpoint only supports {self.prediction_length} future steps')
        import torch
        seq = np.asarray(values[-self.context_length:], dtype=np.float32)
        # No explicit global scaling: checkpoint has internal scaling="std".
        past = torch.as_tensor(seq.reshape(1, self.context_length, 1), dtype=torch.float32, device='cpu')
        with torch.inference_mode():
            out = self._model(past_values=past, return_dict=True, return_loss=False)
        result = out.prediction_outputs.detach().cpu().numpy()
        if result.shape != (1, self.prediction_length, 1):
            raise RuntimeError(f'Unexpected point forecast shape {result.shape}')
        point = result[0, :horizon, 0].astype(np.float64)
        quantiles = None
        raw = getattr(out, 'quantile_outputs', None)
        levels = list(getattr(self._model.config, 'quantile_levels', []) or [])
        if raw is not None and 0.1 in levels and 0.9 in levels:
            q = raw.detach().cpu().numpy()
            # IBM: [batch, quantile, prediction_length, channels]
            if q.ndim == 4 and q.shape[0] == 1 and q.shape[2] >= horizon and q.shape[3] == 1:
                lower = q[0, levels.index(0.1), :horizon, 0]
                upper = q[0, levels.index(0.9), :horizon, 0]
                quantiles = np.stack([lower, upper], axis=1).astype(np.float64)
        if not np.isfinite(point).all() or (quantiles is not None and not np.isfinite(quantiles).all()):
            raise RuntimeError('Model generated non-finite forecasts')
        return point, quantiles
