import { acceptedHost, fixedTimeEqual, safeEditionDate, validEndpoint, validSubscription } from "./validation.ts";

function expect(condition:boolean, message:string) {
  if (!condition) throw new Error(message);
}
Deno.test("only known browser push services pass allowlist",()=>{
  expect(acceptedHost("fcm.googleapis.com"),"Google FCM should be allowed");
  expect(acceptedHost("updates.push.services.mozilla.com"),"Firefox should be allowed");
  expect(acceptedHost("web.push.apple.com"),"Safari should be allowed");
  expect(!acceptedHost("fcm.googleapis.com.evil.example"),"spoofed host blocked");
  expect(!acceptedHost("localhost"),"local host blocked");
});
Deno.test("SSRF and non-HTTPS push endpoints are rejected",()=>{
  expect(!validEndpoint("http://fcm.googleapis.com/send/abcf23456789012345678"),"HTTP");
  expect(!validEndpoint("https://localhost/private-thing-12345678901"),"local");
  expect(!validEndpoint("https://fcm.googleapis.com.evil.example/send/123456789"),"spoofed host");
  expect(validEndpoint("https://fcm.googleapis.com/fcm/send/test123456789012345"),"valid");
});
Deno.test("push endpoint must contain nonempty Web Push keys",()=>{
  const endpoint="https://fcm.googleapis.com/fcm/send/test123456789012345";
  expect(!validSubscription({endpoint}),"missing keys");
  expect(validSubscription({endpoint,keys:{p256dh:"A".repeat(86),auth:"b".repeat(22)}}),"key lengths");
  expect(!validSubscription({endpoint,keys:{p256dh:"???",auth:"b"}}),"malformed");
});
Deno.test("JST after 21:00 only and matching edition date",()=>{
  expect(!safeEditionDate("2026-11-11",new Date("2026-11-11T11:59:00Z")),"before 21");
  expect(safeEditionDate("2026-11-11",new Date("2026-11-11T12:07:00Z")),"21:07 JST");
  expect(!safeEditionDate("2026-11-10",new Date("2026-11-11T12:07:00Z")),"old edition");
  expect(!safeEditionDate("2026-11-12",new Date("2026-11-11T12:07:00Z")),"future edition");
});
Deno.test("dispatch tokens must be nontrivial and match",()=>{
  const token="x".repeat(48);
  expect(fixedTimeEqual(token,token),"same valid token");
  expect(!fixedTimeEqual("short",token),"short token denied");
  expect(!fixedTimeEqual("y".repeat(48),token),"mismatch denied");
});
