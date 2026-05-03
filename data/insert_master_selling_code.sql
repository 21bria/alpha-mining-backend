INSERT INTO kawi.master_selling_code (
    id,
    created_at,
    updated_at,
    is_deleted,
    deleted_at,
    code,
    description,
    "type",
    active,
    truck_factors,
    sublot_close,
    group_close,
    ritase_max,
    tonnage,
    ni,
    fe,
    al2o3,
    co,
    mgo,
    sio2,
    cao,
    mno,
    cr2o3,
    sm,
    mc,
    iup_id,
    user_id
)
SELECT
    s.id,
    COALESCE(s.created_at, now()),
    COALESCE(s.updated_at, now()),
    false,
    NULL,
    -- CODE dari product_code
    COALESCE(NULLIF(s.product_code, ''), 'UNKNOWN'),
    s.description,
    s."type",
    -- ACTIVE INT SAFE
    COALESCE(NULLIF(s.active::text, '')::integer, 1),
    -- NUMERIC SAFE
    COALESCE(NULLIF(s.truck_factors::text, '')::numeric, 0),
    COALESCE(NULLIF(s.sublot_close::text, ''),''),
    COALESCE(NULLIF(s.group_close::text, '')::integer, 0),
    COALESCE(NULLIF(s.ritase_max::text, '')::numeric, 0),
    COALESCE(NULLIF(s.tonnage::text, '')::numeric, 0),
    COALESCE(NULLIF(s.ni::text, '')::numeric, 0),
    COALESCE(NULLIF(s.fe::text, '')::numeric, 0),
    COALESCE(NULLIF(s.al2o3::text, '')::numeric, 0),
    COALESCE(NULLIF(s.co::text, '')::numeric, 0),
    COALESCE(NULLIF(s.mgo::text, '')::numeric, 0),
    COALESCE(NULLIF(s.sio2::text, '')::numeric, 0),
    COALESCE(NULLIF(s.cao::text, '')::numeric, 0),
    COALESCE(NULLIF(s.mno::text, '')::numeric, 0),
    COALESCE(NULLIF(s.cr2o3::text, '')::numeric, 0),
    COALESCE(NULLIF(s.sm::text, '')::numeric, 0),
    COALESCE(NULLIF(s.mc::text, '')::numeric, 0),
    -- IUP FIX
    1 AS iup_id,
    -- USER DEFAULT
    1 AS user_id
FROM ext_kqms.ore_selling_code_product s

-- ANTI DUPLICATE BY CODE (LEBIH LOGIS DARI ID)
-- WHERE NOT EXISTS (
--     SELECT 1
--     FROM kawi.master_selling_code t
--     WHERE t.code = COALESCE(NULLIF(s.product_code, ''), 'UNKNOWN')
-- );