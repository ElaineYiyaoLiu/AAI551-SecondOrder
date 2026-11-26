"""Restore large E3-E5 evidence files from hash-checked repository parts.

Run before verification after a fresh checkout. Existing correct originals are
kept; changed originals fail rather than being overwritten. No external data,
credentials or downloads are required. Author: Elaine Liu, with AI assistance.
"""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def restore(destination=None):
    """Reassemble byte-identical evidence atomically and verify every part."""
    destination=Path(destination) if destination else ROOT/'outputs/policy_grids'
    recipe=json.loads((destination/'evidence_parts.json').read_text())
    restored=[]
    for name,entry in recipe.items():
        target=destination/name
        if not target.resolve().is_relative_to(destination.resolve()):
            raise ValueError('Invalid evidence path')
        if target.exists():
            if hashlib.sha256(target.read_bytes()).hexdigest()!=entry['sha256']:
                raise ValueError('Changed existing evidence: '+name)
            continue
        target.parent.mkdir(parents=True,exist_ok=True)
        temporary=target.with_name(target.name+'.restoring')
        try:
            with temporary.open('wb') as output:
                for part in entry['parts']:
                    path=destination/part['path']
                    if not path.resolve().is_relative_to(destination.resolve()):
                        raise ValueError('Invalid part path')
                    data=path.read_bytes()
                    if hashlib.sha256(data).hexdigest()!=part['sha256']:
                        raise ValueError('Changed evidence part: '+part['path'])
                    output.write(data)
            if temporary.stat().st_size!=entry['bytes'] or hashlib.sha256(temporary.read_bytes()).hexdigest()!=entry['sha256']:
                raise ValueError('Restored hash mismatch: '+name)
            temporary.rename(target)
            restored.append(name)
        finally:
            temporary.unlink(missing_ok=True)
    return restored


if __name__=='__main__':
    print(json.dumps({'restored':restore()},indent=2))
