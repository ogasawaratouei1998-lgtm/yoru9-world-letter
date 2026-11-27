"""Generate source-bound country copy from structured UNESCO property records.

The generated drafts contain only facts explicitly present in the official feed.
They never approve a country, assign a photograph or claim local travel safety.
"""
from datetime import date
from urllib.parse import urlsplit
import re


def official_property_rows(sites):
    result=[]
    seen=set()
    for site in sites:
        if not isinstance(site,dict):
            continue
        url=site.get("sourceUrl","")
        name=site.get("name","")
        if not isinstance(url,str) or not isinstance(name,str):
            continue
        parsed=urlsplit(url)
        if (parsed.scheme!="https" or parsed.netloc!="whc.unesco.org"
                or not re.fullmatch(r"/en/list/[1-9][0-9]*/",parsed.path)
                or parsed.query or parsed.fragment or not 1<=len(name.strip())<=180
                or url in seen):
            continue
        seen.add(url)
        result.append({"name":name.strip(),"sourceUrl":url,
                       "inscribedYear":site.get("inscribedYear")})
    return result


def generate_heritage_drafts(country, sites, day):
    """Use the official names verbatim until a Japanese rendering is reviewed."""
    day=date.fromisoformat(day) if isinstance(day,str) else day
    rows=official_property_rows(sites)
    if not rows:
        return {"portraitDraft":None,"travelDrafts":[],"quizDrafts":[],
                "status":"official_sources_unavailable","publicationEligible":False}
    names="、".join("「"+r["name"]+"」" for r in rows[:2])
    portrait={
        "lead":country+"の世界遺産を資料から訪ねる",
        "body":country+"について、UNESCOの公式世界遺産一覧を入口に文化や自然を考えます。登録資産として"+names+"が掲載されています。地図と公式資料を見比べながら、それぞれの場所がどのような背景を持つのかを読み解く誌上の小旅行です。現地の安全、公開時間、立入条件はこの資料だけでは確認できません。",
        "facts":["UNESCO登録資産："+r["name"] for r in rows[:2]],
        "photos":[],"sourceName":"UNESCO世界遺産センター",
        "sourceUrl":rows[0]["sourceUrl"],
    }
    travel=[];quizzes=[]
    for row in rows[:2]:
        title=row["name"]
        year=row["inscribedYear"]
        fact="UNESCOの公式世界遺産一覧には「"+title+"」が掲載されています。"
        if type(year) is int and 1978<=year<=day.year:
            fact+="登録年は"+str(year)+"年です。"
            options=[str(y)+"年" for y in (year,year-1,year-2)]
            quizzes.append({"question":"「"+title+"」の世界遺産登録年は？",
                            "options":options,"answer":0,"fact":fact,
                            "sourceUrl":row["sourceUrl"],"photoStatus":"unreviewed"})
        travel.append({"title":title,"paragraphs":[
            "公式世界遺産一覧に掲載された「"+title+"」を地図と資料でたどります。場所の成り立ちや周囲の風景については、現地の写真や管理機関の説明と照合しながら読み進めます。写真だけから建物の用途や自然環境の詳細を推測せず、資料に書かれた事実と区別して理解するための入口です。",
            fact+"世界遺産登録の背景や保全の状況については、公式の個別資料を参照して確かめます。今回の下書きは現地への訪問を勧めるものではなく、地理や歴史を学ぶための資料紹介です。具体的な交通、公開時間、施設への立入りについては別途確認が必要です。"],
            "sourceName":"UNESCO世界遺産センター","sourceUrl":row["sourceUrl"],
            "sourceCheckedOn":day.isoformat(),"photoStatus":"unreviewed",
            "editorialOnly":True})
    return {"portraitDraft":portrait,"travelDrafts":travel,"quizDrafts":quizzes,
            "status":"source_bound_draft_requires_copy_and_visual_review",
            "publicationEligible":False}
