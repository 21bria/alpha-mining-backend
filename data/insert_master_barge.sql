INSERT INTO kawi.master_barge (
    id,
    barge_code,
    barge_name,
    capacity,
    description,
    active,
    created_at,
    updated_at,
    user_id
)
SELECT
    s.id,
    s.barge_code,
    s.barge_name,
    -- numeric safe
    COALESCE(NULLIF(s.capacity::text, '')::numeric, 0),
    s.description,
    -- FIX: tambah koma
    COALESCE(NULLIF(s.active::text, '')::integer, 1),
    COALESCE(s.created_at, now()),
    COALESCE(s.updated_at, now()),
    1 AS user_id
FROM ext_kqms.master_barge s;
--  ANTI DUPLICATE
-- WHERE NOT EXISTS (
--     SELECT 1
--     FROM kawi.master_barge t
--     WHERE t.id = s.id
-- );