#!/usr/bin/env python3
"""Free-tier AI editorial pipeline. Fail closed: no key, no verified three, no publication."""
import json, os, re, sys, ipaddress, socket, time
from html.parser import HTMLParser
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

JST=ZoneInfo("Asia/Tokyo")
MODEL=os.getenv("GEMINI_MODEL","gemini-3.5-flash-lite")
KEY=os.getenv("GEMINI_API_KEY","")
REQUIRED=("id","country","category","categoryLabel","label","title","summary","detail","quip","sourceName","sourceUrl","reported")
BLOCK=re.compile(r"死亡|殺害|負傷|災害|差別|自殺|銃撃|戦争|死者|犠牲者|killed|murder|fatal|death|died|suicide|rape|shooting|injured|hospitalized|war|bombing|disaster",re.I)
# Rank incident-specific reporting ahead of generic world-news headlines.
# Ranking only changes retrieval order; it never certifies a fact or relaxes review.
EDITORIAL_MISSION=("Publish only real, consequential failures, misjudgments and plans that backfired. "
    "Every story must have three inseparable parts: independently supported facts about a failure; "
    "a warm, witty AI quip aimed at the decision, contradiction or overconfidence rather than a victim; "
    "and a concrete reframing that helps a reader who failed today feel that setbacks are survivable. "
    "Never replace a failure with generic surprising, uplifting or quirky news merely to fill three slots. "
    "Search across continents and languages; prefer geographic variety when evidence and editorial quality are comparable. "
    "Never use geography as a substitute for a real failure, independent verification, or humane humor. "
    "Do not invent a happy ending, recovery, quote or fact. A reframing is editorial interpretation, not reporting.")
INCIDENT_TERMS=re.compile(r"\b(accidentally|mistak(?:e|en)|mix.?up|blunder|error|wrong|failed|failure|apolog(?:y|ise|ize)|revers(?:e|al)|scrap(?:ped)?|cancel(?:led|ed)|recall|outage|glitch|misplac(?:ed)?|misprint|confus(?:ion|ed)|fiasco|oversight|backfir(?:e|ed)|botch(?:ed)?|miscalculat(?:e|ed|ion))\b|手違い|誤発注|間違|失敗|謝罪|撤回|中止|障害|誤送信|ミス|실수|착각|Verwechslung|par erreur|equivocaci[oó]n|por engano",re.I)

def incident_priority(lead):
    title=lead.get("title","")
    return (0 if INCIDENT_TERMS.search(title) else 1,
            1 if host(lead.get("url",""))=="news.google.com" else 0)


def host(url):
    try:
        p=urlsplit(url)
        return p.hostname.lower().removeprefix("www.") if p.scheme=="https" and p.hostname and not p.username else ""
    except ValueError:return ""

class ArticleText(HTMLParser):
    """Extract visible prose from a publisher article container, not navigation."""
    def __init__(self):
        super().__init__()
        self.parts=[]
        self.hidden=0
        self.article_depth=0
        self.article_parts=[]
        self.article_containers=0
        self.stack=[]
    def handle_starttag(self,tag,attrs):
        attributes=dict(attrs)
        classes=attributes.get("class","").split()
        guardian_body=attributes.get("data-gu-name")=="body"
        # Publisher layouts vary; only explicitly article-scoped containers count.
        article_body=(tag=="article" or guardian_body or
                      any(c in classes for c in ("article-body","article__body",
                          "article-content","article__content","story-body",
                          "story__body","story-content","entry-content",
                          "articleBody","article-text","body-content")) or
                      attributes.get("itemprop")=="articleBody" or
                      attributes.get("data-testid") in ("article-body","article-content"))
        self.stack.append((tag,article_body))
        if article_body:
            self.article_depth+=1
            self.article_containers+=1
        if tag in ("script","style","noscript","svg","nav","footer","header","aside"):
            self.hidden+=1
    def handle_endtag(self,tag):
        # HTML in the wild may be imperfect; only unwind matching open tags.
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i][0]==tag:
                popped=self.stack[i:]
                self.stack=self.stack[:i]
                for old_tag,is_article in popped:
                    if is_article:self.article_depth=max(0,self.article_depth-1)
                    if old_tag in ("script","style","noscript","svg","nav","footer","header","aside"):
                        self.hidden=max(0,self.hidden-1)
                break
    def handle_data(self,data):
        if self.hidden or not data.strip():return
        value=data.strip()
        self.parts.append(value)
        if self.article_depth:self.article_parts.append(value)

