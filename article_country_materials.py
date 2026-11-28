"""Create actionable, non-public country material drafts for every approved news country.

A draft bundle is not approval. Real photographs require exact visual review;
source dates and claims require editorial verification before canonical sync.
"""
from datetime import date
import json
from pathlib import Path

from audit_country_highlights import missing_topic_dates
from country_codes import country_codes
from country_content import load_country_content
from country_editorial_queue import country_editorial_queue
from country_review_bundle import make_queue, write_bundle
from country_bulk_research import save
from country_source_drafts import generate_heritage_drafts


def material_tasks(root, stories, day, *, heritage_sites=None):
    root = Path(root)
    day = date.fromisoformat(day) if isinstance(day, str) else day
    canonical = load_country_content(root)["countries"]
    queue = {row["code"]: row for row in
             country_editorial_queue(root)["prioritizedPending"]}
    authorities = json.loads((root/"country-highlight-sources.json").read_text(
        encoding="utf-8"))["sources"]
    targets = sorted({code for story in stories
                      for code in country_codes(story.get("country",""))})
    tasks = []
    for code in targets:
        entry = canonical[code]
        topic_days = missing_topic_dates({code:entry["highlights"]},code,day,2)
        missing = list(queue.get(code,{}).get("missing",[]))
        missing = [item for item in missing if item != "optional_current_topic"]
        if topic_days:
            missing.append("current_country_topics")
        if entry["status"]=="pending":
            missing.append("country_publication_review")
        if not missing:
            continue
        sites = (heritage_sites or {}).get(code,[])
        generated=(generate_heritage_drafts(entry["name"],sites,day)
                   if entry["status"]=="pending" else None)
        tasks.append({
            "countryCode":code,"country":entry["name"],
            "status":entry["status"],"missing":missing,
            "missingTopicDates":topic_days,
            "portraitDraft":entry.get("portrait") if entry["status"]=="pending" else None,
            "travelDrafts":entry.get("travelDrafts",[]) if entry["status"]=="pending" else [],
            "quizDrafts":entry.get("quiz",[]) if entry["status"]=="pending" else [],
            "generatedSourceDrafts":generated,
            "officialHeritageSources":sites[:5],
            "officialTopicSources":authorities.get(code,[]),
            "topicSourceDiscoveryRequired":bool(topic_days and not authorities.get(code)),
            "editorialReviewRequired":True,"publicationEligible":False,
        })
    return {"editionDate":day.isoformat(),"articleCountries":targets,
            "countriesNeedingMaterials":len(tasks),"tasks":tasks,
            "publicationEligible":False}


def prepare_material_bundle(root, stories, day, report, output, *, heritage_sites=None,
                            write_previews=write_bundle, article_recovery=False,
                            prior=None):
    output=Path(output)
    tasks=material_tasks(root,stories,day,heritage_sites=heritage_sites)
    save(output/"material-tasks.json",tasks)
    canonical=load_country_content(root)["countries"]
    pending={row["countryCode"] for row in tasks["tasks"] if row["status"]=="pending"}
    # Do not enqueue other pending countries or cap article countries at 20.
    queue=[row for row in make_queue(report,canonical,allow_partial=article_recovery)
           if row["code"] in pending]
    if article_recovery:
        from country_article_recovery import write_article_previews
        preview_summary=write_article_previews(queue,output/"photo-review",tasks["editionDate"],prior=prior)
    else:
        preview_summary=write_previews(queue,output/"photo-review",len(queue))
    save(output/"material-summary.json",{
        "editionDate":tasks["editionDate"],
        "articleCountries":tasks["articleCountries"],
        "countriesNeedingMaterials":tasks["countriesNeedingMaterials"],
        "pendingCountryCodes":sorted(pending),
        "topicCountryCodes":[r["countryCode"] for r in tasks["tasks"] if r["missingTopicDates"]],
        "photoReview":preview_summary,"publicationEligible":False,
    })
    return tasks
