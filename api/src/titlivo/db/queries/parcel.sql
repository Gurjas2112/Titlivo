-- One parcel with its village, mapped area and GeoJSON geometry. Params: parcel_id
select p.id, p.state_code, p.village_id, p.survey_no, p.area_m2, p.native_area, p.native_unit,
       p.tenure_class, p.land_class, p.version, p.source_record_id,
       round(st_area(p.geom::geography)::numeric) as mapped_area_m2,
       st_asgeojson(p.geom, 6)::jsonb as geometry,
       st_y(st_centroid(p.geom)) as lat, st_x(st_centroid(p.geom)) as lon,
       v.name as village, v.name_local as village_local, v.district, v.taluk, v.state,
       sr.record_type, sr.system_name, sr.native, sr.as_of
from titlivo.parcels p
join titlivo.villages v on v.id = p.village_id
join titlivo.source_records sr on sr.id = p.source_record_id
where p.id = %(parcel_id)s
