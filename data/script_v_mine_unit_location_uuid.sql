CREATE OR REPLACE VIEW public.v_mine_unit_location_uuid AS
SELECT
    l.id AS old_id,
    (
        substr(md5('mine_unit_location:' || l.id::text || ':' || l.code), 1, 8) || '-' ||
        substr(md5('mine_unit_location:' || l.id::text || ':' || l.code), 9, 4) || '-' ||
        substr(md5('mine_unit_location:' || l.id::text || ':' || l.code), 13, 4) || '-' ||
        substr(md5('mine_unit_location:' || l.id::text || ':' || l.code), 17, 4) || '-' ||
        substr(md5('mine_unit_location:' || l.id::text || ':' || l.code), 21, 12)
    )::uuid AS new_id,
    l.code,
    l.name
FROM public.mine_unit_location l;