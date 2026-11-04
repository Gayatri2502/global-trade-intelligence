create or replace function public.trade_crawler_control(p_body text,p_signature text,p_timestamp bigint)
returns jsonb language plpgsql security definer set search_path='' as $$
declare
 p jsonb := p_body::jsonb;
 action text := p->>'action';
 source_id text := 'public-company-sites';
 secret text;
 target text;
 result jsonb;
begin
 if action is null or action not in ('view','queue','claim','progress') then raise exception 'Invalid operation'; end if;
 select signing_secret into secret from trade_private.sync_sources
 where spreadsheet_id=(case when action in ('claim','progress') then 'crawler:' else '' end)||'1wNPYCBBXAn3y2uJ4LOV6vGgWzYhro_PPGk2HsU0cjj0';
 if secret is null or p_timestamp is null or abs(extract(epoch from now())-p_timestamp)>300 or
 p_signature is distinct from encode(extensions.hmac(convert_to(p_timestamp::text||'.'||p_body,'UTF8'),convert_to(secret,'UTF8'),'sha256'),'hex')
 then raise exception 'Unauthorized' using errcode='42501'; end if;
 if action='view' then
  select coalesce(jsonb_agg(q.summary order by q.started_at desc),'[]') into result from (
   select started_at,summary||jsonb_build_object('run_id',run_id) as summary from trade_private.crawl_runs
   where summary->>'source'=source_id order by started_at desc limit 10
  ) q;
  return jsonb_build_object('runs',result);
 end if;
 perform pg_advisory_xact_lock(hashtext('trade-crawler-control'));
 if action='queue' then
  select run_id into target from trade_private.crawl_runs where summary->>'source'=source_id
   and (summary->>'status'='queued' or (summary->>'status'='running' and (summary->>'heartbeat')::timestamptz>now()-interval '12 minutes'))
   order by started_at desc limit 1;
  if target is not null then return jsonb_build_object('run_id',target,'existing',true); end if;
  target:='public-company-sites:requested:'||gen_random_uuid()::text;
  insert into trade_private.crawl_runs(run_id,summary) values(target,jsonb_build_object('source',source_id,'status','queued','stage','queued','requested_at',now()));
  return jsonb_build_object('run_id',target,'existing',false);
 end if;
 if action='claim' then
  select run_id into target from trade_private.crawl_runs where summary->>'source'=source_id
    and (summary->>'status'='queued' or (run_id like 'public-company-sites:requested:%' and summary->>'status'='running' and (summary->>'heartbeat')::timestamptz<now()-interval '12 minutes'))
    order by started_at limit 1;
  if target is null then return '{}'::jsonb; end if;
  update trade_private.crawl_runs set summary=summary||jsonb_build_object('status','running','stage','connecting','heartbeat',now()) where run_id=target;
  return jsonb_build_object('run_id',target);
 end if;
 target:=p->>'run_id';
 if target is null or target not like 'public-company-sites:%' or length(target)>160
    or p->>'stage' not in ('connecting','crawling','saving') then raise exception 'Invalid progress'; end if;
 insert into trade_private.crawl_runs(run_id,summary) values(target,jsonb_build_object(
   'source',source_id,'status','running','stage',p->>'stage','heartbeat',now(),
   'pages_fetched',(p->>'pages_fetched')::integer,'discovered',(p->>'discovered')::integer,
   'failed_requests',(p->>'failed_requests')::integer,'started_at',p->>'started_at'))
 on conflict(run_id) do update set summary=trade_private.crawl_runs.summary||excluded.summary
 where trade_private.crawl_runs.summary->>'status'<>'saved';
 return '{}'::jsonb;
end;
$$;
revoke all on function public.trade_crawler_control(text,text,bigint) from public,anon,authenticated;
grant execute on function public.trade_crawler_control(text,text,bigint) to anon;
