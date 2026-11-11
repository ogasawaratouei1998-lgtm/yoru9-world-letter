#!/usr/bin/env python3
"""Non-destructive live push readiness probe. Never sends a real notification."""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE="https://kdvkbkdfnrwvrbugpnaq.supabase.co/functions/v1/yoru9-push"

def request_status(url, method="GET", body=None, headers=None):
    req=Request(url,method=method,data=body,headers=headers or {})
    try:
        with urlopen(req, timeout=20) as res:
            return res.status,res.read(20000)
    except HTTPError as exc:
        return exc.code,exc.read(20000)

def main():
    url=os.environ.get("PUSH_DISPATCH_URL","")
    secret=os.environ.get("PUSH_DISPATCH_TOKEN","")
    if url != BASE+"/dispatch" or len(secret)<32:
        raise RuntimeError("GitHub Actions PUSH_DISPATCH_URL or PUSH_DISPATCH_TOKEN not configured. No notification sent.")
    code, body=request_status(BASE+"/health")
    if code!=200:
        raise RuntimeError(f"Push health endpoint returned {code}")
    status=json.loads(body)
    if status.get("service")!="yoru9-push" or status.get("ready") is not True:
        raise RuntimeError("Supabase secrets or VAPID values missing. Push is intentionally disabled.")
    if status.get("signupsOpen") is not True:
        raise RuntimeError("Supabase PUSH_SIGNUPS_ENABLED is not true. Subscription is intentionally disabled.")
    # Check that the GitHub secret and Supabase secret actually match without sending a push.
    check_code,check_body=request_status(BASE+"/verify-auth","POST",b"{}",{
        "Authorization":"Bearer "+secret,
        "Content-Type":"application/json",
    })
    if check_code!=200 or json.loads(check_body).get("notificationSent") is not False:
        raise RuntimeError("Supabase and GitHub dispatch secrets are not matched.")
    # An intentionally wrong token must be rejected before any dispatch or DB update.
    bad_code,_=request_status(BASE+"/dispatch","POST",b"{}",{
        "Authorization":"Bearer invalid-readiness-test-only",
        "Content-Type":"application/json",
    })
    if bad_code!=401:
        raise RuntimeError(f"Unauthorized dispatch did not return HTTP 401 (got {bad_code})")
    # Cross-site requests to the public subscription API must be denied.
    cross_code,_=request_status(BASE+"/subscribe","POST",b"{}",{
        "Origin":"https://example.org",
        "Content-Type":"application/json",
    })
    if cross_code!=403:
        raise RuntimeError(f"Cross-site subscription did not return HTTP 403 (got {cross_code})")
    print("SUCCESS: secrets loaded, registration open, unauthorized requests blocked.")
    print("No user was subscribed and no notification was sent. Device test is still required.")

if __name__=="__main__":
    main()
