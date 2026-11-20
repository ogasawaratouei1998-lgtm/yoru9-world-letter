"""Navigation regression: selected news must have its own screen and URL."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]


class NewsScreenNavigationTest(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node.js is required")
    def test_card_selection_browser_history_and_back_to_gallery(self):
        html=(ROOT/"index.html").read_text(encoding="utf-8")
        start=html.index("let selectedArticleIndex=0;")
        end=html.index("function updateSpotlight(){",start)
        functions=html[start:end]
        harness=r"""
const listeners={};
const selected=new Set();
const classList={
 add(x){selected.add(x)},remove(x){selected.delete(x)},
 contains(x){return selected.has(x)}
};
function element(){
 return {hidden:false,dataset:{},attrs:{},textContent:'',disabled:false,
  classList:{add(){},remove(){}},
  setAttribute(k,v){this.attrs[k]=v},
  getAttribute(k){return this.attrs[k]},
  querySelector(x){return x==='[data-travel-slot]'?this.travelSlot:null;},
  querySelectorAll(){return []},
  addEventListener(){},focus(){},scrollIntoView(){}};
}
const dom={};
const $=id=>(dom[id]??=element());
$('spotlight').travelSlot=element();
const tiles=[element(),element(),element()];
$('issueGallery').querySelectorAll=()=>tiles;
const document={body:{classList},querySelector:()=>element()};
const window={matchMedia:()=>({matches:false}),scrollTo(){},
 addEventListener(type,fn){listeners[type]=fn}};
const location={hash:'#issueGallery'};
const history={
 pushState(_state,_title,hash){location.hash=hash},
 replaceState(_state,_title,hash){location.hash=hash}
};
const edition={stories:[
 {id:'first-id',title:'最初のニュース'},
 {id:'second-id',title:'二本目のニュース'},
 {id:'third-id',title:'三本目のニュース'}]};
let lastRendered=-1,read=-1,filter='all';
function closeOptionalTravelPanels(){}
function updateSpotlight(){lastRendered=selectedArticleIndex}
function renderTravelSlots(){}
function applyFilter(){}
function markRead(i){read=i}
function update(){}
"""
        assertions=r"""
openAtlasStory(1);
if(!selected.has('news-detail-mode')||$('articleReader').hidden)process.exit(11);
if(lastRendered!==1||read!==1||$('spotlight').travelSlot.dataset.travelSlot!=='1')process.exit(12);
if(!$('stories').hidden||$('spotlightBody').hidden!==false)process.exit(13);
if(location.hash!=='#story/second-id')process.exit(14);
if($('readerPrev').disabled!==false)process.exit(15);
if(tiles[1].attrs['aria-expanded']!=='true')process.exit(16);
location.hash='#story/third-id';
listeners['popstate']();
if(lastRendered!==2||$('readerNext').disabled!==true)process.exit(17);
closeArticleReader();
if(selected.has('news-detail-mode')||!$('articleReader').hidden)process.exit(18);
if(location.hash!=='#issueGallery')process.exit(19);
location.hash='#story/first-id';
listeners['hashchange']();
if(lastRendered!==0||!$('readerPrev').disabled)process.exit(20);
location.hash='#issueGallery';
listeners['hashchange']();
if(!$('articleReader').hidden)process.exit(21);
"""
        script=harness+"\n"+functions+"\n"+assertions
        run=subprocess.run(["node","-e",script],capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stderr)

    def test_the_hero_reader_uses_article_specific_content(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        block=page[page.index("function updateSpotlight(){"):
                   page.index("/* Optional 30-second journey",page.index("function updateSpotlight(){"))]
        self.assertIn("edition.stories[selectedArticleIndex]",block)
        self.assertIn("first.title",block)
        self.assertIn("first.summary",block)
        self.assertIn("first.quip",block)
        self.assertIn("first.sourceUrl",block)
        self.assertIn('data-share="'+'$'+'{selectedArticleIndex}"',block)
        self.assertNotIn('data-smile',block)
        self.assertIn("markRead(selectedArticleIndex)",block)
        self.assertNotIn("markRead(0)",block)

    def test_mobile_single_article_screen_keeps_sources_and_travel(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        self.assertIn("body.news-detail-mode main > :not(#articleReader):not(#offlineNotice){display:none!important}",page)
        self.assertIn("body.news-detail-mode #articleReader #stories,",page)
        self.assertIn("body.news-detail-mode #articleReader .spotlight-visual{display:block}",page)
        self.assertIn('id="readerBack"',page)
        self.assertIn('id="readerPrev"',page)
        self.assertIn('id="readerNext"',page)
        self.assertIn("renderTravelSlots();",page)
        self.assertIn("function travelPostcardHtml(",page)
        self.assertIn("storyEvidenceHtml(first)",page)
