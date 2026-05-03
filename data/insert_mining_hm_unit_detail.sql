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
    COALESCE(d.created_at, now()),
    now(),
    'IUP-001-' ||
    COALESCE(h.unit_id::text, '0') || '-' ||
    COALESCE(TO_CHAR(h."date", 'YYYYMMDD'), '00000000') || '-' ||
    COALESCE(h.shift, 'NA') || '-' ||
    COALESCE(TO_CHAR(d.start_time, 'HH24MISS'), '000000') || '-' ||
    COALESCE(TO_CHAR(d.end_time, 'HH24MISS'), '000000'),
    false,
    NULL,
    d.id,
    d.start_time,
    d.end_time,
    COALESCE(NULLIF(d.duration_min::text, '')::integer, 0),
    d.category,
    d.remark,
    NULLIF(d.activity_id::text, '')::bigint,
    d.hm_unit_id,
    1,
    loc.new_id AS location_id,
    NULLIF(d.status_id::text, '')::bigint,
    1
FROM ext_kqms.mine_hm_unit_detail d
JOIN ext_kqms.mine_hm_unit h
  ON h.id = d.hm_unit_id
LEFT JOIN ext_kqms.v_mine_unit_location_uuid loc
  ON loc.old_id = d.location_id
WHERE NOT EXISTS (
    SELECT 1
    FROM kawi.mining_hm_unit_detail t
    WHERE t.id = d.id
);