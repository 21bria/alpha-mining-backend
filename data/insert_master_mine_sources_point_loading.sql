INSERT INTO kawi.master_mine_sources_point_loading (
    id,
    created_at,
    updated_at,
    code,
    is_deleted,
    deleted_at,
    loading_point,
    description,
    category,
    status,
    latitude,
    longitude,
    geometry,
    extra_properties,
    iup_id,
    id_sources,
    user_id
)
SELECT
    s.id,
    COALESCE(s.created_at, NOW()),
    COALESCE(s.updated_at, NOW()),
    -- code (generate dari loading_point)
    'IUP-001-' || s.loading_point,
    -- soft delete default
    FALSE,
    NULL,
    -- data utama
    s.loading_point,
    s.remarks,
    s.category,
    COALESCE(s.status, 1),
    s.latitude,
    s.longitude,
    s.geometry,
    s.extra_properties,
    -- relasi
    1 AS iup_id,        -- <-- ganti sesuai IUP
    s.id_sources,
    1 AS user_id        -- <-- ganti sesuai user
FROM ext_kqms.mine_sources_point_loading s
-- ANTI DUPLICATE
WHERE NOT EXISTS (
    SELECT 1
    FROM kawi.master_mine_sources_point_loading t
    WHERE t.id = s.id
);