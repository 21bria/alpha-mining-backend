INSERT INTO kawi.geology_dome_close (
    id,
    tonnage_dome,
    status_dome,
    description,
    cek_duplicated,
    created_at,
    updated_at,
    dome_id,
    user_id
)
SELECT
    s.id,
    -- numeric safe
    COALESCE(NULLIF(s.tonnage_dome::text, '')::numeric, 0),
    s.status_dome,
    s.description,
    s.cek_duplicated,
    COALESCE(s.created_at, now()),
    COALESCE(s.updated_at, now()),
    -- id_dome → dome_id
    NULLIF(s.id_dome::text, '')::bigint,
    -- USER SAFE
    1 AS user_id
FROM ext_kqms.status_dome s

-- ANTI DUPLICATE (BY ID)
-- WHERE NOT EXISTS (
--     SELECT 1
--     FROM kawi.geology_dome_close t
--     WHERE t.id = s.id
-- );