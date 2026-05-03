INSERT INTO kawi.mining_hm_unit (
    created_at,
    updated_at,
    code,
    is_deleted,
    deleted_at,
    id,
    "date",
    shift,
    hm_start,
    hm_end,
    status,
    iup_id,
    unit_id,
    user_id
)
SELECT
    COALESCE(s.created_at, now()),
    now(),
    'IUP-001-' ||
    COALESCE(s.unit_id::text, '0') || '-' ||
    COALESCE(TO_CHAR(s."date", 'YYYYMMDD'), '00000000') || '-' ||
    COALESCE(s.shift, 'NA'),
    false,
    NULL,
    s.id,
    s."date",
    s.shift,
    s.hm_start,
    s.hm_end,
    s.status,
    1,
    s.unit_id,
    1
FROM ext_kqms.mine_hm_unit s
WHERE NOT EXISTS (
    SELECT 1
    FROM kawi.mining_hm_unit t
    WHERE t.id = s.id
);