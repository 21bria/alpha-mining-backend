INSERT INTO kawi.selling_barging (
    created_at,
    updated_at,
    code,
    is_deleted,
    deleted_at,
    id,
    date_barge_in,
    date_barge_out,
    barge_code,
    barging_load_loc,
    barging_unload_loc,
    date_hauling,
    time_hauling,
    shift,
    id_material,
    id_stockpile,
    id_pile,
    unit_code,
    tonnage,
    ritase_group,
    ton_barge_load,
    ton_barge_unload,
    fill_adjust,
    batch,
    id_factory,
    type_selling,
    code_inc,
    code_sub,
    code_batch_in,
    code_batch_ex,
    code_batch_pulp,
    surv_order,
    code_monitoring,
    code_lot,
    date_barging,
    sale_adjust,
    sale_dome,
    direct,
    status_barging,
    no_input,
    description,
    iup_id,
    user_id
)
SELECT
    COALESCE(s.created_at, now()),
    COALESCE(s.updated_at, now()),
    -- CODE UNIQUE
    'SL-' || to_char(clock_timestamp(), 'YYYYMMDDHH24MISSMS') || '-' || ROW_NUMBER() OVER (),
    false,
    NULL,
    -- UUID
    gen_random_uuid(),
    s.date_barge_in,
    s.date_barge_out,
    s.barge_code,
    s.barging_load_loc,
    s.barging_unload_loc,
    s.date_hauling,
    s.time_hauling,
    s.shift,
    -- FK numeric safe
    NULLIF(s.id_material::text, '')::bigint,
    NULLIF(s.id_stockpile::text, '')::bigint,
    NULLIF(s.id_pile::text, '')::bigint,
    s.unit_code,
    -- numeric safe
    COALESCE(NULLIF(s.tonnage::text, '')::numeric, 0),
    COALESCE(NULLIF(s.ritase_group::text, '')::bigint, 0),
    COALESCE(NULLIF(s.ton_barge_load::text, '')::numeric, 0),
    COALESCE(NULLIF(s.ton_barge_unload::text, '')::numeric, 0),
    COALESCE(NULLIF(s.fill_adjust::text, '')::numeric, 0),
    s.batch,
    NULLIF(s.id_factory::text, '')::bigint,
    s.type_selling,
    s.code_inc,
    s.code_sub,
    s.code_batch_in,
    s.code_batch_ex,
    s.code_batch_pulp,
    s.surv_order,
    s.code_monitoring,
    s.code_lot,
    s.date_barging,
    COALESCE(NULLIF(s.sale_adjust::text, ''),''),
    COALESCE(NULLIF(s.sale_dome::text, ''),''),
    s.direct,
    s.status_barging,
    s.no_input,
    -- remarks → description
    s.remarks,
    --  IUP FIX
    1 AS iup_id,
    -- USER SAFE
    1 AS user_id
FROM ext_kqms.ore_sellings_barging s

-- ANTI DUPLICATE TARGET
-- WHERE NOT EXISTS (
--     SELECT 1
--     FROM kawi.selling_barging t
--     WHERE t.iup_id = 1
--       AND t.code_batch_ex = s.code_batch_ex
--       AND t.barge_code = s.barge_code
--       AND t.date_barging = s.date_barging
-- );