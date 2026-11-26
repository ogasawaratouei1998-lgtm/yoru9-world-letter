import json
import unittest
from unittest.mock import Mock, patch

import auto_editorial as editorial
import local_editorial

class LocalEditorialTest(unittest.TestCase):
    def test_loopback_only_and_strict_json(self):
        client=Mock()
        response=client.getresponse.return_value
        response.status=200
        response.read.return_value=json.dumps({"choices":[{
            "finish_reason":"stop","message":{"content":json.dumps({"ready":True})}
        }]}).encode()
        with patch.object(local_editorial.http.client,"HTTPConnection",return_value=client) as connect:
            self.assertEqual(local_editorial.generate_json("test"),{"ready":True})
        connect.assert_called_once_with("127.0.0.1",18089,timeout=240)
        args=client.request.call_args.args
        self.assertEqual(args[:2],("POST","/v1/chat/completions"))
        self.assertNotIn("Authorization",args[3])
        self.assertEqual(json.loads(args[2])["response_format"],{"type":"json_object"})
        client.close.assert_called_once()

    def test_reject_truncated_or_non_object_response(self):
        for finish,content in [("length",'{"approved":true}'),("stop","[]"),("stop","broken")]:
            with self.subTest(finish=finish,content=content):
                client=Mock()
                response=client.getresponse.return_value
                response.status=200
                response.read.return_value=json.dumps({"choices":[{
                    "finish_reason":finish,"message":{"content":content}
                }]}).encode()
                with patch.object(local_editorial.http.client,"HTTPConnection",return_value=client):
                    with self.assertRaises(RuntimeError):
                        local_editorial.generate_json("test")
                client.close.assert_called_once()

    def test_local_mode_never_calls_gemini_even_without_key(self):
        with patch.object(editorial,"LOCAL_EDITORIAL",True), patch.object(editorial,"KEY",""), \
             patch.object(editorial,"LOCAL_BACKEND_FAILED",False), \
             patch.object(editorial,"RUN_DEADLINE",None), \
             patch.object(local_editorial,"generate_json",return_value={"stories":[]}) as local, \
             patch.object(editorial,"available_models") as remote:
            self.assertEqual(editorial.ai("draft"),{"stories":[]})
            local.assert_called_once()
            remote.assert_not_called()

    def test_timeout_is_request_scoped_and_never_calls_remote(self):
        with patch.object(editorial,"LOCAL_EDITORIAL",True), patch.object(editorial,"KEY",""), \
             patch.object(editorial,"LOCAL_BACKEND_FAILED",False), \
             patch.object(editorial,"RUN_DEADLINE",None), \
             patch.object(local_editorial,"generate_json",side_effect=[
                 local_editorial.LocalRequestTimeout("timeout"),{"stories":[]}]) as local, \
             patch.object(editorial,"available_models") as remote:
            with self.assertRaises(local_editorial.LocalRequestTimeout):
                editorial.ai("draft")
            self.assertFalse(editorial.LOCAL_BACKEND_FAILED)
            self.assertEqual(editorial.ai("different source"),{"stories":[]})
            self.assertEqual(local.call_count,2)
            remote.assert_not_called()

    def test_http_timeout_is_sanitized_and_closes_connection(self):
        client=Mock()
        client.getresponse.side_effect=TimeoutError("private details")
        with patch.object(local_editorial.http.client,"HTTPConnection",return_value=client):
            with self.assertRaisesRegex(local_editorial.LocalRequestTimeout,"request timed out"):
                local_editorial.generate_json("draft")
        client.close.assert_called_once()

    def test_incomplete_json_is_candidate_scoped(self):
        with patch.object(editorial,"LOCAL_EDITORIAL",True), patch.object(editorial,"KEY",""), \
             patch.object(editorial,"LOCAL_BACKEND_FAILED",False), \
             patch.object(editorial,"RUN_DEADLINE",None), \
             patch.object(local_editorial,"generate_json",side_effect=[
                 local_editorial.LocalResponseError("incomplete"),{"stories":[]}]) as local, \
             patch.object(editorial,"available_models") as remote:
            with self.assertRaises(local_editorial.LocalResponseError):
                editorial.ai("draft")
            self.assertFalse(editorial.LOCAL_BACKEND_FAILED)
            self.assertEqual(editorial.ai("next draft"),{"stories":[]})
            self.assertEqual(local.call_count,2)
            remote.assert_not_called()

    def test_screening_reorders_without_discarding_any_group(self):
        groups=[{"groupId":i,"articles":[{"title":"News "+str(i),
                 "text":"A report","url":"https://example.com/"+str(i)}]}
                for i in range(1,12)]
        with patch.object(editorial,"LOCAL_BACKEND_FAILED",False), \
             patch.object(editorial,"RUN_DEADLINE",None), \
             patch.object(editorial,"ai",side_effect=[{"preferred":[5,5,True,999]},
                                                    {"preferred":[10]}]):
            ordered,screened,preferred=editorial.screen_local_groups(groups)
        self.assertEqual(screened,11)
        self.assertEqual(preferred,2)
        self.assertEqual([g["groupId"] for g in ordered[:2]],[5,10])
        self.assertEqual(sorted(g["groupId"] for g in ordered),list(range(1,12)))

    def test_draft_metadata_is_bound_to_selected_source_and_unverified(self):
        group={"groupId":1,"articles":[{"title":"one","text":"body",
                                       "url":"https://example.com/one"}]}
        story={k:"reported text" for k in local_editorial.DRAFT_FIELDS}
        story.update(category="person",sourceIndex=1,sourceUrl="https://invented.example/",
                     editorVerified=True,editorialScores={"safety":5},imagePath="paid.webp")
        result=local_editorial.bind_draft({"stories":[story]},group)["stories"][0]
        self.assertEqual(result["sourceUrl"],group["articles"][0]["url"])
        self.assertEqual(result["verificationUrls"],[result["sourceUrl"]])
        self.assertEqual(result["sourceName"],"example.com")
        self.assertNotIn("editorVerified",result)
        self.assertNotIn("editorialScores",result)
        self.assertNotIn("imagePath",result)
        self.assertEqual(result["id"],local_editorial.bind_draft({"stories":[story]},group)["stories"][0]["id"])
        for invalid in (0,2,True,"1",None):
            story["sourceIndex"]=invalid
            self.assertEqual(local_editorial.bind_draft({"stories":[story]},group),{"stories":[]})

    def test_local_failure_has_no_remote_fallback(self):
        with patch.object(editorial,"LOCAL_EDITORIAL",True), patch.object(editorial,"KEY",""), \
             patch.object(editorial,"LOCAL_BACKEND_FAILED",False), \
             patch.object(editorial,"RUN_DEADLINE",None), \
             patch.object(local_editorial,"generate_json",side_effect=RuntimeError("down")) as local, \
             patch.object(editorial,"available_models") as remote:
            with self.assertRaises(RuntimeError): editorial.ai("draft")
            with self.assertRaisesRegex(RuntimeError,"circuit open"): editorial.ai("audit")
            local.assert_called_once()
            remote.assert_not_called()

if __name__ == "__main__":
    unittest.main()