def extracted_article_text(html):
    parser=ArticleText()
    parser.feed(html)
    # Prefer the publisher's article container; reject generic site chrome.
    if parser.article_containers:
        return " ".join(parser.article_parts)
    return ""

def public_host(url):
    domain=host(url)
    if not domain or domain in ("localhost",) or domain.endswith((".local",".internal")):return False
    try:
        addresses=socket.getaddrinfo(domain,443,type=socket.SOCK_STREAM)
        return bool(addresses) and all(ipaddress.ip_address(x[4][0]).is_global for x in addresses)
    except (OSError,ValueError):return False

def source_text(url, diagnostics=None):
    # Only public HTTPS URLs from the collected lead list may be fetched.
    if not public_host(url):
        if diagnostics is not None:diagnostics.append("blocked_host")
        return ""
    class SafeRedirect(__import__("urllib.request",fromlist=["HTTPRedirectHandler"]).HTTPRedirectHandler):
        def redirect_request(self,req,fp,code,msg,headers,newurl):
            if not public_host(newurl):raise ValueError("unsafe_redirect")
            return super().redirect_request(req,fp,code,msg,headers,newurl)
    from urllib.request import build_opener
    opener=build_opener(SafeRedirect)
    req=Request(url,headers={
        "User-Agent":"Mozilla/5.0 (compatible; Yoru9EditorialResearch/1.0)",
        "Accept":"text/html,application/xhtml+xml;q=0.9",
        "Accept-Language":"en-GB,en;q=0.8",
    })
    try:
        with opener.open(req,timeout=7) as response:
            if "text/html" not in response.headers.get("Content-Type",""):
                if diagnostics is not None:diagnostics.append("non_html")
                return ""
            raw=response.read(180000)
        text=extracted_article_text(raw.decode("utf-8",errors="replace"))
        if len(text)<600:
            if diagnostics is not None:diagnostics.append("short_html")
            return ""
        if diagnostics is not None:diagnostics.append("fetched")
        return text[:13000]
    except HTTPError as exc:
        if diagnostics is not None:diagnostics.append("http_"+str(exc.code))
        return ""
    except (OSError,ValueError,URLError) as exc:
        if diagnostics is not None:diagnostics.append(type(exc).__name__)
        return ""

def available_models():
    """List supported models, with a bounded preference order and no paid fallback."""
    endpoint="https://generativelanguage.googleapis.com/v1beta/models?pageSize=100"
    req=Request(endpoint,headers={"x-goog-api-key":KEY})
    with urlopen(req,timeout=25) as response:
        catalog=json.load(response)
    models=[m["name"] for m in catalog.get("models",[])
            if "generateContent" in m.get("supportedGenerationMethods",[])
            and m.get("name","").startswith("models/gemini-")]
    preferred=[MODEL,"gemini-3.5-flash-lite","gemini-3.5-flash","gemini-2.5-flash-lite","gemini-2.5-flash",
               "gemini-2.0-flash-lite","gemini-2.0-flash"]
    result=[]
    for name in preferred:
        full="models/"+name
        if full in models and full not in result:result.append(full)
    if not result:raise RuntimeError("No supported Gemini model found; safe stop")
    return result[:3]

def available_model():
    return available_models()[0]

ACTIVE_MODEL=None

