-- Standalone Yoru9 push project only. Never run on an unrelated project.
-- Keep all data private; the service_role is the only database client.
CREATE TABLE IF NOT EXISTS public.yoru9_push_subscriptions (
  endpoint_hash text PRIMARY KEY CHECK (endpoint_hash ~ '^[0-9a-f]{64}$'),
  endpoint text NOT NULL UNIQUE,
  p256dh text NOT NULL,
  auth text NOT NULL,
  last_notified_date date,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.yoru9_push_dispatches (
  edition_date date PRIMARY KEY,
  state text NOT NULL DEFAULT 'processing'
    CHECK (state IN ('processing', 'complete', 'partial')),
  total integer NOT NULL DEFAULT 0,
  delivered integer NOT NULL DEFAULT 0,
  gone integer NOT NULL DEFAULT 0,
  failed integer NOT NULL DEFAULT 0,
  started_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz
);

CREATE TABLE IF NOT EXISTS public.yoru9_push_rate_windows (
  client_hash text NOT NULL CHECK (client_hash ~ '^[0-9a-f]{64}$'),
  minute_window timestamptz NOT NULL,
  counter integer NOT NULL DEFAULT 1,
  PRIMARY KEY(client_hash, minute_window)
);

-- These tables exist in the public schema for service-role PostgREST access only.
-- Anonymous visitors cannot SELECT or write them via the Data API.
ALTER TABLE public.yoru9_push_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.yoru9_push_dispatches ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.yoru9_push_rate_windows ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.yoru9_push_subscriptions FROM PUBLIC, anon, authenticated;
REVOKE ALL ON TABLE public.yoru9_push_dispatches FROM PUBLIC, anon, authenticated;
REVOKE ALL ON TABLE public.yoru9_push_rate_windows FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.yoru9_push_subscriptions TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.yoru9_push_dispatches TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.yoru9_push_rate_windows TO service_role;

-- Called only by the privileged Edge Function; atomic per-minute rate limit.
-- Deliberately not callable by anon or authenticated.
CREATE OR REPLACE FUNCTION public.yoru9_push_allow_request(p_hash text, p_limit integer DEFAULT 6)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE allowed integer;
BEGIN
  IF p_hash !~ '^[0-9a-f]{64}$' OR p_limit < 1 OR p_limit > 30 THEN
    RETURN false;
  END IF;
  INSERT INTO public.yoru9_push_rate_windows AS rate
    (client_hash, minute_window, counter)
  VALUES (p_hash, pg_catalog.date_trunc('minute', pg_catalog.now()), 1)
  ON CONFLICT(client_hash, minute_window)
  DO UPDATE SET counter=rate.counter+1
    WHERE rate.counter < p_limit
  RETURNING counter INTO allowed;
  RETURN allowed IS NOT NULL;
END;
$$;
REVOKE ALL ON FUNCTION public.yoru9_push_allow_request(text, integer) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.yoru9_push_allow_request(text, integer) TO service_role;

-- Service-role-only garbage collection can delete expired rate windows daily.
