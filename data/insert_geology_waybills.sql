INSERT INTO kawi.geology_waybills (
    created_at,
    updated_at,
    code,
    is_deleted,
    deleted_at,
    id,
    tgl_deliver,
    delivery_time,
    waybill_number,
    qty,
    sample_id,
    mral_order,
    roa_order,
    remarks,
    delivery,
    iup_id,
    user_id
)
SELECT
    COALESCE(s.created_at, now()),
    COALESCE(s.updated_at, now()),
    --  CODE: IUP + DATE + SAMPLE
    'IUP-001-' ||
    TO_CHAR(s.tgl_deliver, 'YYYYMMDD') || '-' ||
    COALESCE(NULLIF(s.sample_id, ''), 'UNKNOWN'),
    false,
    NULL,
    -- UUID
    gen_random_uuid(),
    s.tgl_deliver,
    s.delivery_time,
    s.waybill_number,
    -- numb_sample → qty
    COALESCE(NULLIF(s.numb_sample::text, '')::bigint, 0),
    s.sample_id,
    s.mral_order,
    s.roa_order,
    s.remarks,
    s.delivery,
    -- IUP FIX
    1 AS iup_id,
    --  USER SAFE
    1 AS user_id
FROM ext_kqms.waybills s

--  ANTI DUPLICATE
-- WHERE NOT EXISTS (
--     SELECT 1
--     FROM kawi.geology_waybills t
--     WHERE t.code =
--         'IUP-001-' ||
--         TO_CHAR(s.tgl_deliver, 'YYYYMMDD') || '-' ||
--         COALESCE(NULLIF(s.sample_id, ''), 'UNKNOWN')
-- );