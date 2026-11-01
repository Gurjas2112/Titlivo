-- Named example parcels (hero parcel + one per planted flag) for tours, screenshots and Postman.
create table if not exists titlivo.demo_parcels (
    key        text primary key,
    parcel_id  text not null references titlivo.parcels(id) on delete cascade
);
