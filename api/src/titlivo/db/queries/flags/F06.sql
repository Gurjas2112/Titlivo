-- F06 Rapid flips: three or more sales within 24 months.
with sales as (
    select parcel_id, registered_on, mutation_no, source_record_id
    from titlivo.title_events
    where event_type = 'sale' and (%(parcel_id)s::text is null or parcel_id = %(parcel_id)s::text)
),
windows as (
    select s.parcel_id, s.registered_on as window_start, s.source_record_id,
           count(*) as sales,
           max(o.registered_on) as window_end,
           array_agg(o.mutation_no order by o.registered_on) as mutation_nos
    from sales s
    join sales o on o.parcel_id = s.parcel_id
                and o.registered_on between s.registered_on and s.registered_on + interval '730 days'
    group by s.parcel_id, s.registered_on, s.source_record_id
    having count(*) >= 3
)
select distinct on (parcel_id) parcel_id,
       jsonb_build_object('sales_in_window', sales, 'window_start', window_start, 'window_end', window_end,
                          'mutation_nos', mutation_nos) as evidence,
       source_record_id
from windows
order by parcel_id, sales desc, window_start
