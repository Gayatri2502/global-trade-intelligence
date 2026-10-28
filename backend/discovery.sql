create table trade_private.discovery_leads (
 lead_id text primary key,
 spreadsheet_id text not null,
 company text not null,
 role text not null,
 product text,
 country text,
 phone text,
 email text,
 website text not null,
 social_urls jsonb not null default '[]',
 evidence text,
 status text not null default 'Unverified',
 first_seen timestamptz not null default now(),
 last_seen timestamptz not null default now(),
 delivered_at timestamptz
);
create index on trade_private.discovery_leads(spreadsheet_id,delivered_at);
create table trade_private.crawl_runs (
 run_id text primary key, started_at timestamptz not null default now(),
 summary jsonb not null
);
alter table trade_private.discovery_leads enable row level security;
alter table trade_private.crawl_runs enable row level security;
revoke all on trade_private.discovery_leads,trade_private.crawl_runs from public,anon,authenticated;
create function public.trade_discovery(p_body text,p_signature text,p_timestamp bigint)
returns jsonb language plpgsql security definer set search_path='' as $$
declare payload jsonb:=p_body::jsonb; secret text; item jsonb; source_id text; result jsonb;
begin
 if abs(extract(epoch from now())-p_timestamp)>300 then raise exception 'Expired request';end if;
 source_id:=payload->>'spreadsheetId';
 select signing_secret into secret from trade_private.sync_sources where spreadsheet_id=case when payload->>'kind'='discovery_ingest' then 'crawler:'||source_id else source_id end;
 if secret is null or p_signature is null or p_signature<>encode(extensions.hmac(convert_to(p_timestamp::text||'.'||p_body,'UTF8'),convert_to(secret,'UTF8'),'sha256'),'hex') then raise exception 'Unauthorized';end if;
 if payload->>'kind'='discovery_ingest' then
  if jsonb_array_length(payload->'leads')>100 then raise exception 'Batch limit exceeded';end if;
  for item in select value from jsonb_array_elements(payload->'leads') loop
   if (item->>'lead_id') !~ '^[a-f0-9]{32}$' or (item->>'website') !~ '^https://' or length(item->>'company')>300 then raise exception 'Invalid lead';end if;
   insert into trade_private.discovery_leads(lead_id,spreadsheet_id,company,role,product,country,phone,email,website,social_urls,evidence)
   values(item->>'lead_id',source_id,item->>'company',item->>'role',item->>'product',item->>'country',item->>'phone',item->>'email',item->>'website',coalesce(item->'social_urls','[]'),left(item->>'evidence',1500))
   on conflict(lead_id) do update set last_seen=now();
  end loop;
  insert into trade_private.crawl_runs(run_id,summary) values(payload->>'run_id',coalesce(payload->'summary','{}')) on conflict do nothing;
  return jsonb_build_object('ok',true,'accepted',jsonb_array_length(payload->'leads'));
 elsif payload->>'kind'='discovery_ack' then
  update trade_private.discovery_leads set delivered_at=now() where spreadsheet_id=source_id and lead_id in(select jsonb_array_elements_text(payload->'lead_ids'));
  return jsonb_build_object('ok',true);
 else
  select coalesce(jsonb_agg(to_jsonb(q)),'[]'::jsonb) into result from (select lead_id,company,role,product,country,phone,email,website,social_urls,evidence,status,first_seen from trade_private.discovery_leads where spreadsheet_id=source_id and delivered_at is null order by first_seen limit 100) q;
  return jsonb_build_object('ok',true,'discovery',result);
 end if;
end $$;
revoke all on function public.trade_discovery(text,text,bigint) from public,anon,authenticated;
grant execute on function public.trade_discovery(text,text,bigint) to service_role;