def ai(prompt):
    global ACTIVE_MODEL
    if not KEY:raise RuntimeError("GEMINI_API_KEY not configured; no publication")
    models=available_models()
    if ACTIVE_MODEL in models:
        models=[ACTIVE_MODEL]+[model for model in models if model!=ACTIVE_MODEL]
    data={"contents":[{"parts":[{"text":prompt}]}],
          "generationConfig":{"responseMimeType":"application/json","temperature":0.1}}
    last_error=None
    for model in models:
        for version in ("v1beta","v1"):
            url="https://generativelanguage.googleapis.com/"+version+"/"+model+":generateContent"
            req=Request(url,data=json.dumps(data).encode(),
                        headers={"Content-Type":"application/json","x-goog-api-key":KEY},method="POST")
            try:
                with urlopen(req,timeout=90) as response:result=json.load(response)
                raw=result["candidates"][0]["content"]["parts"][0]["text"]
                ACTIVE_MODEL=model
                print("Gemini generation succeeded:",model,version,flush=True)
                return json.loads(raw)
            except HTTPError as exc:
                # Print only status and sanitized provider reason, never headers or key.
                try:
                    err=json.loads(exc.read(4096).decode("utf-8"))
                    status=str(err.get("error",{}).get("status","UNKNOWN"))[:50]
                    message=str(err.get("error",{}).get("message",""))[:320]
                    message=re.sub(r"AIza[A-Za-z0-9_-]{20,}", "[REDACTED_KEY]", message)
                    message=re.sub(r"key=[^&\\s]+", "key=[REDACTED]", message,flags=re.I)
                except (ValueError,UnicodeError,AttributeError):status="UNKNOWN";message="unavailable"
                print("Gemini generation failed:",model,version,"HTTP",exc.code,status,"reason:",message,flush=True)
                last_error=exc.code
                if exc.code in (429,500,502,503,504):
                    # One bounded retry for temporary capacity failures; never bypass checks.
                    time.sleep(3)
                    try:
                        with urlopen(req,timeout=90) as response:result=json.load(response)
                        raw=result["candidates"][0]["content"]["parts"][0]["text"]
                        ACTIVE_MODEL=model
                        print("Gemini generation succeeded after transient retry:",model,version,flush=True)
                        return json.loads(raw)
                    except HTTPError as retry_exc:
                        last_error=retry_exc.code
                        print("Gemini transient retry failed:",model,version,"HTTP",retry_exc.code,flush=True)
                        if retry_exc.code not in (400,404,429,500,502,503,504):raise RuntimeError("Gemini API HTTP "+str(retry_exc.code))
                    except (URLError,TimeoutError) as retry_exc:
                        print("Gemini transient retry failed:",type(retry_exc).__name__,flush=True)
                    break
                if exc.code not in (404,400):raise RuntimeError("Gemini API HTTP "+str(exc.code))
    raise RuntimeError("No available model/version generated content; last HTTP "+str(last_error))

def archive_summaries():
    result=[]
    for file in Path("data/archive").glob("????-??-??.json"):
        try:
            for story in json.loads(file.read_text()).get("stories",[]):
                result.append({"title":story.get("title",""),"summary":story.get("summary",""),"country":story.get("country","")})
        except (ValueError,OSError):continue
    return result[-250:]

def previous_events():
    seen=set()
    for file in Path("data/archive").glob("????-??-??.json"):
        try:
            for story in json.loads(file.read_text()).get("stories",[]):
                seen.add(story.get("sourceUrl",""))
                seen.add(story.get("id",""))
        except (ValueError,OSError):continue
    return seen

# Similar headlines help discovery, but are not proof of corroboration.
STOPWORDS=set("the a an and or of to in on for with from at by as is are was were after before new latest says say report reports news world today update video live how why what who where this that about into over under amid".split())

def title_terms(title):
    return {w for w in re.findall(r"[a-z0-9]{3,}",title.lower()) if w not in STOPWORDS}

def corroboration_groups(items):
    """Group potentially matching incidents across distinct publisher domains."""
    groups=[]
    for i,item in enumerate(items):
        terms=title_terms(item["title"])
        if len(terms)<3:continue
        matches=[item]
        for other in items[i+1:]:
            if host(other["url"])==host(item["url"]):continue
            other_terms=title_terms(other["title"])
            shared=terms & other_terms
            if len(shared)>=3 and len(shared)/max(1,min(len(terms),len(other_terms)))>=0.45:
                matches.append(other)
        if len(matches)>=2:groups.append(matches[:4])
    unique={}
    for group in groups:
        key=tuple(sorted(x["url"] for x in group))
        unique[key]=group
    return list(unique.values())[:48]

