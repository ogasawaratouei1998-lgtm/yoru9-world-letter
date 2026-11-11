// No environment variables or privileged database access in this module.
export const READER_ORIGIN = "https://ogasawaratouei1998-lgtm.github.io";

export type StoredPushSubscription = {
  endpoint: string;
  keys: { p256dh: string; auth: string };
};

export function acceptedHost(hostname: string): boolean {
  const host = hostname.toLowerCase();
  return host === "fcm.googleapis.com" ||
    host === "updates.push.services.mozilla.com" ||
    host.endsWith(".push.services.mozilla.com") ||
    host === "web.push.apple.com" ||
    host.endsWith(".push.apple.com") ||
    host.endsWith(".notify.windows.com");
}

export function validEndpoint(value: unknown): value is string {
  if (typeof value !== "string" || value.length < 20 || value.length > 1800) return false;
  try {
    const url = new URL(value);
    return url.protocol === "https:" && !url.username && !url.password &&
      !url.hash && !url.port && acceptedHost(url.hostname);
  } catch { return false; }
}

const keyPattern = /^[A-Za-z0-9_-]+$/;
export function validSubscription(data: unknown): data is StoredPushSubscription {
  if (typeof data !== "object" || data === null) return false;
  const sub = data as Record<string, unknown>;
  if (!validEndpoint(sub.endpoint)) return false;
  if (typeof sub.keys !== "object" || sub.keys === null) return false;
  const keys = sub.keys as Record<string, unknown>;
  return typeof keys.p256dh === "string" && keys.p256dh.length >= 80 &&
    keys.p256dh.length <= 120 && keyPattern.test(keys.p256dh) &&
    typeof keys.auth === "string" && keys.auth.length >= 16 &&
    keys.auth.length <= 60 && keyPattern.test(keys.auth);
}

export function safeEditionDate(day: unknown, now: Date = new Date()): boolean {
  if (typeof day !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(day)) return false;
  const today = new Intl.DateTimeFormat("en-CA", {
    timeZone:"Asia/Tokyo",year:"numeric",month:"2-digit",day:"2-digit"
  }).format(now);
  const time = new Intl.DateTimeFormat("en-GB", {
    timeZone:"Asia/Tokyo",hour:"2-digit",minute:"2-digit",hour12:false
  }).format(now);
  return day === today && time >= "21:00";
}

export function fixedTimeEqual(a: string,b: string): boolean {
  // Equal-time for equal-sized secrets; disallow short or missing tokens.
  if (a.length < 32 || b.length < 32) return false;
  let differences=a.length^b.length;
  const n=Math.max(a.length,b.length);
  for(let i=0;i<n;i++) differences |= (a.charCodeAt(i%a.length)^b.charCodeAt(i%b.length));
  return differences===0;
}


export function validPushSettings(values:{
  publicKey:string;privateKey:string;subject:string;token:string;salt:string;
}):boolean {
  return /^[A-Za-z0-9_-]{87}$/.test(values.publicKey) &&
    /^[A-Za-z0-9_-]{43}$/.test(values.privateKey) &&
    /^mailto:[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/.test(values.subject) &&
    /^[A-Za-z0-9_-]{43,}$/.test(values.token) &&
    /^[A-Za-z0-9_-]{43,}$/.test(values.salt);
}
