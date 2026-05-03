INSERT INTO kawi.geology_dome_finish (
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
    COALESCE(NULLIF(s.tonnage_dome::text, '')::numeric, 0),
    s.status_dome,
    s.description,
    s.cek_duplicated,
    COALESCE(s.created_at, now()),
    COALESCE(s.updated_at, now()),
    NULLIF(s.id_dome::text, '')::bigint,
    1 AS user_id
FROM ext_kqms.status_dome_finish s
-- WHERE NOT EXISTS (
--     SELECT 1
--     FROM kawi.geology_dome_finish t
--     WHERE t.id = s.id
-- );