#!/usr/bin/env python3
"""A fail-closed release contract for the whole reader, not just news JSON.

Called after publication data is staged and before it is committed/pushed.
Optional --site validates the *built* Pages bundle including real image files.
No paid AI APIs, downloads, or image generation are performed by this checker.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from check_country_experience import country_coverage
from country_codes import country_codes

SVG_NS="{http://www.w3.org/2000/svg}svg"


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError("公開品質ゲート: "+message)


def jpeg_dimensions(path: Path) -> tuple[int,int]:
    """Read actual JPEG SOF dimensions without external imaging dependencies."""
    with path.open("rb") as stream:
        if stream.read(2)!=b"\xff\xd8":
            raise ValueError("invalid JPEG signature: "+str(path))
        while True:
            marker=stream.read(1)
            if not marker:break
            if marker!=b"\xff":continue
            marker=stream.read(1)
            while marker==b"\xff":
                marker=stream.read(1)
            if not marker or marker in (b"\xd9",b"\xda"):break
            if marker in (b"\x00",b"\x01") or 0xd0<=marker[0]<=0xd7:
                continue
            length=stream.read(2)
            if len(length)!=2:break
            size=int.from_bytes(length,"big")
            if size<2:break
            if marker[0] in (0xc0,0xc1,0xc2,0xc3,0xc5,0xc6,0xc7,
                             0xc9,0xca,0xcb,0xcd,0xce,0xcf):
                body=stream.read(5)
                if len(body)==5:
                    return int.from_bytes(body[3:5],"big"),int.from_bytes(body[1:3],"big")
                break
            stream.seek(size-2,1)
    raise ValueError("JPEG dimensions unavailable: "+str(path))


def audit(root: Path, site: Path | None = None) -> dict:
    root=Path(root)
    issue=json.loads((root/"data/current.json").read_text(encoding="utf-8"))
    date=issue.get("editionDate","")
    stories=issue.get("stories")
    require(issue.get("status")=="published" and isinstance(date,str)
            and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}",date))
            and isinstance(stories,list) and bool(stories),
            "公開号の日付・公開状態・記事データが不正")
    archive_path=root/"data/archive"/(date+".json")
    require(archive_path.is_file(),"公開号のアーカイブがない")
    require(json.loads(archive_path.read_text(encoding="utf-8"))==issue,
            "公開号とアーカイブが一致していない")
    index=json.loads((root/"data/archive/index.json").read_text(encoding="utf-8"))
    require(sum(row.get("date")==date for row in index.get("issues",[])
                if isinstance(row,dict))==1,
            "アーカイブの一覧に当日号がちょうど1件必要")
    ids=[s.get("id") for s in stories]
    require(len(ids)==len(set(ids)) and all(isinstance(x,str) and x for x in ids),
            "記事IDに重複または欠損がある")
    new_regular=(date>="2026-11-21" and issue.get("editionType")=="regular")
    if new_regular:
        # The current issue must be nonempty (checked above), but has no
        # mandatory minimum or maximum count of approved stories.
        require(all("imagePath" not in s and "imageType" not in s for s in stories),
                "無料イラスト方式に生成画像の参照が混入")

    html=(root/"index.html").read_text(encoding="utf-8")
    quiz=(root/"world-passport.js").read_text(encoding="utf-8")
    worker=(root/"service-worker.js").read_text(encoding="utf-8")
    stops=json.loads((root/"travel-stops.json").read_text(encoding="utf-8"))
    require("function fallbackNewsArt(story)" in html and
            "return fallbackNewsArt(story);" in html and
            "function renderIssueGallery()" in html,
            "記事の無料イラスト表示経路がない")
    require('id="todayMapPins"' in html and "currentIssueCountries()" in html and
            "'実話'+edition.stories.length+'本・'+countries.length+'カ国'" in html,
            "地図と記事数・国数の連動が欠落")
    require('id="todayMapLegend"' in html and
            'id="todayCountryQuiz"' in html and
            "revealWorldPassportAnswerPhoto" in quiz,
            "写真付き3択クイズの表示経路が欠落")
    require(not any(token in html for token in
                    ('id="todayPassportBoard"','id="todayPassportCount"',
                     'id="todayPassportStamps"','id="todayQuizStampReward"')),
            "削除済みスタンプ帳が再び表示される")
    require(not any(token in quiz for token in
                    ("localStorage","worldPassportStamps","todayPassportBoard")),
            "削除済みスタンプ収集が復活している")
    require('class="travel-story"' in html and
            'stop.travelStory.map(paragraph=>' in html and
            'escapeHtml(paragraph)' in html,
            "小旅行の詳しい文章が安全に描画されない")
    require("const SHELL_CACHE = 'yoru9-shell-v" in worker and
            "caches.delete" in worker,
            "PWAの更新・古いキャッシュの削除がない")

    # An unfinished future country must not produce a one-line guide,
    # generic quiz, missing cover or incorrectly attributed tourist photo.
    countries=country_coverage(root,stories)
    codes={code for story in stories for code in country_codes(story.get("country",""))}
    require(set(countries)==codes,"ニュースの国と紹介・クイズの国が不一致")

    for key,stop in stops.items():
        if stop.get("coverOnly") or stop.get("quizOnly"):continue
        essays=stop.get("travelStory")
        require(isinstance(essays,list) and len(essays)==2 and
                all(isinstance(p,str) and 70<=len(p.strip())<=360
                    for p in essays),
                "小旅行 "+key+" に詳しい2段落がない")
        require(stop.get("country") and stop.get("place") and
                isinstance(stop.get("photoCaption"),str) and stop.get("author") and
                stop.get("licenseUrl","").startswith("https://creativecommons.org/"),
                "小旅行 "+key+" の国・写真出典・権利が不備")

    art=root/"assets/news"
    require(art.is_dir(),"ニュースのSVGイラスト集がない")
    for image in art.glob("*.svg"):
        document=ET.parse(image)
        require(document.getroot().tag==SVG_NS and
                not any(element.tag.endswith(("script","foreignObject")) for
                        element in document.iter()),
                "SVGイラストの形式が不正: "+image.name)

    # Verify real bytes and dimensions in the assembled *public* bundle,
    # not merely a path or a successful downloads counter.
    if site is not None:
        site=Path(site)
        from reader_asset_split import expected_reader_assets, rendered_service_worker
        browser_assets=expected_reader_assets(root)
        for relative,expected in browser_assets.items():
            dest=site/relative
            require(dest.is_file() and dest.read_bytes()==expected,
                    '分離済みCSS/JavaScriptの公開ファイルが元データと不一致: '+relative)
        for relative in ("world-passport.js","service-worker.js",
                         "travel-stops.json","data/current.json"):
            expected=(root/relative).read_bytes()
            if relative=="service-worker.js":
                # The built worker must cache the same fingerprinted reader
                # files as the exact verified release HTML, not stale JS.
                expected=rendered_service_worker(
                    expected.decode("utf-8"),
                    browser_assets["index.html"].decode("utf-8")
                ).encode("utf-8")
            dest=site/relative
            require(dest.is_file() and dest.read_bytes()==expected,
                    "公開ビルドのファイルが元データと不一致: "+relative)
        for relative in ("data/approved","assets/news-generated"):
            require(not (site/relative).exists(),
                    "公開ビルドに承認用データ・有料画像が混入: "+relative)
        targets={row["cover"] for row in countries.values()}
        targets.update(stops[key]["photoAsset"] for row in countries.values()
                       for key in row["quizPhotoKeys"])
        targets.update(row["postcard"] for row in countries.values())
        require(targets,"表示する写真がない")
        covers={row["cover"] for row in countries.values()}
        for relative in sorted(targets):
            file=site/relative
            require(file.is_file() and 3000<=file.stat().st_size<=2_000_000,
                    "実際の写真ファイルが欠落: "+relative)
            try:
                width,height=jpeg_dimensions(file)
            except (OSError,ValueError) as exc:
                raise ValueError("公開品質ゲート: JPEG画像の検証に失敗: "+relative) from exc
            if relative in covers:
                require(width>=1000 and height>=540,
                        "国紹介の写真が低解像度: "+relative+" ("+str(width)+"x"+str(height)+")")
            else:
                require(width>=330 and height>=200,
                        "小旅行・クイズ写真が低解像度: "+relative)
    return {"date":date,"stories":len(stories),"countries":len(countries),
            "touristRecords":sum(not(s.get("coverOnly") or s.get("quizOnly"))
                                 for s in stops.values()),
            "buildPhotosChecked":site is not None}


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,default=Path(__file__).resolve().parent)
    parser.add_argument("--site",type=Path)
    args=parser.parse_args()
    summary=audit(args.root,args.site)
    print("Reader release quality PASSED:",json.dumps(summary,ensure_ascii=False))


if __name__=="__main__":
    main()
