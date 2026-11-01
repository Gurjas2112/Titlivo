-- F04 Recorded area differs from the mapped (geodesic) area by more than 10 percent.
select p.id as parcel_id,
       jsonb_build_object('recorded_m2', round(p.area_m2), 'mapped_m2', round(st_area(p.geom::geography)::numeric),
                          'difference_pct', round(100 * abs(p.area_m2 - st_area(p.geom::geography)::numeric)
                                                  / st_area(p.geom::geography)::numeric, 1),
                          'native_area', p.native_area, 'native_unit', p.native_unit) as evidence,
       p.source_record_id
from titlivo.parcels p
where abs(p.area_m2 - st_area(p.geom::geography)::numeric) / st_area(p.geom::geography)::numeric > 0.10
  and (%(parcel_id)s::text is null or p.id = %(parcel_id)s::text)
