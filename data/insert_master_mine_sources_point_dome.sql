INSERT INTO kawi.master_mine_sources_point_dome (
    id,
    created_at,
    updated_at,
    code,
    is_deleted,
    deleted_at,
    pile_id,
    description,
    category,
    compositing,
    dome_finish,
    status_dome,
    plan_ni_min,
    plan_ni_max,
    status,
    direct_sale,
    latitude,
    longitude,
    geometry,
    extra_properties,
    iup_id,
    user_id,
    id_dumping
)
SELECT
    s.id,
    COALESCE(s.created_at, NOW()),
    COALESCE(s.updated_at, NOW()),
    -- code generate dari pile_id
    'IUP-001-' || s.pile_id,
    FALSE,
    NULL,
    s.pile_id,
    s.remarks,
    s.category,
    s.compositing,
    s.dome_finish,
    s.status_dome,
    s.plan_ni_min,
    s.plan_ni_max,
    COALESCE(s.status, 1),
    s.direct_sale,
    s.latitude,
    s.longitude,
    s.geometry,
    '{}'::jsonb AS extra_properties,
    1 AS iup_id,
    1 AS user_id,
    s.id_dumping
FROM ext_kqms.mine_sources_point_dome s
WHERE NOT EXISTS (
    SELECT 1
    FROM kawi.master_mine_sources_point_dome t
    WHERE t.id = s.id
);