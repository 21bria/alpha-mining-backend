INSERT INTO kawi.master_mine_sources_point_dumping (
    id,
    created_at,
    updated_at,
    code,
    is_deleted,
    deleted_at,
    dumping_point,
    description,
    category,
    compositing,
    status,
    geometry,
    latitude,
    longitude,
    extra_properties,
    iup_id,
    user_id
)
SELECT
    s.id,
    COALESCE(s.created_at, NOW()),
    COALESCE(s.updated_at, NOW()),
    -- code generate dari dumping_point
    'IUP-001-' || s.dumping_point,
    -- soft delete default
    FALSE,
    NULL,
    -- data utama
    s.dumping_point,
    s.remarks,
    s.category,
    s.compositing,
    COALESCE(s.status, 1),
    s.geometry,
    s.latitude,
    s.longitude,
    -- karena source tidak ada extra_properties
    '{}'::jsonb AS extra_properties,
    -- relasi
    1 AS iup_id,
    1 AS user_id
FROM ext_kqms.mine_sources_point_dumping s
-- ANTI DUPLICATE
WHERE NOT EXISTS (
    SELECT 1
    FROM kawi.master_mine_sources_point_dumping t
    WHERE t.id = s.id
);