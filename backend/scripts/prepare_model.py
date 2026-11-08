"""Explicit model acquisition. Never executed at API startup.

Downloads an immutable revision and generates local SHA256 manifest. The manifest
helps detect local corruption; upstream authenticity requires trusted transport / provenance.
"""
import argparse
import json
import os
from pathlib import Path
from huggingface_hub import HfApi, snapshot_download
from app.core.model_integrity import hash_file, verify_model

REPO = 'ibm-granite/granite-timeseries-ttm-r3'

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--output',default='./.models/granite-ttm-r3')
    p.add_argument('--revision',default=os.environ.get('MODEL_REVISION',''))
    p.add_argument('--verify-only',action='store_true')
    a=p.parse_args()
    dest=Path(a.output).resolve()
    if a.verify_only:
        print(json.dumps({'status':'verified','revision':verify_model(dest)}))
        return
    revision=a.revision or HfApi().model_info(REPO).sha
    if len(revision)!=40 or not all(x in '0123456789abcdef' for x in revision):
        raise ValueError('Use immutable 40-character model revision SHA')
    dest.mkdir(parents=True,exist_ok=True)
    snapshot_download(repo_id=REPO,revision=revision,local_dir=str(dest),
        allow_patterns=['config.json','*.safetensors','model.safetensors.index.json'],
        ignore_patterns=['*.bin','*.pt','*.pth'])
    files={str(f.relative_to(dest)):hash_file(f) for f in dest.rglob('*') if f.is_file() and not f.is_symlink() and (f.name=='config.json' or f.suffix=='.safetensors' or f.name=='model.safetensors.index.json')}
    if 'config.json' not in files or not any(name.endswith('.safetensors') for name in files):
        raise RuntimeError('Checkpoint download incomplete')
    tmp=dest/'manifest.json.tmp'
    tmp.write_text(json.dumps({'model_id':REPO,'revision':revision,'files':files},indent=2)+'\n','utf-8')
    tmp.replace(dest/'manifest.json')
    print(json.dumps({'status':'downloaded_and_verified','revision':verify_model(dest),'files':list(files)}))

if __name__=='__main__':
    main()
