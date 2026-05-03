INSERT INTO kawi.mining_fuel_consumption (
    created_at,
    updated_at,
    code,
    is_deleted,
    deleted_at,
    id,
    "date",
    shift,
    unit,
    hours_metre,
    drivers,
    charging_time,
    volume,
    category,
    "storage",
    "operator",
    description,
    iup_id,
    user_id
)
SELECT
    COALESCE(s.created_at, now()),
    COALESCE(s.updated_at, now()),
    -- CODE UNIQUE
    'FUEL-' || to_char(clock_timestamp(), 'YYYYMMDDHH24MISSMS') || '-' || ROW_NUMBER() OVER (),
    false,
    NULL,
    -- UUID BARU
    gen_random_uuid(),
    s."date",
    s.shift,
    s.unit,
    -- HANDLE NUMERIC (kalau varchar)
    COALESCE(NULLIF(s.hours_metre::text, '')::numeric, 0),
    s.drivers,
    s.charging_time,
    COALESCE(NULLIF(s.volume::text, '')::numeric, 0),
    s.category,
    s."storage",
    s."operator",
    -- rename remark → description
    s.remark,
    -- IUP FIX
    1 AS iup_id,
    -- USER SAFE
    1 AS user_id
FROM ext_kqms.mine_units_fuel_consumption s;