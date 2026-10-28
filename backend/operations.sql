-- Separate read/backup key; no access through anonymous/authenticated roles.
create table if not exists trade_private.dashboard_cache (
 spreadsheet_id text primary key, model jsonb not null, source_hash text not null, updated_at timestamptz not null default now()
);
alter table trade_private.dashboard_cache enable row level security;
revoke all on trade_private.dashboard_cache from public,anon,authenticated;
create or replace function public.trade_operations(p_body text,p_signature text,p_timestamp bigint)
returns jsonb language plpgsql security definer set search_path='' as $$
declare p jsonb:=p_body::jsonb; secret text; data jsonb; bin bytea; digest text; source text;
begin
 select signing_secret into secret from trade_private.sync_sources where spreadsheet_id=(case when p->>'kind'='backup_upload' then '' else 'operations:' end)||(p->>'spreadsheetId');
 if secret is null or abs(extract(epoch from now())-p_timestamp)>300 or p_signature is null or p_signature<>encode(extensions.hmac(convert_to(p_timestamp::text||'.'||p_body,'UTF8'),convert_to(secret,'UTF8'),'sha256'),'hex') then raise exception 'Unauthorized'; end if;
 if p->>'kind'='snapshot_read' then
 select jsonb_build_object('snapshot',s.payload,'hash',s.content_hash,'lastSync',src.last_sync_at) into data from trade_private.sync_sources src join trade_private.sheet_snapshots s on s.spreadsheet_id=src.spreadsheet_id and s.content_hash=src.last_hash where src.spreadsheet_id=p->>'spreadsheetId';
 elsif p->>'kind'='model_upload' then
 select last_hash into source from trade_private.sync_sources where spreadsheet_id=p->>'spreadsheetId';
 if source is distinct from p->>'sourceHash' then raise exception 'Snapshot changed; retry'; end if;
 insert into trade_private.dashboard_cache values(p->>'spreadsheetId',p->'model',source,now()) on conflict(spreadsheet_id) do update set model=excluded.model,source_hash=excluded.source_hash,updated_at=now(); data:='{"ok":true}';
 elsif p->>'kind'='dashboard_read' then
 select jsonb_build_object('model',model,'updatedAt',updated_at) into data from trade_private.dashboard_cache where spreadsheet_id=p->>'spreadsheetId';
 elsif p->>'kind'='backup_upload' then
 bin:=decode(p->>'content','base64'); if octet_length(bin)>8000000 or substring(bin from 1 for 2)<>decode('504b','hex') then raise exception 'Invalid workbook archive'; end if;
 digest:=encode(extensions.digest(bin,'sha256'),'hex');
 insert into trade_private.workbook_archives(sha256,filename,content) values(digest,'Trade_Business_Dashboard.xlsx',bin) on conflict do nothing; data:=jsonb_build_object('ok',true,'sha256',digest);
 elsif p->>'kind'='backup_read' then
 select jsonb_build_object('sha256',sha256,'content',encode(content,'base64'),'createdAt',created_at) into data from trade_private.workbook_archives order by created_at desc limit 1;
 else raise exception 'Unknown operation'; end if;
 if data is null then raise exception 'No data available'; end if; return data;
end $$;
revoke all on function public.trade_operations(text,text,bigint) from public,anon,authenticated;
grant execute on function public.trade_operations(text,text,bigint) to service_role;
