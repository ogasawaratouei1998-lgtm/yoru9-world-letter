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
from article_country_materials import prepare_material_bundle, material_tasks
from country_topic_drafts import discover_topics
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
    p.add_argument("--prefetched",type=Path)
    p.add_argument("--prior-materials",type=Path)
    p.add_argument("--prefetched-photos",type=Path)
    mode=p.add_mutually_exclusive_group()
    mode.add_argument("--topics-only",action="store_true")
    mode.add_argument("--skip-topics",action="store_true")
    args=p.parse_args()
    day=datetime.now(ZoneInfo("Asia/Tokyo")).date().isoformat()
    if not args.approved.is_file():
        print("No approved article yet; no country research.")
        return
    payload=json.loads(args.approved.read_text(encoding="utf-8"))
    if getattr(args,"topics_only",False):
        public=validate_release_input(ROOT,payload,day,require_assets=True)
        tasks=material_tasks(ROOT,public["stories"],day)
        save(args.output/"material-tasks.json",tasks)
        from country_material_prefetch import merge_prefetch
        topics=merge_prefetch(tasks,discover_topics(tasks),getattr(args,"prefetched",None))
        save(args.output/"topic-drafts.json",topics)
        return
    plan=article_plan(ROOT,payload,day)
    sites={}
    # Approved countries missing only dated topics need official event sources,
    # not another full UNESCO inventory or photo search.
    if plan["countries"]:
        try:
            feed=download_feed()
            sites=collect_sites(feed)
            inventory=build_inventory(ROOT,feed)
            plan=article_plan(ROOT,payload,day,inventory)
        except (URLError,TimeoutError,ValueError,OSError,ET.ParseError) as exc:
            print("Official inventory unavailable:",type(exc).__name__)
    save(args.output/"plan.json",plan)
    # Save tasks before network calls, and persist partial results after each slot.
    # Only the same edition and exact plan slot can reuse candidate evidence.
    from country_article_recovery import (
        candidate_resume, read_prefetched_candidates, add_named_photo_leads,
        checkpoint_research, write_completion_report, discover_authority_leads,
    )
    prior=getattr(args,"prior_materials",None)
    early=getattr(args,"prefetched_photos",None)
    resume=candidate_resume(plan,day,prior,early)
    def checkpoint(rows):
        checkpoint_research(args.output,plan,day,rows)
    report=combine(plan,[research_shard(plan,0,resume=resume,retry_transient=True,
                                      on_progress=checkpoint)])
    add_named_photo_leads(ROOT,report,plan)
    report["editionDate"]=day
    report["articleCountryNeeds"]=plan["articleCountryNeeds"]
    save(args.output/"research.json",report)
    public=validate_release_input(ROOT,payload,day,require_assets=True)
    tasks=prepare_material_bundle(ROOT,public["stories"],day,report,args.output,
                                  heritage_sites=sites,article_recovery=True,prior=prior)
    if not getattr(args,"skip_topics",False):
        topics=discover_topics(tasks)
        # Earlier research remains unapproved until the separate second read.
        from country_material_prefetch import merge_prefetch
        topics=merge_prefetch(tasks,topics,getattr(args,"prefetched",None))
        save(args.output/"topic-drafts.json",topics)
    if "tasks" in tasks:
        discover_authority_leads(ROOT,tasks,args.output)
        write_completion_report(ROOT,payload,day,args.output)
    print("Article countries needing enrichment:",sorted(plan["articleCountryNeeds"]))
    print("Material preparation tasks:",tasks["countriesNeedingMaterials"],
          "; source and visual approval required before publication.")

if __name__=="__main__":
    main()
