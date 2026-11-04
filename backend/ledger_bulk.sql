begin;
create or replace function public.trade_ledger(p_body text, p_signature text, p_timestamp bigint)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare
  request jsonb := p_body::jsonb;
  secret text;
  model jsonb;
  collection text;
  record jsonb;
  version bigint;
  imported integer := 0;
begin
  select signing_secret into secret from trade_private.sync_sources
  where spreadsheet_id = '1wNPYCBBXAn3y2uJ4LOV6vGgWzYhro_PPGk2HsU0cjj0';
  if secret is null or p_timestamp is null or abs(extract(epoch from now())-p_timestamp)>300
     or p_signature is distinct from encode(extensions.hmac(convert_to(p_timestamp::text||'.'||p_body,'UTF8'),convert_to(secret,'UTF8'),'sha256'),'hex') then
    raise exception 'Unauthorized' using errcode = '42501';
  end if;
  case request->>'action'
    when 'read' then
      select cache.model into model from trade_private.dashboard_cache cache
      where spreadsheet_id = '1wNPYCBBXAn3y2uJ4LOV6vGgWzYhro_PPGk2HsU0cjj0';
      if model is null then raise exception 'No dashboard snapshot'; end if;
      return jsonb_build_object('model', model, 'records',
        (select coalesce(jsonb_agg(to_jsonb(r)), '[]'::jsonb) from trade_private.ledger_records r));
    when 'save' then
      collection := request->>'collection';
      record := request->'record';
      version := trade_private.save_ledger_record(collection, record->>'id',
        (request->>'revision')::bigint, record, (request->>'archived')::boolean);
      return jsonb_build_object('revision',version);
    when 'import' then
      if jsonb_typeof(request->'records') is distinct from 'array' or jsonb_array_length(request->'records') not between 1 and 500 then
        raise exception 'Invalid import size';
      end if;
      lock table trade_private.ledger_records in share row exclusive mode;
      for record in select value from jsonb_array_elements(request->'records') loop
        if exists (select 1 from trade_private.ledger_records r where r.collection='contacts'
          and lower(btrim(r.data->>'name'))=lower(btrim(record->>'name'))
          and lower(btrim(coalesce(r.data->>'country','')))=lower(btrim(coalesce(record->>'country','')))) then
          continue;
        end if;
        perform trade_private.save_ledger_record('contacts',record->>'id',0,record,false);
        imported := imported + 1;
      end loop;
      return jsonb_build_object('imported',imported,'skipped',jsonb_array_length(request->'records')-imported);
    else raise exception 'Unknown action';
  end case;
end;
$$;
revoke all on function public.trade_ledger(text,text,bigint) from public;
grant execute on function public.trade_ledger(text,text,bigint) to anon;
commit;
