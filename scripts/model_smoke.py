"""Real, local-only Granite checkpoint execution. Fails loudly when model unavailable."""
import argparse
import json
import os
import sys
import time
from pathlib import Path
import csv
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.inference.granite import GraniteTTMR3


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--model-path',default=str(ROOT/'.models/granite-ttm-r3'))
    parser.add_argument('--threads',type=int,default=2)
    a=parser.parse_args()
    model=GraniteTTMR3(Path(a.model_path),a.threads)
    start=time.perf_counter()
    model.load()
    if not model.loaded:
        raise SystemExit(f'Granite not ready: {model.error}')
    cold_ms=(time.perf_counter()-start)*1000
    path=ROOT/'datasets/sample/sample-energy.csv'
    with path.open() as f: values=np.asarray([float(r['value']) for r in csv.DictReader(f)],dtype=np.float64)
    lat=[]
    for _ in range(5):
        begin=time.perf_counter()
        result,quantiles=model.forecast(values,24)
        lat.append((time.perf_counter()-begin)*1000)
        assert result.shape==(24,) and np.isfinite(result).all()
        if quantiles is not None: assert quantiles.shape==(24,2)
    print(json.dumps({'status':'verified_real_inference','revision':model.revision,'device':'cpu',
        'cold_load_ms':round(cold_ms,2),'warm_latency_ms':[round(x,2) for x in lat],
        'predicted_first':float(result[0]),'quantiles_available':quantiles is not None},indent=2))

if __name__=='__main__': main()
