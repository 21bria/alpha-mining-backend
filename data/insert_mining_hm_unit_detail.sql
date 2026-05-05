INSERT INTO kawi.mining_hm_unit_detail (
    created_at,
    updated_at,
    code,
    is_deleted,
    deleted_at,
    id,
    start_time,
    end_time,
    duration_min,
    category,
    description,
    activity_id,
    hm_unit_id,
    iup_id,
    location_id,
    status_id,
    user_id
)
SELECT
    x.created_at,
    x.updated_at,
    x.code,
    x.is_deleted,
    x.deleted_at,
    x.id,
    x.start_time,
    x.end_time,
    x.duration_min,
    x.category,
    x.description,
    x.activity_id,
    x.hm_unit_id,
    x.iup_id,
    x.location_id,
    x.status_id,
    x.user_id
FROM (
    SELECT DISTINCT ON (d.id)
        COALESCE(d.created_at, NOW()) AS created_at,
        NOW() AS updated_at,
        'IUP-001-' ||
        COALESCE(h.unit_id::text, '0') || '-' ||
        COALESCE(TO_CHAR(h."date", 'YYYYMMDD'), '00000000') || '-' ||
        COALESCE(h.shift, 'NA') || '-' ||
        COALESCE(TO_CHAR(d.start_time, 'HH24MISS'), '000000') || '-' ||
        COALESCE(TO_CHAR(d.end_time, 'HH24MISS'), '000000') AS code,
        FALSE AS is_deleted,
        NULL::timestamptz AS deleted_at,
        d.id,
        d.start_time,
        d.end_time,
        COALESCE(NULLIF(d.duration_min::text, '')::integer, 0) AS duration_min,
        d.category,
        d.remark AS description,
        NULLIF(d.activity_id::text, '')::bigint AS activity_id,
        d.hm_unit_id,
        1 AS iup_id,
        loc.new_id AS location_id,
        NULLIF(d.status_id::text, '')::bigint AS status_id,
        1 AS user_id
    FROM ext_kqms.mine_hm_unit_detail d
    JOIN ext_kqms.mine_hm_unit h
        ON h.id = d.hm_unit_id
    LEFT JOIN ext_kqms.v_mine_unit_location_uuid loc
        ON loc.old_id = d.location_id
    ORDER BY d.id, d.created_at DESC NULLS LAST
) x
ON CONFLICT (id) DO NOTHING;