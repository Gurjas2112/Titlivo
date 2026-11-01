-- Titlivo core schema (spec §8). Plain Postgres + PostGIS so it runs on the local
-- docker image and on Supabase unchanged. All data is synthetic (synthetic = true).

create extension if not exists postgis;
create extension if not exists pg_trgm;

create schema if not exists titlivo;
set search_path = titlivo, public;

create table if not exists titlivo.villages (
    id            text primary key,              -- DEMO-V-<state>-<n>
    state_code    text not null,                 -- LGD state code: 27 MH, 29 KA, 24 GJ
    state         text not null,
    district      text not null,
    taluk         text not null,
    name          text not null,
    name_local    text not null,
    geom          geometry(MultiPolygon, 4326) not null,
    synthetic     boolean not null default true
);

create table if not exists titlivo.source_records (
    id            text primary key,              -- DEMO-SR-…
    state_code    text not null,
    record_type   text not null,                 -- mh_712 | ka_rtc | gj_712
    system_name   text not null,                 -- e.g. "Mahabhumi 7/12 (synthetic)"
    native        jsonb not null,                -- the record exactly as the state issues it
    as_of         date not null,
    synthetic     boolean not null default true
);

create table if not exists titlivo.parcels (
    id                text primary key,          -- demo ULPIN: DEMO-<2-digit state><12-char geohash>
    state_code        text not null,
    village_id        text not null references titlivo.villages(id),
    survey_no         text not null,
    area_m2           numeric(14,2) not null,    -- recorded area, converted to m²
    native_area       text not null,             -- as written in the record, e.g. "1.25"
    native_unit       text not null,             -- hectare_are | acre_gunta | hectare_are_sqm
    tenure_class      text not null,             -- canonical code, see config/glossary
    land_class        text not null,
    geom              geometry(Polygon, 4326) not null,
    source_record_id  text not null references titlivo.source_records(id),
    version           integer not null default 1,
    synthetic         boolean not null default true,
    unique (village_id, survey_no)
);
create index if not exists parcels_geom_idx on titlivo.parcels using gist (geom);
create index if not exists parcels_survey_trgm on titlivo.parcels using gin (survey_no gin_trgm_ops);

create table if not exists titlivo.parties (
    id          text primary key,                -- DEMO-PTY-…
    name        text not null,                   -- Latin display name
    name_local  text not null,                   -- name in the state's script
    name_key    text not null,                   -- lower-case, diacritics stripped, for search
    synthetic   boolean not null default true
);
create index if not exists parties_name_key_trgm on titlivo.parties using gin (name_key gin_trgm_ops);

create table if not exists titlivo.holdings (
    parcel_id  text not null references titlivo.parcels(id) on delete cascade,
    party_id   text not null references titlivo.parties(id),
    share      numeric(6,4) not null,
    primary key (parcel_id, party_id)
);

create table if not exists titlivo.title_events (
    id                text primary key,          -- DEMO-EV-…
    parcel_id         text not null references titlivo.parcels(id) on delete cascade,
    seq               integer not null,          -- order within the parcel (registration order)
    event_type        text not null,             -- grant | sale | gift | succession | partition | gpa | mutation
    native_term       text not null,             -- the state's own word for it
    registered_on     date not null,
    from_parties      text[] not null default '{}',
    to_parties        text[] not null default '{}',
    doc_no            text,
    amount_inr        bigint,
    mutation_no       text,
    mutation_status   text,                      -- certified | pending
    basis_ref         text,                      -- e.g. death certificate ref for a succession
    remarks           text,
    source_record_id  text not null references titlivo.source_records(id),
    injected          boolean not null default false,  -- added through /v1/admin/events (demo)
    unique (parcel_id, seq)
);
create index if not exists title_events_parcel_idx on titlivo.title_events (parcel_id, registered_on);

create table if not exists titlivo.encumbrances (
    id                text primary key,
    parcel_id         text not null references titlivo.parcels(id) on delete cascade,
    kind              text not null,             -- mortgage | charge | lien
    native_term       text not null,
    lender            text not null,
    amount_inr        bigint not null,
    created_on        date not null,
    released_on       date,
    status            text not null,             -- active | released
    mutation_no       text,
    source_record_id  text not null references titlivo.source_records(id),
    injected          boolean not null default false
);
create index if not exists encumbrances_parcel_idx on titlivo.encumbrances (parcel_id);

create table if not exists titlivo.litigation (
    id                text primary key,
    parcel_id         text not null references titlivo.parcels(id) on delete cascade,
    case_no           text not null,
    court             text not null,
    status            text not null,             -- pending | stay | disposed
    filed_on          date not null,
    source_record_id  text not null references titlivo.source_records(id)
);

-- Flags are recomputed from SQL rules (api/src/titlivo/db/queries/flags/*.sql) and cached here
-- for the map and for passports. The rules, not this table, are the source of truth.
create table if not exists titlivo.parcel_flags (
    id                bigserial primary key,
    parcel_id         text not null references titlivo.parcels(id) on delete cascade,
    flag_id           text not null,
    severity          text not null,
    evidence          jsonb not null,
    source_record_id  text,
    computed_at       timestamptz not null default now()
);
create index if not exists parcel_flags_parcel_idx on titlivo.parcel_flags (parcel_id);
