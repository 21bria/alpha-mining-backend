INSERT INTO kawi.mining_weather (
    created_at,
    updated_at,
    code,
    is_deleted,
    deleted_at,
    id,
    "date",
    shift,
    category,
    start_time,
    end_time,
    duration,
    description,
    iup_id,
    user_id
)
SELECT
    COALESCE(s.created_at, now()),
    COALESCE(s.updated_at, now()),
    -- CODE UNIQUE
    'WTH-' || to_char(clock_timestamp(), 'YYYYMMDDHH24MISSMS') || '-' || ROW_NUMBER() OVER (),
    false,
    NULL,
    -- UUID
    gen_random_uuid(),
    s."date",
    s.shift,
    s.category,
    s.start_time,
    s.end_time,
    -- handle numeric (kalau varchar)
    COALESCE(NULLIF(s.duration::text, '')::numeric, 0),
    -- remark → description
    s.remark,
    -- IUP FIX
    1 AS iup_id,
    -- USER FIX (tidak ada di source)
    1 AS user_id
FROM ext_kqms.mine_weather s
-- ANTI DUPLICATE TARGET
-- WHERE NOT EXISTS (
--     SELECT 1
--     FROM kawi.mining_weather t
--     WHERE t.iup_id = 1
--       AND t."date" = s."date"
--       AND t.shift = s.shift
--       AND t.start_time = s.start_time
--       AND t.end_time = s.end_time
-- );