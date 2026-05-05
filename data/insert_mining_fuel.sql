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
    COALESCE(x.created_at, NOW()),
    COALESCE(x.updated_at, NOW()),
    'FUEL-' || to_char(clock_timestamp(), 'YYYYMMDDHH24MISSMS') || '-' || x.rn,
    FALSE,
    NULL,
    gen_random_uuid(),
    x."date",
    x.shift,
    x.unit,
    COALESCE(NULLIF(x.hours_metre::text, '')::numeric, 0),
    x.drivers,
    x.charging_time,
    COALESCE(NULLIF(x.volume::text, '')::numeric, 0),
    x.category,
    x."storage",
    x."operator",
    x.remark,
    1 AS iup_id,
    1 AS user_id
FROM (
    SELECT DISTINCT ON (s."date", s.shift, s.unit)
        s.*,
        ROW_NUMBER() OVER () AS rn
    FROM ext_kqms.mine_units_fuel_consumption s
    WHERE s."date" IS NOT NULL
      AND s.shift IS NOT NULL
      AND s.unit IS NOT NULL
    ORDER BY s."date", s.shift, s.unit, s.updated_at DESC NULLS LAST, s.created_at DESC NULLS LAST
) x
ON CONFLICT (iup_id, "date", shift, unit) DO NOTHING;