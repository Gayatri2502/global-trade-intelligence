create table trade_private.sync_sources (
 spreadsheet_id text primary key,
 signing_secret text not null,
 last_version bigint not null default 0,
 last_sync_at timestamptz,
 last_hash text
);
create table trade_private.sheet_snapshots (
 spreadsheet_id text not null references trade_private.sync_sources,
 content_hash text not null,
 captured_at timestamptz not null default now(),
 payload jsonb not null,
 primary key(spreadsheet_id,content_hash)
);
create table trade_private.sheet_records (
 spreadsheet_id text not null references trade_private.sync_sources,
 sheet_id text not null,
 record_id text not null,
 sheet_name text not null,
 row_data jsonb not null,
 updated_at timestamptz not null default now(),
 deleted_at timestamptz,
 primary key(spreadsheet_id,sheet_id,record_id)
);
create table trade_private.change_events (
 event_id bigint generated always as identity primary key,
 spreadsheet_id text not null,
 sheet_id text not null,
 record_id text not null,
 action text not null check(action in ('INSERT','UPDATE','DELETE','RESTORE')),
 before_data jsonb,
 after_data jsonb,
 recorded_at timestamptz not null default now()
);
alter table trade_private.sync_sources enable row level security;
alter table trade_private.sheet_snapshots enable row level security;
alter table trade_private.sheet_records enable row level security;
alter table trade_private.change_events enable row level security;
revoke all on all tables in schema trade_private from public,anon,authenticated;

create function public.trade_ingest(p_body text,p_signature text,p_timestamp bigint)
returns jsonb language plpgsql security definer set search_path='' as $$
declare
 payload jsonb; src trade_private.sync_sources%rowtype; sh jsonb; rec jsonb;
 oldrec trade_private.sheet_records%rowtype; ids text[]; sheets text[] := '{}';
 sid text; rid text; kind text; hash text; version bigint; changes int:=0;
begin
 if octet_length(p_body)>12000000 then raise exception 'Payload too large'; end if;
 payload:=p_body::jsonb;
 select * into src from trade_private.sync_sources where spreadsheet_id=payload->>'spreadsheetId' for update;
 if not found then raise exception 'Unauthorized'; end if;
 if abs(extract(epoch from now())-p_timestamp)>300 then raise exception 'Expired request'; end if;
 if p_signature is null or p_signature !~ '^[0-9a-f]{64}$' or
    p_signature<>encode(extensions.hmac(convert_to(p_timestamp::text||'.'||p_body,'UTF8'),convert_to(src.signing_secret,'UTF8'),'sha256'),'hex') then
    raise exception 'Unauthorized'; end if;
 version:=(payload->>'version')::bigint;
 if version<=src.last_version then return jsonb_build_object('ok',true,'status','stale_or_duplicate','version',src.last_version); end if;
 if jsonb_typeof(payload->'sheets')<>'array' or jsonb_array_length(payload->'sheets')=0 then raise exception 'Complete sheet list required'; end if;
 hash:=encode(extensions.digest((payload->'sheets')::text,'sha256'),'hex');
 if hash=src.last_hash then
   update trade_private.sync_sources set last_version=version,last_sync_at=now() where spreadsheet_id=src.spreadsheet_id;
   return jsonb_build_object('ok',true,'status','unchanged','changes',0);
 end if;
 for sh in select value from jsonb_array_elements(payload->'sheets') loop
  sid:=sh->>'sheetId';
  if sid is null or sid=any(sheets) then raise exception 'Invalid or duplicate sheet ID'; end if;
  sheets:=array_append(sheets,sid); ids:='{}';
  for rec in select value from jsonb_array_elements(sh->'records') loop
   rid:=rec->>'id';
   if rid is null or rid='' or rid=any(ids) then raise exception 'Missing or duplicate record ID'; end if;
   ids:=array_append(ids,rid);
   select * into oldrec from trade_private.sheet_records where spreadsheet_id=src.spreadsheet_id and sheet_id=sid and record_id=rid;
   kind:=null;
   if not found then kind:='INSERT';
   elsif oldrec.deleted_at is not null then kind:='RESTORE';
   elsif oldrec.row_data is distinct from rec then kind:='UPDATE'; end if;
   if kind is not null then
    insert into trade_private.change_events(spreadsheet_id,sheet_id,record_id,action,before_data,after_data)
    values(src.spreadsheet_id,sid,rid,kind,oldrec.row_data,rec);
    insert into trade_private.sheet_records(spreadsheet_id,sheet_id,record_id,sheet_name,row_data)
    values(src.spreadsheet_id,sid,rid,sh->>'name',rec)
    on conflict(spreadsheet_id,sheet_id,record_id) do update set row_data=excluded.row_data,sheet_name=excluded.sheet_name,deleted_at=null,updated_at=now();
    changes:=changes+1;
   end if;
  end loop;
  for oldrec in select * from trade_private.sheet_records where spreadsheet_id=src.spreadsheet_id and sheet_id=sid and deleted_at is null and not(record_id=any(ids)) loop
   insert into trade_private.change_events(spreadsheet_id,sheet_id,record_id,action,before_data) values(src.spreadsheet_id,sid,oldrec.record_id,'DELETE',oldrec.row_data);
   update trade_private.sheet_records set deleted_at=now(),updated_at=now() where spreadsheet_id=src.spreadsheet_id and sheet_id=sid and record_id=oldrec.record_id;
   changes:=changes+1;
  end loop;
 end loop;
 for oldrec in select * from trade_private.sheet_records where spreadsheet_id=src.spreadsheet_id and deleted_at is null and not(sheet_id=any(sheets)) loop
  insert into trade_private.change_events(spreadsheet_id,sheet_id,record_id,action,before_data) values(src.spreadsheet_id,oldrec.sheet_id,oldrec.record_id,'DELETE',oldrec.row_data);
  update trade_private.sheet_records set deleted_at=now(),updated_at=now() where spreadsheet_id=src.spreadsheet_id and sheet_id=oldrec.sheet_id and record_id=oldrec.record_id;
  changes:=changes+1;
 end loop;
 insert into trade_private.sheet_snapshots(spreadsheet_id,content_hash,payload) values(src.spreadsheet_id,hash,payload) on conflict do nothing;
 update trade_private.sync_sources set last_version=version,last_hash=hash,last_sync_at=now() where spreadsheet_id=src.spreadsheet_id;
 return jsonb_build_object('ok',true,'status','synced','changes',changes,'hash',hash);
end $$;
revoke all on function public.trade_ingest(text,text,bigint) from public,anon,authenticated;
grant execute on function public.trade_ingest(text,text,bigint) to service_role;
comment on function public.trade_ingest is 'Authenticated Sheets webhook. Service role plus per-workbook HMAC, timestamp, monotonic version and transactional soft-delete audit.';
