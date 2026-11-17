"""Human mistake comedy requires a harmless setup, not real harassment."""
import unittest
from editorial_identity import (
    noncomic_incident_rejection,human_failure_rejection,comic_line_rejection,
)


class ComicSituationTests(unittest.TestCase):
    def test_siren_harassment_is_not_harmless_comedy(self):
        proposed={
            "title":"救急出動のサイレンに苦情を浴びせた住民、自らの通報網を止める",
            "summary":"住民がサイレンに抗議し、消防団への苦情を続けました。",
            "humanMistake":"消防団の緊急出動に苦情を寄せてしまった",
        }
        self.assertIsNotNone(noncomic_incident_rejection(proposed))
        original=[{"text":"Volunteer firefighters were abused and harassed over the emergency siren."}]
        sanitized={"title":"住民の通報と地域の意外な展開","humanActor":"住民",
                   "humanMistake":"知らせる仕組みの目的を勘違いした"}
        self.assertEqual(noncomic_incident_rejection(sanitized,original),
                         "harassment_of_emergency_responders")

    def test_real_harmless_work_mixup_remains_allowed(self):
        story={"title":"市の道路工事で標示を誤記した",
               "humanActor":"市役所の道路管理担当",
               "humanMistake":"道路上のつづりを間違えてしまった",
               "quip":"つづりは間違えたが、注目を集める仕事は大成功。"}
        self.assertIsNone(human_failure_rejection(story))
        self.assertIsNone(noncomic_incident_rejection(
            story,[{"text":"City road crew accidentally misspelled a street marking and corrected it."}]))
        self.assertIsNone(comic_line_rejection(story["quip"]))

    def test_funny_emergency_misidentification_not_blanket_banned(self):
        # No harassment of rescuers: an ordinary human mix-up may be funny.
        story={"title":"ワニだと見間違えて出動、実はプールの浮き輪",
               "humanActor":"市の動物管理担当",
               "humanMistake":"ワニだと見間違えて現場まで向かった"}
        self.assertIsNone(noncomic_incident_rejection(story,[
            {"text":"The officer mistook an inflatable pool toy for an alligator."}]))

if __name__=="__main__":
    unittest.main()
