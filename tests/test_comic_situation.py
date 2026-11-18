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

    def test_unfunny_student_disciplinary_dispute_is_rejected(self):
        story={"title":"学位授与式の騒動で大臣が途中退席、学生らに処分",
               "humanActor":"学生リーダー",
               "humanMistake":"式典で抗議をして学内評議会に謝罪を求められた"}
        article=[{"text":"Convocation row: council asks suspended students to "
                         "accept mistake after minister walked out."}]
        self.assertEqual(noncomic_incident_rejection(story,article),
                         "disciplinary_confrontation_not_comic_error")
        softened={"title":"大学で思いがけない展開",
                  "humanActor":"学生",
                  "humanMistake":"進行を勘違いしてしまった"}
        self.assertEqual(noncomic_incident_rejection(softened,article),
                         "disciplinary_confrontation_not_comic_error")

    def test_comic_graduation_diploma_typo_still_eligible(self):
        story={"title":"卒業式の証書を誤字で印刷、職員が訂正",
               "humanActor":"事務職員",
               "humanMistake":"卒業証書の文字を間違えて印刷した"}
        article=[{"text":"At graduation ceremony the printer misspelled "
                         "names and staff corrected the diplomas."}]
        self.assertIsNone(noncomic_incident_rejection(story,article))

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

    def test_dead_racehorse_disposal_is_never_light_comedy(self):
        # A previous live probe approved this kind of unsuitable story.
        story={"title":"競走馬が埋葬の途中でゴミ箱に見つかった",
               "humanActor":"関係者",
               "humanMistake":"亡くなった競走馬の処理を不適切に行った",
               "quip":"栄光のゴール板ではなくゴミ箱行き"}
        article=[{"text":"Dead Melbourne Cup racehorse found dumped in "
                         "Sydney waste facility during disposal."}]
        self.assertEqual(noncomic_incident_rejection(story,article),
                         "animal_death_or_disposal_not_comedy")
        self.assertEqual(noncomic_incident_rejection(
            {"title":"担当者の段取りミス",
             "humanActor":"関係者","humanMistake":"動物の扱いを誤った"},
            article),"animal_death_or_disposal_not_comedy")

    def test_horse_novelty_requires_actual_human_error(self):
        story={"title":"競走馬が思いがけない場所で見つかった",
               "humanActor":"係員",
               "humanMistake":"発見しただけで特定のミスはない"}
        self.assertEqual(human_failure_rejection(story),
                         "animal_novelty_not_human_failure")
        harmless={"title":"係員が馬を犬と見間違えて通報",
                  "humanActor":"施設の係員",
                  "humanMistake":"遠くの馬を犬だと見間違えて通報してしまった"}
        self.assertIsNone(human_failure_rejection(harmless))
        self.assertIsNone(noncomic_incident_rejection(harmless,[
            {"text":"The attendant mistook a horse for a dog."}]))

    def test_hospital_staff_shortage_publicity_is_not_comedy(self):
        story={'title':'病院の深刻な人員不足をメディア経由で訴える',
               'humanActor':'病院経営陣',
               'humanMistake':'院内の問題をメディア経由で訴えた',
               'quip':'院内の危機をPRに使った'}
        original=[{'text':'Cork University Hospital managers described'
                   ' serious staffing shortages and too few nurses.'}]
        self.assertEqual(noncomic_incident_rejection(story,original),
                         'hospital_staffing_crisis_not_comedy')
        self.assertEqual(noncomic_incident_rejection(
            {'title':'関係者の想定外の会見',
             'humanMistake':'説明の場を選び間違えた'},original),
            'hospital_staffing_crisis_not_comedy')

    def test_hospital_sign_typo_stays_eligible(self):
        story={'title':'病院の駐車場案内が誤字だらけ',
               'humanActor':'施設担当者',
               'humanMistake':'駐車場案内看板の文字を間違えた'}
        original=[{'text':'Hospital staff spotted a typo on a parking sign'
                   ' and corrected it.'}]
        self.assertIsNone(noncomic_incident_rejection(story,original))
if __name__=="__main__":
    unittest.main()
