#!/usr/bin/env python3
"""Read-only article-driven enrichment. No automatic photo/cultural approval."""
import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from country_codes import country_codes
from country_readiness import article_country_backlog
from release_contract import validate_release_input
from country_bulk_research import make_plan, research_shard, combine, save
from country_unesco_source_catalog import build_inventory, download_feed, collect_sites
from article_country_materials import prepare_material_bundle
from xml.etree import ElementTree as ET
from urllib.error import URLError

ROOT=Path(__file__).resolve().parent

def article_plan(root, payload, day, inventory=None):
    public=validate_release_input(root,payload,day,require_assets=True)
    missing,ready=article_country_backlog(public["stories"],root,day)
    plan=make_plan(root,inventory)
    # Existing approved assets are reused; missing fresh topics are recorded
    # separately, not treated as permission to generate unsourced events.
    plan["countries"]=[row for row in plan["countries"] if row["code"] in missing]
    for row in plan["countries"]:
        row["shard"]=0
    plan["shards"]=1
    plan["slotCount"]=sum(len(row["slots"]) for row in plan["countries"])
    plan["pendingCount"]=len(plan["countries"])
    plan["articleCountryNeeds"]=missing
    return plan

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--approved",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    day=datetime.now(ZoneInfo("Asia/Tokyo")).date().isoformat()
    if not args.approved.is_file():
        print("No approved article yet; no country research.")
        return
    payload=json.loads(args.approved.read_text(encoding="utf-8"))
    plan=article_plan(ROOT,payload,day)
    sites={}
    # Include already approved countries that lack a current topic, not just
    # pending countries requiring three photographs.
    if plan["articleCountryNeeds"]:
        try:
            feed=download_feed()
            sites=collect_sites(feed)
            inventory=build_inventory(ROOT,feed)
            plan=article_plan(ROOT,payload,day,inventory)
        except (URLError,TimeoutError,ValueError,OSError,ET.ParseError) as exc:
            print("Official inventory unavailable:",type(exc).__name__)
    save(args.output/"plan.json",plan)
    report=combine(plan,[research_shard(plan,0)])
    report["articleCountryNeeds"]=plan["articleCountryNeeds"]
    save(args.output/"research.json",report)
    public=validate_release_input(ROOT,payload,day,require_assets=True)
    tasks=prepare_material_bundle(ROOT,public["stories"],day,report,args.output,
                                  heritage_sites=sites)
    print("Article countries needing enrichment:",sorted(plan["articleCountryNeeds"]))
    print("Material preparation tasks:",tasks["countriesNeedingMaterials"],
          "; source and visual approval required before publication.")

if __name__=="__main__":
    main()
