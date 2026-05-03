INSERT INTO kawi.sellings_barging_temporary (
    created_at,
    updated_at,
    code,
    is_deleted,
    deleted_at,
    id,
    code_lot,
    barge_code,
    date_hauling,
    time_hauling,
    shift,
    id_material,
    id_stockpile,
    id_pile,
    unit_code,
    tonnage,
    type_selling,
    code_inc,
    code_sub,
    code_sub_auto,
    id_user,
    sale_adjust,
    no_urut,
    status,
    description,
    iup_id,
    user_id
)
SELECT
    COALESCE(s.created_at, now()),
    COALESCE(s.updated_at, now()),
    --  CODE: IUP + CREATED_AT
    'IUP-001-' || TO_CHAR(s.created_at, 'YYYYMMDDHH24MISSMS'),
    false,
    NULL,
    -- UUID
    gen_random_uuid(),
    s.code_lot,
    s.barge_code,
    s.date_hauling,
    s.time_hauling,
    s.shift,
    -- FK SAFE
    NULLIF(s.id_material::text, '')::bigint,
    NULLIF(s.id_stockpile::text, '')::bigint,
    NULLIF(s.id_pile::text, '')::bigint,
    s.unit_code,
    -- NUMERIC SAFE
    COALESCE(NULLIF(s.tonnage::text, '')::numeric, 0),
    s.type_selling,
    s.code_inc,
    s.code_sub,
    s.code_sub_auto,
    --  SOURCE USER
    COALESCE(NULLIF(s.id_user::text, '')::bigint, 1),
    COALESCE(NULLIF(s.sale_adjust::text, '')::numeric, 0),
    COALESCE(NULLIF(s.no_urut::text, '')::bigint, 0),
    s.status,
    -- remarks → description
    s.remarks,
    --  IUP FIX
    1 AS iup_id,
    -- USER SAFE
    1 AS user_id
FROM ext_kqms.ore_sellings_barging_temp s
-- ANTI DUPLICATE (BY CODE)
-- WHERE NOT EXISTS (
--     SELECT 1
--     FROM kawi.sellings_barging_temporary t
--     WHERE t.code =
--         'IUP-001-' || TO_CHAR(s.created_at, 'YYYYMMDDHH24MISSMS')
-- );