def select_distinct_groups(groups, limit=24):
    """Choose many non-overlapping source groups without first-match bias.

    Candidate pairs are discovery hypotheses, not verified incidents. Keep
    publisher independence and let the later editorial/audit stages decide
    whether each group actually corroborates an event.
    """
    candidates=[]
    seen=set()
    for group in groups:
        urls=frozenset(item["url"] for item in group)
        if len(urls)<2 or len({host(url) for url in urls})<2 or urls in seen:
            continue
        seen.add(urls)
        candidates.append((group,urls))
    # Explore both taking and skipping a group. Bounded beam search prevents
    # a large early group from suppressing several independent later pairs.
    # Prefer groups with more independent sources when counts are tied.
    states=[((),frozenset())]
    for index,(_,urls) in enumerate(candidates):
        next_states=list(states)
        for chosen,used in states:
            if len(chosen)<limit and used.isdisjoint(urls):
                next_states.append((chosen+(index,),used|urls))
        next_states.sort(key=lambda state:(
            -len(state[0]),
            sum(len(candidates[i][1]) for i in state[0]),
            state[0]))
        # Retain distinct used-URL sets to preserve alternate future choices.
        unique={}
        for state in next_states:
            unique.setdefault(state[1],state)
            if len(unique)>=128:
                break
        states=list(unique.values())
    best=min(states,key=lambda state:(
        -len(state[0]),
        sum(len(candidates[i][1]) for i in state[0]),
        state[0]))
    return [candidates[i][0] for i in best[0]]

def semantic_corroboration_groups(items):
    """AI proposes pairs, but exact source URLs and distinct hosts are enforced locally."""
    if len(items)<2:return []
    compact=[{"title":x["title"],"url":x["url"],"excerpt":x["text"][:2400]} for x in items[:120]]
    result=ai("Find pairs of articles about the SAME specific incident, not merely the same topic. Include independently reported individual mishaps and consequential personal decisions, not only corporate or government events. "
        "Compare concrete people, places, actions and dates in the supplied excerpts. "
        "Two sources must be editorially independent, not syndicated rewrites. "
        "When uncertain, omit the pair. Return JSON object with pairs array of objects "
        "{urls:[exact_source_url_1,exact_source_url_2]}. No invented URLs. Evidence: "
        +json.dumps(compact,ensure_ascii=False))
    pairs=result.get("pairs",[])
    if not isinstance(pairs,list):return []
    by_url={x["url"]:x for x in items}
    groups=[]
    seen=set()
    for pair in pairs[:48]:
        if not isinstance(pair,dict):continue
        urls=pair.get("urls")
        if not isinstance(urls,list) or len(urls)!=2 or not all(isinstance(u,str) for u in urls):continue
        if any(u not in by_url for u in urls) or len({host(u) for u in urls})!=2:continue
        key=tuple(sorted(urls))
        if key in seen:continue
        seen.add(key)
        groups.append([by_url[u] for u in urls])
    return groups[:36]

def valid_recent_reported(raw, now):
    """Allow only an explicit calendar date in the last seven days (JST)."""
    if not isinstance(raw,str) or not re.fullmatch(r"\d{4}[-.]\d{2}[-.]\d{2}",raw):return False
    try:reported=datetime.strptime(raw.replace(".","-"),"%Y-%m-%d").date()
    except ValueError:return False
    return now.date()-timedelta(days=7)<=reported<=now.date()

