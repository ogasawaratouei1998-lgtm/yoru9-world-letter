#!/usr/bin/env python3
"""Normalize canonical JSON to 1-country-per-line while keeping it below 1 MiB."""
import argparse
import json
from pathlib import Path
LIMIT=1024*1024
def format_manifest(doc):
    def encode(v):return json.dumps(v,ensure_ascii=False,separators=(",",":"))
    rows=[]
    for k,v in doc.items():
        if k=="countries":
            entries=list(v.items())
            lines=["    "+encode(code)+": "+encode(row)+("," if i<len(entries)-1 else "")
                   for i,(code,row) in enumerate(entries)]
            rows.append('  "countries": {\n'+"\n".join(lines)+'\n  }')
        else:rows.append("  "+encode(k)+": "+encode(v))
    return "{\n"+",\n".join(rows)+"\n}\n"
def validate(path):
    raw=path.read_text(encoding="utf-8")
    doc=json.loads(raw)
    if len(doc["countries"])!=196:raise ValueError("196-country mapping changed")
    if format_manifest(doc)!=raw:raise ValueError("Not normalized: run country_manifest_format.py --write")
    if len(raw.encode("utf-8"))>=LIMIT:raise ValueError("Country file exceeds GitHub Contents 1 MiB limit")
    return doc
def main():
    p=argparse.ArgumentParser()
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument("--check",action="store_true")
    g.add_argument("--write",action="store_true")
    p.add_argument("--path",type=Path,default=Path(__file__).resolve().parent/"country-content.json")
    a=p.parse_args()
    if a.write:
        raw=format_manifest(json.loads(a.path.read_text(encoding="utf-8")))
        if len(raw.encode("utf-8"))>=LIMIT:raise ValueError("Data must be split before growing past 1 MiB")
        a.path.write_text(raw,encoding="utf-8")
    else:validate(a.path)
    print("Country manifest: 196 entries, below GitHub Contents API limit")
if __name__=="__main__":main()
