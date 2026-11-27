"""Same-day editorial continuation; no article text, titles, drafts or approval flags.

Only public publisher links for pending articles and opaque digests of attempted
URLs are stored. The queue is a scheduling hint, never a news approval decision.
"""
import hashlib
import json
import os
from pathlib import Path
from trusted_originals import trusted_original_domain

MAX_PENDING=128
MAX_ATTEMPTED=512

def fingerprint(url):
    return hashlib.sha256(url.encode("utf-8")).hexdigest()

class EditorialResume:
    def __init__(self,day,path=None):
        self.day=day
        self.path=Path(path) if path else None
        self.pending={}
        self.attempted=set()
        if not self.path:
            return
        try:
            if self.path.stat().st_size>512000:return
            raw=json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw,dict) or raw.get("day")!=day or raw.get("version")!=1:return
            for row in raw.get("pending",[])[:MAX_PENDING]:
                if not isinstance(row,dict):continue
                url=row.get("url")
                stamp=row.get("seendate")
                if (isinstance(url,str) and len(url)<=1500 and trusted_original_domain(url)
                        and isinstance(stamp,str) and 0<len(stamp)<=30):
                    self.pending[url]={"url":url,"seendate":stamp}
            self.attempted={x for x in raw.get("attempted",[])[:MAX_ATTEMPTED]
                            if isinstance(x,str) and len(x)==64 and all(c in "0123456789abcdef" for c in x)}
            self.pending={u:row for u,row in self.pending.items() if fingerprint(u) not in self.attempted}
        except (OSError,ValueError,TypeError,KeyError):
            self.pending={}
            self.attempted=set()

    @classmethod
    def from_environment(cls,day):
        return cls(day,os.getenv("YORU9_RESUME_PATH"))

    def save(self):
        if not self.path:return
        payload={"version":1,"day":self.day,"pending":list(self.pending.values())[:MAX_PENDING],
                 "attempted":sorted(self.attempted)[:MAX_ATTEMPTED]}
        try:
            self.path.parent.mkdir(parents=True,exist_ok=True)
            tmp=self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload,ensure_ascii=False)+"\n",encoding="utf-8")
            tmp.replace(self.path)
        except OSError:
            print("Editorial continuation checkpoint unavailable; continue normal review.",flush=True)

    def restore_pending(self,leads):
        seen={item.get("url") for item in leads if isinstance(item,dict)}
        # The actual publisher article is fetched again; no saved prose is trusted.
        return list(leads)+[{**row,"title":"","sourcecountry":"","provider":"same-day continuation"}
                            for url,row in self.pending.items() if url not in seen]

    def rank(self,url):
        return 0 if url in self.pending else 2 if fingerprint(url) in self.attempted else 1

    def order_leads(self,ordered,recent,limit):
        if not self.path:return ordered
        # Prior unfinished publisher links remain reachable even if the normal
        # region/host discovery budget did not include them in this run.
        pending=[lead for lead in recent if lead["url"] in self.pending]
        seen={lead["url"] for lead in pending}
        combined=pending+[lead for lead in ordered if lead["url"] not in seen]
        return sorted(combined,key=lambda lead:self.rank(lead["url"]))[:limit]

    def merge_shortlist(self,ranked,all_groups,limit):
        if not self.path:return ranked
        # An unfinished source must not be lost at the 64-group shortlist cap.
        pending=[group for group in all_groups if group[0]["url"] in self.pending]
        new=[group for group in all_groups if self.rank(group[0]["url"])==1]
        seen=set()
        combined=[]
        for group in pending+ranked+new:
            url=group[0]["url"]
            if url not in seen:
                combined.append(group)
                seen.add(url)
        return sorted(combined,key=lambda group:self.rank(group[0]["url"]))[:limit]

    def order_groups(self,groups):
        if not self.path:return groups
        return sorted(groups,key=lambda group:self.rank(group["articles"][0]["url"]))

    def checkpoint_queue(self,groups,leads):
        if not self.path:return
        current={lead["url"]:lead for lead in leads}
        # Retain old unfinished links even after a transient fetch failure.
        self.pending={url:row for url,row in self.pending.items() if url in current}
        for group in groups:
            url=group["articles"][0]["url"]
            lead=current.get(url,{})
            stamp=lead.get("seendate")
            if (len(self.pending)<MAX_PENDING and trusted_original_domain(url)
                    and len(url)<=1500 and isinstance(stamp,str) and 0<len(stamp)<=30
                    and fingerprint(url) not in self.attempted):
                self.pending[url]={"url":url,"seendate":stamp}
        self.save()

    def record_attempt(self,group):
        if not self.path or not group.get("articles"):return
        url=group["articles"][0]["url"]
        if not trusted_original_domain(url):return
        self.pending.pop(url,None)
        self.attempted.add(fingerprint(url))
        self.save()
