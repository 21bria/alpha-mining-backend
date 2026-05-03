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
    now() AS created_at,
    now() AS updated_at,
    s.code,
    false AS is_deleted,
    NULL AS deleted_at,
    s.new_id AS id,
    s.name,
    NULL AS description,
    1 AS iup_id,
    1 AS user_id
FROM ext_kqms.v_mine_unit_location_uuid s
WHERE NOT EXISTS (
    SELECT 1
    FROM kawi.master_activity_locations t
    WHERE t.id = s.new_id
);

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