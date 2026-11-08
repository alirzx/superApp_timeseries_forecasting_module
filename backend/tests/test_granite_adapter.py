from types import SimpleNamespace
from pathlib import Path
import numpy as np
import torch
from app.inference.granite import GraniteTTMR3

def test_adapter_inference_tensor_and_quantile_shapes():
    class FakeTorchModel:
        config=SimpleNamespace(quantile_levels=[0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9])
        def __call__(self, past_values, return_dict, return_loss):
            assert tuple(past_values.shape)==(1,512,1)
            assert not return_loss and return_dict
            p=torch.ones((1,30,1))*33
            q=torch.arange(9).view(1,9,1,1).expand(1,9,30,1).float()*10
            return SimpleNamespace(prediction_outputs=p,quantile_outputs=q)
    adapter=GraniteTTMR3(Path('/does-not-matter'))
    adapter._model=FakeTorchModel()
    p,q=adapter.forecast(np.arange(720,dtype=float),horizon=12)
    assert p.shape==(12,) and np.all(p==33)
    assert q.shape==(12,2) and np.all(q[:,0]==0) and np.all(q[:,1]==80)
