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
            "finish_reason":"stop","message":{"content":"{\\"ready\\": true}"}
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
