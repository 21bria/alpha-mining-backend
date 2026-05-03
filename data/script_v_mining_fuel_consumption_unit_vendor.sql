CREATE OR REPLACE VIEW kawi.v_mining_fuel_with_unit AS
SELECT
    f.created_at,
    f.updated_at,
    f.code,
    f.is_deleted,
    f.deleted_at,
    f.id,
    f."date",
    f.shift,
    f.unit AS unit_legacy,
    f.hours_metre,
    f.drivers,
    f.charging_time,
    f.volume,
    f.category,
    f."storage",
    f."operator",
    f.description,
    f.iup_id,
    f.user_id,
    mu.id AS master_unit_id,
    mu.unit_vendor,
    mu.unit_code,
    CASE
        WHEN lower(trim(f.unit)) = lower(trim(mu.unit_code)) THEN 'unit_code'
        WHEN lower(trim(f.unit)) = lower(trim(mu.unit_vendor)) THEN 'unit_vendor'
        ELSE NULL
    END AS match_by
FROM kawi.mining_fuel_consumption f
LEFT JOIN kawi.master_units mu
    ON lower(trim(f.unit)) = lower(trim(mu.unit_code))
    OR lower(trim(f.unit)) = lower(trim(mu.unit_vendor));