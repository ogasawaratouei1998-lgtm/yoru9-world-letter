"""Guard against ordinary corporate stories and flat commentary on editorial reissue."""
import json
from pathlib import Path
import unittest

from editorial_surprise import (
    stage_quip_rejection, extraordinary_rejection, edition_mixture_rejection
)
from publish_approved import validate_approved

ROOT=Path(__file__).resolve().parents[1]


class HardSurpriseEditionTest(unittest.TestCase):
    def test_spoken_tsukkomi_must_go_past_summary(self):
        for soft in (
            "安全を守るはずの車止めが財布とタイヤを削る特等席になっていたとは。",
            "このようなことが起きるとは本当に驚きですね。",
            "計画が予想外に展開したというお話でした。",
        ):
            self.assertIsNotNone(stage_quip_rejection(soft),soft)
        self.assertIsNone(stage_quip_rejection(
            "味方へのパスが自陣にゴール！お前が先制点配ってどうすんねん！"))

    def test_unverified_shock_score_and_recap_are_rejected(self):
        issue=json.loads((ROOT/'data/approved/2026-11-18.json').read_text())
        story=issue['stories'][0]
        self.assertIsNone(extraordinary_rejection(story))
        for patch in (
            {'surpriseVerified':False},
            {'surpriseScore':3},
            {'stageTsukkomiVerified':False},
            {'surpriseType':'ordinary-news'},
            {'surprisePayoff':story['surpriseSetup']},
            {'quip':'これは驚くようなことですね。'},
        ):
            self.assertIsNotNone(extraordinary_rejection({**story,**patch}))

    def test_reissued_edition_has_three_desks_and_not_one_old_story(self):
        approved=json.loads((ROOT/'data/approved/2026-11-18.json').read_text())
        self.assertEqual(approved['approvedBy'],'editorial-hard-surprise-2026-11-18')
        self.assertIsNone(edition_mixture_rejection(approved['stories']))
        old={
            'new-plymouth-cycleway-2026',
            'oy-bar-studio-city-closure-2026',
            'blackburn-mcdonalds-ai-mural-mixups-2026',
        }
        self.assertFalse(old.intersection({s['id'] for s in approved['stories']}))
        expected=validate_approved(approved,'2026-11-18')
        current=json.loads((ROOT/'data/current.json').read_text())
        archive=json.loads((ROOT/'data/archive/2026-11-18.json').read_text())
        self.assertEqual(expected,current)
        self.assertEqual(expected,archive)

    def test_editorial_immutability_still_blocks_unapproved_replacement(self):
        from datetime import datetime
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from publish_approved import publish
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            for sub in ('data/approved','data/archive'):
                (root/sub).mkdir(parents=True,exist_ok=True)
            original=(ROOT/'data/approved/2026-11-18.json').read_text()
            (root/'data/approved/2026-11-18.json').write_text(original)
            (root/'data/archive/2026-11-18.json').write_text(
                json.dumps({'status':'published','editionDate':'2026-11-18','stories':[{'id':'old'}]}))
            (root/'data/current.json').write_text(json.dumps({
                'status':'published','editionDate':'2026-11-18','stories':[{'id':'old'}]}))
            (root/'data/archive/index.json').write_text('{"issues":[]}')
            with self.assertRaisesRegex(ValueError,'無断の差し替え'):
                publish(root,datetime.fromisoformat('2026-11-18T22:15:00+09:00'))


if __name__=='__main__':
    unittest.main()
