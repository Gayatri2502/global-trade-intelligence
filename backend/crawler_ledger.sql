begin;
create or replace function public.trade_crawler_ledger(p_body text,p_signature text,p_timestamp bigint)
returns jsonb language plpgsql security definer set search_path='' as $$
declare
 payload jsonb := p_body::jsonb;
 secret text;
 item jsonb;
 existing trade_private.ledger_records;
 candidate_count integer;
 current_data jsonb;
 merged jsonb;
 source_key text := payload->>'source';
 run_key text := payload->>'run_id';
 saved_summary jsonb;
 inserted integer := 0;
 updated integer := 0;
 duplicates integer := 0;
 rejected integer := 0;
 field text;
begin
 select signing_secret into secret from trade_private.sync_sources
 where spreadsheet_id='crawler:1wNPYCBBXAn3y2uJ4LOV6vGgWzYhro_PPGk2HsU0cjj0';
 if secret is null or p_timestamp is null or abs(extract(epoch from now())-p_timestamp)>300 or
  p_signature is distinct from encode(extensions.hmac(convert_to(p_timestamp::text||'.'||p_body,'UTF8'),convert_to(secret,'UTF8'),'sha256'),'hex')
 then raise exception 'Unauthorized' using errcode='42501'; end if;
 if source_key is null or source_key !~ '^[a-z0-9-]{1,60}$' then raise exception 'Invalid source'; end if;
 if payload->>'action'='state' then
  select summary into saved_summary from trade_private.crawl_runs
  where summary->>'source'=source_key and summary->>'status'='saved' order by started_at desc limit 1;
  return coalesce(saved_summary,'{}');
 end if;
 if run_key is null or length(run_key)>160 or payload->>'action' not in ('save','failure')
 then raise exception 'Invalid run'; end if;
 perform pg_advisory_xact_lock(hashtext('trade-crawler:'||run_key));
 select summary into saved_summary from trade_private.crawl_runs where run_id=run_key;
 if saved_summary->>'status'='saved' then return saved_summary; end if;
 saved_summary:=coalesce(payload->'summary','{}')||jsonb_build_object('source',source_key,'completed_at',now());
 if payload->>'action'='failure' then
  saved_summary:=saved_summary||'{"status":"failed"}'::jsonb;
 else
  if jsonb_typeof(payload->'leads') is distinct from 'array' or jsonb_array_length(payload->'leads') not between 1 and 100 then
   raise exception 'A run must contain between 1 and 100 leads';
  end if;
  lock table trade_private.ledger_records in share row exclusive mode;
  for item in select value from jsonb_array_elements(payload->'leads') loop
   if coalesce(item->>'lead_id','') !~ '^[a-f0-9]{32}$' or coalesce(item->>'website','') !~ '^https://' or
      coalesce(length(btrim(item->>'company')),0) not between 1 and 300 or
      coalesce(item->>'country','') in ('','NA') or item->>'role' !~* '(import|export|buyer|supplier|grower)' then
    rejected:=rejected+1; continue;
   end if;
   select count(*) into candidate_count from trade_private.ledger_records r
   where r.collection='contacts' and
    (r.record_id='WEB-'||(item->>'lead_id') or
     (regexp_replace(lower(r.data->>'name'),'[^[:alnum:]]','','g')=regexp_replace(lower(item->>'company'),'[^[:alnum:]]','','g')
      and lower(btrim(r.data->>'country'))=lower(btrim(item->>'country'))));
   if candidate_count>1 then rejected:=rejected+1; continue; end if;
   select * into existing from trade_private.ledger_records r where r.collection='contacts' and
    (r.record_id='WEB-'||(item->>'lead_id') or
     (regexp_replace(lower(r.data->>'name'),'[^[:alnum:]]','','g')=regexp_replace(lower(item->>'company'),'[^[:alnum:]]','','g')
      and lower(btrim(r.data->>'country'))=lower(btrim(item->>'country'))));
   if existing.archived then duplicates:=duplicates+1; continue; end if;
   current_data:=coalesce(existing.data,jsonb_build_object(
     'id','WEB-'||(item->>'lead_id'),'name',item->>'company','country',item->>'country',
     'role',case when item->>'role' ~* '(import|buyer)' then 'Buyer' when item->>'role' ~* 'export' then 'Exporter' else 'Grower / supplier' end,
     'stage','New','priority','Unassessed','verified',false,'discovery',true,'discovered',current_date::text));
   merged:=current_data;
   foreach field in array array['email','phone','product','city','region','address','person','designation','hsCode'] loop
    if coalesce(nullif(btrim(merged->>field),''),'NA')='NA' and coalesce(nullif(btrim(item->>field),''),'NA')<>'NA' then
     merged:=jsonb_set(merged,array[field],item->field);
    end if;
   end loop;
   if coalesce(nullif(btrim(merged->>'source'),''),'NA')='NA' then
    merged:=jsonb_set(merged,'{source}',item->'website');
   end if;
   if not (coalesce(merged->'discoverySources','[]'::jsonb) @> jsonb_build_array(item->>'website')) then
    merged:=jsonb_set(merged,'{discoverySources}',coalesce(merged->'discoverySources','[]'::jsonb)||jsonb_build_array(item->>'website'));
   end if;
   if existing.record_id is null or merged is distinct from current_data then
    perform trade_private.save_ledger_record('contacts',merged->>'id',coalesce(existing.revision,0),merged,false);
    if existing.record_id is null then inserted:=inserted+1; else updated:=updated+1; end if;
   else duplicates:=duplicates+1;
   end if;
  end loop;
  saved_summary:=saved_summary||jsonb_build_object('status',case when inserted+updated+duplicates=0 then 'failed' else 'saved' end,
   'inserted',inserted,'updated',updated,'duplicates',duplicates,'rejected',rejected);
 end if;
 insert into trade_private.crawl_runs(run_id,summary) values(run_key,saved_summary)
 on conflict(run_id) do update set summary=excluded.summary;
 return saved_summary;
end;
$$;
revoke all on function public.trade_crawler_ledger(text,text,bigint) from public,anon,authenticated;
grant execute on function public.trade_crawler_ledger(text,text,bigint) to anon;
commit;
