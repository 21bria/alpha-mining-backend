CREATE OR REPLACE VIEW public.v_mine_hm_unit_detail_uuid AS
SELECT
    d.id,
    d.start_time,
    d.end_time,
    d.duration_min,
    d.category,
    d.remark,
    d.created_at,
    d.activity_id,
    d.hm_unit_id,
    d.location_id AS old_location_id,
    loc.new_id AS location_uuid,
    d.status_id
FROM public.mine_hm_unit_detail d
LEFT JOIN public.v_mine_unit_location_uuid loc
    ON loc.old_id = d.location_id;