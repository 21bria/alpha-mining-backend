INSERT INTO kawi.master_activity_locations (
    created_at,
    updated_at,
    code,
    is_deleted,
    deleted_at,
    id,
    "name",
    description,
    iup_id,
    user_id
)
SELECT
    NOW(),
    NOW(),
    x.code,
    FALSE,
    NULL,
    x.new_id,
    x.name,
    NULL,
    1,
    1
FROM (
    SELECT DISTINCT ON (s.new_id)
        s.new_id,
        s.code,
        s.name
    FROM ext_kqms.v_mine_unit_location_uuid s
    ORDER BY s.new_id, s.code, s.name
) x
ON CONFLICT (id) DO NOTHING;

-- UPDATE ?
INSERT INTO kawi.master_activity_locations (
    created_at,
    updated_at,
    code,
    is_deleted,
    deleted_at,
    id,
    "name",
    description,
    iup_id,
    user_id
)
SELECT
    now(),
    now(),
    s.code,
    false,
    NULL,
    s.new_id,
    s.name,
    NULL,
    1,
    1
FROM ext_kqms.v_mine_unit_location_uuid s
ON CONFLICT (id) DO UPDATE SET
    code = EXCLUDED.code,
    name = EXCLUDED.name,
    updated_at = now();