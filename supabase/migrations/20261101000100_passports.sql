-- Title Passports, status lists and the events that change them (spec §6.10, §6.12).
set search_path = titlivo, public;

create table if not exists titlivo.status_lists (
    id           integer primary key,
    purpose      text not null check (purpose in ('suspension', 'revocation')),
    size_bits    integer not null,
    bits         bytea not null,
    next_free    integer not null default 0,
    updated_at   timestamptz not null default now()
);

create table if not exists titlivo.passports (
    id                 uuid primary key,
    parcel_id          text not null references titlivo.parcels(id) on delete cascade,
    parcel_version     integer not null,
    jwt                text not null,
    suspension_list    integer not null references titlivo.status_lists(id),
    suspension_index   integer not null,
    revocation_list    integer not null references titlivo.status_lists(id),
    revocation_index   integer not null,
    issued_at          timestamptz not null,
    valid_until        timestamptz not null,
    superseded_by      uuid references titlivo.passports(id),
    unique (suspension_list, suspension_index),
    unique (revocation_list, revocation_index)
);
create index if not exists passports_parcel_idx on titlivo.passports (parcel_id);

create table if not exists titlivo.passport_events (
    id           bigserial primary key,
    passport_id  uuid not null references titlivo.passports(id) on delete cascade,
    kind         text not null,                 -- issued | suspended | reinstated | revoked
    reason       text,
    flag_ids     text[] not null default '{}',
    at           timestamptz not null default now()
);

insert into titlivo.status_lists (id, purpose, size_bits, bits)
values (1, 'suspension', 131072, decode(repeat('00', 16384), 'hex')),
       (2, 'revocation', 131072, decode(repeat('00', 16384), 'hex'))
on conflict (id) do nothing;
