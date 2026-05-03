INSERT INTO master_unit_assignments (
    start_date,
    end_date,
    active,
    iup_id,
    unit_id
)
SELECT
    CURRENT_DATE AS start_date,
    NULL AS end_date,
    TRUE AS active,
    1 AS iup_id,
    u.id AS unit_id
FROM master_units u
LEFT JOIN master_unit_assignments ua
    ON ua.unit_id = u.id
    AND ua.active = TRUE
WHERE ua.unit_id IS NULL;