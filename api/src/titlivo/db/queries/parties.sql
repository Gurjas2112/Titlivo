-- Names for a set of party ids. Params: ids (text[])
select id, name, name_local from titlivo.parties where id = any(%(ids)s::text[])
