begin;

create table if not exists trade_private.ledger_records (
    collection text not null check (collection in ('contacts', 'calls', 'deals', 'milestones', 'cash')),
    record_id text not null check (length(record_id) between 1 and 200),
    data jsonb not null check (jsonb_typeof(data) = 'object'),
    revision bigint not null default 1 check (revision > 0),
    archived boolean not null default false,
    updated_at timestamptz not null default now(),
    primary key (collection, record_id)
);

create table if not exists trade_private.ledger_history (
    collection text not null,
    record_id text not null,
    revision bigint not null,
    data jsonb not null,
    archived boolean not null,
    changed_at timestamptz not null,
    primary key (collection, record_id, revision),
    foreign key (collection, record_id)
        references trade_private.ledger_records (collection, record_id)
);

alter table trade_private.ledger_records enable row level security;
alter table trade_private.ledger_history enable row level security;
revoke all on trade_private.ledger_records, trade_private.ledger_history from public, anon, authenticated;

create or replace function trade_private.save_ledger_record(
    p_collection text, p_record_id text, p_revision bigint, p_data jsonb, p_archived boolean
) returns bigint language plpgsql security invoker set search_path = '' as $$
declare
    saved trade_private.ledger_records;
begin
    if p_revision = 0 then
        insert into trade_private.ledger_records (collection, record_id, data, archived)
        values (p_collection, p_record_id, p_data, p_archived)
        on conflict do nothing returning * into saved;
    else
        update trade_private.ledger_records
        set data = p_data, archived = p_archived, revision = revision + 1, updated_at = now()
        where collection = p_collection and record_id = p_record_id and revision = p_revision
        returning * into saved;
    end if;
    if saved.revision is null then
        raise exception 'Record changed. Reload before saving.' using errcode = '40001';
    end if;
    insert into trade_private.ledger_history
        (collection, record_id, revision, data, archived, changed_at)
    values (saved.collection, saved.record_id, saved.revision, saved.data, saved.archived, saved.updated_at);
    return saved.revision;
end;
$$;
revoke all on function trade_private.save_ledger_record(text, text, bigint, jsonb, boolean) from public, anon, authenticated;

commit;