def main():
    now=datetime.now(JST)
    day=now.date().isoformat()
    if not KEY:
        print("No free-tier AI key configured. Safe skip.");return 0
    leads=json.loads(Path("data/candidates.json").read_text()).get("candidates",[])
    recent=[]
    for lead in leads:
        try:
            raw=lead["seendate"]
            if re.fullmatch(r"\d{8}T\d{6}Z",raw):
                stamp=datetime.strptime(raw,"%Y%m%dT%H%M%SZ").replace(tzinfo=ZoneInfo("UTC")).astimezone(JST)
            else:
                stamp=datetime.fromisoformat(raw.replace("Z","+00:00")).astimezone(JST)
            if not (now - timedelta(days=7) <= stamp <= now + timedelta(minutes=10)):continue
        except (KeyError,ValueError,TypeError):continue
        if host(lead.get("url","")) and not BLOCK.search(lead.get("title","")):recent.append(lead)
    if len(recent)<5:
        print("Not enough recent leads within seven days; safe skip.");return 0
    # Collect actual article bodies before asking the model to draft.
    cache={}
    source_leads=[]
    # Prioritize direct publisher URLs; interleave domains to avoid source monopolies.
    buckets={}
    for lead in sorted(recent,key=incident_priority):
        buckets.setdefault(host(lead['url']),[]).append(lead)
    ordered=[]
    # A single host (notably news.google.com) must never exhaust the fetch budget.
    # Preserve slots for independent publisher articles across multiple feeds.
    per_host={}
    while buckets and len(ordered)<240:
        progressed=False
        for domain in list(buckets):
            limit=5 if domain=="news.google.com" else 30
            if per_host.get(domain,0)>=limit:
                del buckets[domain]
                continue
            if buckets[domain]:
                ordered.append(buckets[domain].pop(0))
                per_host[domain]=per_host.get(domain,0)+1
                progressed=True
            if not buckets[domain]:del buckets[domain]
            if len(ordered)>=240:break
        if not progressed:break
    outcomes={}
    failure_reasons={}
    for lead in ordered:
        provider=lead.get('provider','unknown')
        label='Google RSS' if provider.startswith('Google') else ('BBC RSS' if provider.startswith('BBC') else ('Guardian RSS' if provider.startswith('The Guardian') else ('GDELT' if provider.startswith('GDELT') else 'Other')))
        outcomes.setdefault(label,[0,0])
        outcomes[label][0]+=1
        url=lead['url']
        if url not in cache:
            diagnostics=[]
            cache[url]=source_text(url,diagnostics)
            reason=diagnostics[0] if diagnostics else 'unknown'
            failure_reasons.setdefault(label,{})[reason]=failure_reasons.setdefault(label,{}).get(reason,0)+1
        if cache[url]:outcomes[label][1]+=1
        if cache[url]:source_leads.append({'title':lead['title'],'url':url,'publisher':lead.get('domain',''),'text':cache[url][:8500]})
    print('Evidence collection:',len(recent),'recent seven-day leads,',len(source_leads),'fetchable article bodies',flush=True)
    print('Article retrieval by provider (attempted, fetched):',json.dumps(outcomes,sort_keys=True),flush=True)
    print('Article retrieval diagnostic counts (no URLs or article text):',json.dumps(failure_reasons,sort_keys=True),flush=True)
    if len(source_leads)<2:
        print('Fewer than two article bodies; safe skip before AI generation.');return 0
    groups=corroboration_groups(source_leads)
    print('Cross-publisher headline groups:',len(groups),flush=True)
    # Headline overlap is only a discovery heuristic. Even when it finds five
    # candidates, semantic matching can find additional consequential incidents
    # described with different wording by independent publishers.
    # Keep the bounded candidate budget; final publication still requires
    # two fetched sources and an independent adversarial AI audit.
    print('Trying AI semantic incident matching to supplement headline groups.',flush=True)
    semantic=semantic_corroboration_groups(source_leads)
    existing={tuple(sorted(x['url'] for x in group)) for group in groups}
    for group in semantic:
        key=tuple(sorted(x['url'] for x in group))
        if key not in existing:
            groups.append(group)
            existing.add(key)
    raw_group_count=len(groups)
    groups=select_distinct_groups(groups,limit=36)
    print('Combined cross-publisher groups:',len(groups),'distinct from',raw_group_count,'overlapping candidates',flush=True)
    if len(groups)<3:
        print('Fewer than three independently sourced incident groups; safe skip.');return 0
    # Preserve each hypothesized incident's exact article-to-article association.
    # A flat article list can hide which sources are meant to corroborate one another.
    grouped_evidence=[{"groupId":i+1,"articles":[{"title":item["title"],
        "url":item["url"],"text":item["text"][:4800]} for item in group]}
        for i,group in enumerate(groups[:24])]
    # Preserve allowed corroboration pairs: a model must not combine unrelated sources.
    allowed_pairs=set()
    for group in groups[:36]:
        for i,first in enumerate(group):
            for second in group[i+1:]:
                if host(first["url"])!=host(second["url"]):
                    allowed_pairs.add(frozenset((first["url"],second["url"])))
    grouped_urls={item["url"] for group in groups for item in group}
    grouped_sources=[item for item in source_leads if item["url"] in grouped_urls]
    prompt=(EDITORIAL_MISSION+' You are editor A. Return JSON object with stories array of up to 16 Japanese stories about CONSEQUENTIAL, well-documented failures by ordinary individuals, workers, entrepreneurs, companies, institutions, governments or prominent decision-makers. Include personal decisions that backfired (such as work, career, business, purchases or everyday judgment), costly mistakes, public policy reversals, operational breakdowns and ambitious plans that backfired. Give individual incidents equal editorial consideration; do not require celebrity, high financial stakes or institutional status. Do not impose a fixed category quota or lower evidence standards to fill a category. The purpose is to help readers facing serious personal difficulties regain perspective: even powerful organizations make mistakes, and setbacks can be survived. Do not prioritize trivial typos or harmless oddities merely because they are easy to joke about. A personally meaningful mistake can be consequential without being nationally important. '
      'Use ONLY supplied fetched article texts, never external knowledge. Only draft stories corroborated by TWO independent publisher articles describing the SAME incident. '
      'verificationUrls must be exact URLs present in evidence, on distinct domains. Do not invent facts, URLs or unsupported details. '
      'For each include required fields '+str(REQUIRED)+', verificationUrls (2 URLs), eventKey (normalized incident identifier), evidence (facts corroborated by both). '
      'CRITICAL OUTPUT SCHEMA: category MUST be exactly one of person, work, company (lowercase English), NEVER government, politics, institution, business, organization or any Japanese category value. Use company for corporate and institutional failures INCLUDING government agencies, public institutions and large organizations; use work for workplace or operational mistakes; use person for individual decision-maker mistakes. categoryLabel is the human-readable Japanese label, not category. Do not alter these enum values even when the subject is consequential or political. '
      'For each story, make the quip an affectionate, pointed observation about the verified mistake; in the detail or summary, offer a specific perspective shift for readers who are worried about their own failure. Do not make empty motivational claims, imply an unreported recovery, or treat the mistake as harmless when it was not. Reject generic surprising news without a real failure, even if it is funny. Before rejecting an otherwise well-sourced failure for no_respectful_comic_angle, explore at least two different safe comic targets (the plan versus reality, the mistaken assumption versus the outcome); if neither works, reject it. ' 
      'Serious stakes are welcome, but NEVER mock victims, casualties, poverty, illness or vulnerable people. For individuals, humor should target a relatable miscalculation, ironic outcome or overconfidence rather than their identity, appearance, hardship or vulnerability; avoid invasive private-life details and public shaming. For institutions, target flawed plans, contradictions and decisions, not those harmed. Exclude incidents where a respectful comic angle cannot be supported. No death, injuries, abuse or humiliation in the chosen story or quip. Edition date JST: '+day+'. Stories must have a verifiable reported date within the preceding seven days; do not confuse edition date with reporting date. '
      'Each group is only a hypothesis: check that its articles actually describe the same specific event, and that the reported date is explicit in the supplied article text. '
      'Return JSON with stories array AND diagnostics array containing one object for every input group: '
      '{groupId:integer,eligible:boolean,reasonCode:string}. Use ONLY these reasonCode values: '
      'same_incident_supported, unrelated_articles, syndicated_or_not_independent, no_explicit_recent_report_date, '
      'insufficient_facts, sensitive_incident, no_respectful_comic_angle, other. Do not reject an incident merely for being consequential or financially serious; reject only if there is no respectful, constructive comic angle. '
      'A group marked eligible still needs all story fields and independent verification; do not fill gaps by inference. '
      'Candidate groups with their own article bodies (NOT proof): '+json.dumps(grouped_evidence,ensure_ascii=False))
    draft_response=ai(prompt)
    draft=draft_response.get("stories",[]) if isinstance(draft_response,dict) else []
    if not isinstance(draft,list):
        print("Editorial drafting diagnostic: malformed stories response; safe skip.",flush=True)
        return 0
    # Diagnostics are model assessments, not factual verification. Never use them
    # to approve an article or to weaken any subsequent independent check.
    diagnostics=draft_response.get("diagnostics",[]) if isinstance(draft_response,dict) else []
    valid_codes={"same_incident_supported","unrelated_articles","syndicated_or_not_independent",
        "no_explicit_recent_report_date","insufficient_facts","sensitive_incident",
        "no_respectful_comic_angle","other"}
    group_reasons={}
    if isinstance(diagnostics,list):
        for item in diagnostics[:len(grouped_evidence)]:
            if not isinstance(item,dict):continue
            group_id=item.get("groupId")
            code=item.get("reasonCode")
            if type(group_id) is int and 1<=group_id<=len(grouped_evidence) and code in valid_codes:
                group_reasons[group_id]=code
    print("AI candidate group assessment:",json.dumps({
        "assessed":len(group_reasons),
        "total":len(grouped_evidence),
        "reason_counts":{code:list(group_reasons.values()).count(code) for code in sorted(set(group_reasons.values()))}
    },sort_keys=True),flush=True)
    if len(draft)<3:
        # Separate diagnosis from drafting. A large all-groups request can
        # return only diagnostics, even when some groups are draftable.
        # Retry in small, independent batches; the same downstream source,
        # date, safety and second-AI verification gates still apply.
        # Diagnostics from the first model call are not a veto. In practice a
        # diagnostics-heavy response can label every group "other" or reject
        # viable stories without drafting them. Give each candidate a focused
        # drafting chance; the deterministic and independent audit gates below
        # remain unchanged.
        retry_candidates=list(grouped_evidence)
        print("Supplementing insufficient editorial drafts one incident at a time:",
              len(retry_candidates),flush=True)
        for start in range(0,min(len(retry_candidates),18)):
            batch=retry_candidates[start:start+1]
            retry_prompt=(EDITORIAL_MISSION+
                " You are editor A. Draft up to three Japanese news stories ONLY "
                "when two independent publisher articles in the SAME input group "
                "corroborate the same specific real-world mistake. "
                "Return JSON object with stories array. Do not return diagnostics. "
                "If evidence is insufficient, return an empty stories array. "
                "Each story must contain fields "+str(REQUIRED)+
                ", verificationUrls (exact two supplied URLs from that group), "
                "eventKey (specific incident identifier at least 12 characters), "
                "and evidence (facts supported by both articles). "
                "category must be exactly person, work, or company. "
                "reported must be an explicit source-supported date within the "
                "last seven days, formatted YYYY-MM-DD. "
                "Use warm humor about the mistake, never victims or suffering; "
                "give readers perspective without inventing outcomes. "
                "Do not infer any fact absent from the supplied text. "
                "Edition date JST: "+day+
                ". Candidate groups (hypotheses, NOT proof): "+
                json.dumps(batch,ensure_ascii=False))
            try:
                retry_result=ai(retry_prompt)
                retry_stories=retry_result.get("stories",[]) if isinstance(retry_result,dict) else []
                if isinstance(retry_stories,list):
                    draft.extend(retry_stories[:3])
                print("Small-batch draft count:",len(retry_stories) if isinstance(retry_stories,list) else 0,flush=True)
            except (RuntimeError,ValueError,KeyError,TypeError) as exc:
                print("Small-batch draft failed:",type(exc).__name__,flush=True)
            if len(draft)>=6:
                break
    if not draft:
        # A successful API call can legitimately return zero verifiable stories.
        # Log only bounded metadata, not untrusted article text or AI prose.
        print("Editorial drafting diagnostic:",json.dumps({
            "candidate_groups":len(groups),
            "group_domain_counts":[len({host(x["url"]) for x in group}) for group in groups[:36]],
            "group_article_counts":[len(group) for group in groups[:36]],
            "source_articles":len(grouped_sources),
            "drafted":0,
            "response_keys":sorted(k for k in draft_response if k in ("stories","status","reason","reasons","diagnostics")),
            "has_model_explanation":any(k in draft_response for k in ("reason","reasons","diagnostics"))
        },sort_keys=True),flush=True)
        print("No draft stories generated; evidence must not be promoted to publication.",flush=True)
        return 0
    seen=previous_events()
    selected=[]
    # Only aggregate rejection categories, never article text or model free-form reasons.
    rejection_counts={}
    def reject(reason):
        rejection_counts[reason]=rejection_counts.get(reason,0)+1
    past=archive_summaries()
    accepted_summaries=[]
    lead_urls={x['url'] for x in source_leads}
    for story in draft:
        if not isinstance(story,dict) or any(not isinstance(story.get(k),str) or not story[k].strip() for k in REQUIRED):
            reject("missing_required_fields");continue
        if not valid_recent_reported(story["reported"],now):
            reject("invalid_reporting_date");continue
        if story["category"] not in ("person","work","company"):
            reject("invalid_category");continue
        urls=story.get("verificationUrls",[])
        if not isinstance(urls,list) or len(urls)<2 or len(set(host(u) for u in urls))<2 or not all(host(u) for u in urls):
            reject("insufficient_independent_urls");continue
        if not any(frozenset(pair) in allowed_pairs for pair in __import__("itertools").combinations(urls,2)):
            reject("unmatched_source_pair");continue
        if story["sourceUrl"] not in urls or any(u not in lead_urls for u in urls):
            reject("urls_not_in_fetched_evidence");continue
        if story["sourceUrl"] in seen or story["id"] in seen:
            reject("previously_published");continue
        if BLOCK.search(" ".join(str(story[k]) for k in ("title","summary","detail","quip"))):
            reject("sensitive_content");continue
        event=story.get("eventKey")
        if not isinstance(event,str) or len(event)<12:
            reject("invalid_event_key");continue
        if event in seen:
            reject("duplicate_event");continue
        # Both independent source pages must be actually retrieved, not merely named by AI.
        evidence=[]
        for url in urls[:3]:
            if cache[url]:evidence.append({"url":url,"text":cache[url]})
        if len(evidence)<2 or len({host(x["url"]) for x in evidence})<2:
            reject("insufficient_fetched_articles");continue
        audit=ai(EDITORIAL_MISSION+" You are independent adversarial fact checker B. You must verify every concrete "
          "claim in this Japanese article against the TWO separately fetched source article texts below. "
          "Reject unsupported claims, syndicated duplicate reporting, mismatched dates, invented quotes, "
          "unsafe jokes, generic news without a genuine failure, missing compassionate reframing, and repeated events. An ordinary individual's consequential, independently documented mistake is as eligible as a serious corporate or institutional failure when the humor targets a decision, irony or overconfidence rather than a victim or private vulnerability. Do not reject solely because the subject is not famous or the consequences are personal, financially serious or politically significant. Reject humiliating exposure of private individuals and unsupported personal details. Compare against the prior published events and already selected events, "
          "reject the same underlying incident even if the title, source, language or URL differs. "
          "Reject if evidence is insufficient or unclear. "
          "Output only JSON {approved:boolean,reason:string}. Article: "
          +json.dumps(story,ensure_ascii=False)+" Previously published events: "
          +json.dumps(past,ensure_ascii=False)+" Already selected today: "
          +json.dumps(accepted_summaries,ensure_ascii=False)+" Independently fetched sources: "
          +json.dumps(evidence,ensure_ascii=False))
        if audit.get("approved") is not True:
            # Free-form AI reasons are not logged; only bounded, diagnostic labels.
            reason=str(audit.get("reason","")).lower()[:500]
            if any(w in reason for w in ("date","time","old","recent")):category="audit_date"
            elif any(w in reason for w in ("same incident","duplicate","repeat","previous","syndicat")):category="audit_duplicate_or_syndication"
            elif any(w in reason for w in ("joke","humor","harm","unsafe","sensitive","victim")):category="audit_safety"
            elif any(w in reason for w in ("source","evidence","corroborat","unsupported","fact","verify","claim")):category="audit_evidence"
            else:category="audit_other_or_unspecified"
            reject(category);continue
        story["editorVerified"]=True
        story["humorSafe"]=True
        seen.update((story["sourceUrl"],story["id"],event))
        selected.append(story)
        accepted_summaries.append({"title":story["title"],"summary":story["summary"],"country":story["country"]})
        if len(selected)==3:break
    print("Editorial decision counts:",json.dumps({"drafted":len(draft),"approved":len(selected),"rejected":rejection_counts},sort_keys=True),flush=True)
    if len(selected)!=3:
        print("Two-stage verification did not approve exactly three; no publication.");return 0
    payload={"status":"approved","editionDate":day,"editionType":"regular","title":day+"｜本日の3大ニュース",
      "editorApproved":True,"factChecked":True,"humorReviewed":True,"approvedBy":"automated-two-stage-review","stories":selected}
    target=Path("data/approved")/(day+".json")
    if target.exists():return 0
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n")
    print("Created three-story AI issue",day)
    return 0

if __name__=="__main__":
    try:sys.exit(main())
    except Exception as e:
        print("Fail-closed AI review:",type(e).__name__,str(e),file=sys.stderr)
        sys.exit(1)
