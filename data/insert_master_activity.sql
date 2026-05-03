
INSERT INTO kawi.master_activity (
    id,
    code,
    "name",
    user_id,
    status_id
)
SELECT
    s.id,
    s.code,
    s."name",
    1 AS user_id,
    NULLIF(s.status_id::text, '')::bigint AS status_id
FROM ext_kqms.mine_unit_activity s
ON CONFLICT (id) DO UPDATE SET
    code = EXCLUDED.code,
    name = EXCLUDED.name,
    status_id = EXCLUDED.status_id,
    user_id = EXCLUDED.user_id;