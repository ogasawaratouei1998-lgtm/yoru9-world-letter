import unittest,json
from suggest_ai_quips import request_payload,parse_api_result

class QuipDraftTest(unittest.TestCase):
    def test_payload_refuses_to_verify_or_publish(self):
        p=request_payload([{"id":"lead-001","headline":"Unexpected cake order","candidateUrl":"https://example.org","publisher":"Source"}])
        self.assertFalse(p["store"])
        self.assertIn("json_schema",str(p["text"]))
        self.assertIn("未確認",p["instructions"])
    def test_draft_strips_unexpected_ids_and_marks_unverified(self):
        data={"output":[{"type":"message","content":[{"type":"output_text","text":json.dumps({"ideas":[
          {"id":"lead-001","quipIdea":"あれれ","harmConcern":"確認必要","factCheckQuestions":["出典を確認"]},
          {"id":"bad","quipIdea":"should be excluded","harmConcern":"","factCheckQuestions":[]}]})}]}]}
        out=parse_api_result(data,["lead-001"])
        self.assertEqual(len(out),1)
        self.assertEqual(out[0]["status"],"AI_DRAFT_NOT_VERIFIED_NOT_APPROVED")
    def test_missing_output_fails(self):
        with self.assertRaises(ValueError):parse_api_result({},["lead-001"])

if __name__=="__main__":unittest.main()
