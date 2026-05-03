CREATE VIEW public.v_mine_hm_unit_migration AS
SELECT
    created_at,
    now() AS updated_at,
    'IUP-001-' ||
    COALESCE(unit_id::text, '0') || '-' ||
    COALESCE(TO_CHAR("date", 'YYYYMMDD'), '00000000') || '-' ||
    COALESCE(shift, 'NA') AS code,
    false AS is_deleted,
    NULL::timestamp AS deleted_at,
    id,
    "date",
    shift,
    hm_start,
    hm_end,
    status,
    1 AS iup_id,
    unit_id,
    1 AS user_id
FROM public.mine_hm_unit;