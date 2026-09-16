-- Ad Spy Agent - Postgres schema (self-hosted).
--
-- Mounted into the postgres container's /docker-entrypoint-initdb.d/ so it
-- runs automatically the first time the `postgres` volume is created (see
-- docker-compose.yml). To apply by hand instead:
--   psql "$DATABASE_URL" -f db/schema.sql

create extension if not exists "pgcrypto";

-- One row per research run requested from the dashboard. The worker polls
-- for status = 'pending', claims a row (-> 'running'), then fills in the
-- DNA/brand columns and flips status to 'completed' or 'failed'.
create table if not exists research_jobs (
  id uuid primary key default gen_random_uuid(),
  query text not null,
  country text not null default 'ALL',
  max_ads integer not null default 30,
  scroll_rounds integer not null default 5,
  use_gemini boolean not null default true,
  status text not null default 'pending'
    check (status in ('pending', 'running', 'completed', 'failed')),
  brand_info jsonb not null default '{}'::jsonb,
  copy_dna jsonb not null default '{}'::jsonb,
  creative_dna jsonb not null default '{}'::jsonb,
  gemini_copy_dna jsonb not null default '{}'::jsonb,
  gemini_creative_dna jsonb not null default '{}'::jsonb,
  error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists research_jobs_status_created_idx
  on research_jobs (status, created_at);

-- One row per scraped ad, linked back to the job that found it. image_url is
-- a path like /images/<job_id>/<file>.jpg that Caddy serves directly off the
-- shared ad_images volume - the worker writes the file there and never
-- "uploads" it anywhere.
create table if not exists ads (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null references research_jobs (id) on delete cascade,
  ad_id text,
  platform text,
  status text,
  start_date text,
  primary_text text,
  headline text,
  cta text,
  media_type text,
  angle text,
  funnel_stage text,
  copy_breakdown jsonb not null default '{}'::jsonb,
  full_breakdown jsonb not null default '{}'::jsonb,
  image_path text,
  image_url text,
  created_at timestamptz not null default now()
);

create index if not exists ads_job_id_idx on ads (job_id);

-- Keep updated_at current on every research_jobs change.
create or replace function set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists research_jobs_set_updated_at on research_jobs;
create trigger research_jobs_set_updated_at
  before update on research_jobs
  for each row execute function set_updated_at();
