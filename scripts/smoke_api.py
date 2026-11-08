"""Run from repo root after starting API. Supports baseline and real Granite mode."""
import argparse
import csv
import json
import os
from pathlib import Path
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--url',default='http://127.0.0.1:8005')
    parser.add_argument('--model',choices=['granite-ttm-r3','seasonal-naive'],default='granite-ttm-r3')
    parser.add_argument('--key',default=os.environ.get('API_TOKEN',''))
    args=parser.parse_args()
    path=ROOT/'datasets/sample/sample-energy.csv'
    with path.open() as f:
        points=list(csv.DictReader(f))
    payload={'points':points,'model':args.model,'frequency':'h','horizon':24,'seasonal_period':24}
    url=args.url.rstrip('/')+'/v1/forecast'
    req=urllib.request.Request(url,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','X-API-Key':args.key},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=180) as resp: result=json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        raise SystemExit(f'HTTP {exc.code} from {url}: {exc.read().decode()[:500]}') from exc
    assert result['model']==args.model
    assert len(result['forecast'])==24
    assert result['observations_used']>=2
    print(json.dumps({'status':'ok','model':result['model'],'revision':result['model_revision'],
       'forecast_points':len(result['forecast']), 'latency_ms':result['latency_ms'],
       'first':result['forecast'][0],'last':result['forecast'][-1]},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
