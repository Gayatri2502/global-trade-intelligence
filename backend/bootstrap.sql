-- Apply once before schema.sql and discovery.sql on a new Supabase project.
create schema if not exists trade_private;
revoke all on schema trade_private from public,anon,authenticated;
create table if not exists trade_private.workbook_archives (
 sha256 text primary key check(length(sha256)=64),
 filename text not null,
 content bytea not null check(octet_length(content)>0),
 created_at timestamptz not null default now()
);
create table if not exists trade_private.model_snapshots (
 workbook_sha256 text primary key references trade_private.workbook_archives(sha256),
 model jsonb not null,
 created_at timestamptz not null default now()
);
alter table trade_private.workbook_archives enable row level security;
alter table trade_private.model_snapshots enable row level security;
revoke all on all tables in schema trade_private from public,anon,authenticated;
