"""Seal a privately preflighted bundle; reuse only byte-identical release inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

def fingerprint(root, names):
    root=Path(root)
    digest=hashlib.sha256()
    for name in sorted(set(names)):
        path=root/name
        if path.is_symlink():
            raise ValueError("Symlink in release inputs: "+name)
        digest.update(json.dumps(name,ensure_ascii=True).encode()+b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest() if path.is_file() else b"missing")
    return digest.hexdigest()

def source_fingerprint(root):
    root=Path(root)
    tracked=subprocess.check_output(["git","ls-files","-z"],cwd=root).decode().split("\0")
    names=[p for p in tracked if p and not p.startswith(("data/approved/","data/archive/")) and p!="data/current.json"]
    names += ["data/current.json"]+[p.relative_to(root).as_posix() for p in (root/"data/archive").rglob("*.json")]
    return fingerprint(root,names)

def bundle_fingerprint(site):
    site=Path(site)
    entries=list(site.rglob("*"))
    if any(p.is_symlink() for p in entries):
        raise ValueError("Unexpected symlink in prepared bundle")
    if not (site/"index.html").is_file():
        raise ValueError("Missing prepared reader")
    return fingerprint(site,[p.relative_to(site).as_posix() for p in entries if p.is_file()])

def snapshot(root, site):
    root=Path(root)
    issue=json.loads((root/"data/current.json").read_text(encoding="utf-8"))
    return {"version":1,"day":issue["editionDate"],"source":source_fingerprint(root),"bundle":bundle_fingerprint(site)}

def seal(root, site, manifest):
    Path(manifest).write_text(json.dumps(snapshot(root,site),sort_keys=True)+"\n",encoding="utf-8")

def verify(root, site, manifest):
    expected=json.loads(Path(manifest).read_text(encoding="utf-8"))
    if expected!=snapshot(root,site):
        raise ValueError("Prepared bundle does not match current validated release inputs")
    from check_release_candidate import audit
    audit(root,site)
    return True

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode",choices=("seal","verify"))
    p.add_argument("--site",required=True,type=Path)
    p.add_argument("--manifest",required=True,type=Path)
    a=p.parse_args()
    if a.mode=="seal":
        seal(Path.cwd(),a.site,a.manifest)
    else:
        verify(Path.cwd(),a.site,a.manifest)
        print("Exact preflighted release bundle verified")

if __name__=="__main__":
    main()
