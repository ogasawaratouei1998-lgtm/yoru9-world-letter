import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from prepare_editorial import prepare,timestamp
JST=ZoneInfo('Asia/Tokyo')

class EditorialInboxTest(unittest.TestCase):
    def test_recent_headline_never_verified(self):
        d={'candidates':[{'title':'Unexpected cake order mix-up','url':'https://example.org/1','sourcecountry':'GB','seendate':'2026-11-11T07:00:00+09:00'}]}
        o=prepare(d,now=datetime(2026,11,11,8,0,tzinfo=JST))
        self.assertEqual(o['leads'][0]['factStatus'],'NOT_VERIFIED')
        self.assertFalse(o['automaticPublication'])
    def test_stale_and_harm_and_insecure_are_excluded(self):
        d={'candidates':[
           {'title':'wrong order','url':'https://example.org/1','seendate':'2026-10-01'},
           {'title':'bombing mistake','url':'https://example.org/2','seendate':'2026-11-11'},
           {'title':'mistake but insecure','url':'http://example.org/3','seendate':'2026-11-11'}]}
        self.assertEqual(prepare(d,now=datetime(2026,11,11,tzinfo=JST))['leads'],[])
    def test_unknown_date_not_misrepresented_as_fresh(self):
        d={'candidates':[{'title':'Interesting confusion','url':'https://example.org/1'}]}
        o=prepare(d,now=datetime(2026,11,11,tzinfo=JST))['leads'][0]
        self.assertFalse(o['ageVerified'])
        self.assertIsNone(o['reportAgeDays'])
    def test_location_diversity(self):
        d={'candidates':[{'title':'wrong order '+str(i),'url':'https://example.org/'+str(i),'seendate':'2026-11-11','sourcecountry':'JP'} for i in range(15)]}
        self.assertEqual(len(prepare(d,now=datetime(2026,11,11,tzinfo=JST))['leads']),6)
    def test_gdelt_date_parse(self):
        self.assertEqual(timestamp('20261110T100500Z').astimezone(JST).date().isoformat(),'2026-11-10')

if __name__=='__main__':unittest.main()
