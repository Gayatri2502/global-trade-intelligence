begin;
create table trade_private.ledger_sheet_baseline (
 collection text, record_id text, data jsonb not null,
 primary key (collection, record_id)
);
create table trade_private.ledger_sync_review (
 collection text, record_id text, field text, reason text not null,
 primary key (collection, record_id, field)
);
alter table trade_private.ledger_sheet_baseline enable row level security;
alter table trade_private.ledger_sync_review enable row level security;
revoke all on trade_private.ledger_sheet_baseline, trade_private.ledger_sync_review from public, anon, authenticated;

create function trade_private.reconcile_ledger() returns trigger
language plpgsql security definer set search_path='' as $$
declare
 kind text;
 incoming record;
 saved trade_private.ledger_records;
 baseline jsonb;
 merged jsonb;
 field_name text;
begin
 if new.spreadsheet_id <> '1wNPYCBBXAn3y2uJ4LOV6vGgWzYhro_PPGk2HsU0cjj0' then return new; end if;
 foreach kind in array array['contacts','calls','deals','milestones','cash'] loop
  for incoming in
   select coalesce(btrim(value->>'id'),'') id, count(*) copies, min(value::text)::jsonb data
   from jsonb_array_elements(coalesce(new.model->kind,'[]'))
   where coalesce(value->>'id','') not ilike 'TEST-%'
   group by 1
  loop
   if incoming.id='' or incoming.copies<>1 then
    insert into trade_private.ledger_sync_review values(kind,incoming.id,'id','Missing or duplicate ID') on conflict do nothing;
    continue;
   end if;
   delete from trade_private.ledger_sync_review where collection=kind and record_id=incoming.id and field in ('id','__deleted__');
   select * into saved from trade_private.ledger_records where collection=kind and record_id=incoming.id for update;
   select data into baseline from trade_private.ledger_sheet_baseline where collection=kind and record_id=incoming.id;
   if saved.revision is null then
    perform trade_private.save_ledger_record(kind,incoming.id,0,incoming.data,false);
   elsif baseline is not null then
    merged := saved.data;
    for field_name in select jsonb_object_keys(incoming.data || baseline) loop
     if incoming.data->field_name is not distinct from baseline->field_name then continue; end if;
     if saved.data->field_name is not distinct from baseline->field_name or saved.data->field_name is not distinct from incoming.data->field_name then
      merged := (merged-field_name) || case when incoming.data ? field_name then jsonb_build_object(field_name,incoming.data->field_name) else '{}'::jsonb end;
      delete from trade_private.ledger_sync_review where collection=kind and record_id=incoming.id and field=field_name;
     else
      insert into trade_private.ledger_sync_review values(kind,incoming.id,field_name,'Changed in both Sheets and Trade Ledger') on conflict do nothing;
      incoming.data := (incoming.data-field_name) || case when baseline ? field_name then jsonb_build_object(field_name,baseline->field_name) else '{}'::jsonb end;
     end if;
    end loop;
    if merged is distinct from saved.data then
     perform trade_private.save_ledger_record(kind,incoming.id,saved.revision,merged,saved.archived);
    end if;
   end if;
   insert into trade_private.ledger_sheet_baseline values(kind,incoming.id,incoming.data)
   on conflict (collection,record_id) do update set data=excluded.data;
  end loop;
  insert into trade_private.ledger_sync_review
   select kind,b.record_id,'__deleted__','Row removed from Sheets. Review before archiving.'
   from trade_private.ledger_sheet_baseline b where b.collection=kind
   and not exists (select 1 from jsonb_array_elements(coalesce(new.model->kind,'[]')) v where btrim(v->>'id')=b.record_id)
   on conflict do nothing;
 end loop;
 return new;
end;
$$;
revoke all on function trade_private.reconcile_ledger() from public, anon, authenticated;
create trigger reconcile_ledger_snapshot after insert or update of model on trade_private.dashboard_cache
for each row execute function trade_private.reconcile_ledger();
update trade_private.dashboard_cache set model=model where spreadsheet_id='1wNPYCBBXAn3y2uJ4LOV6vGgWzYhro_PPGk2HsU0cjj0';
commit;
