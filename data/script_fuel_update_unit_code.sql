SELECT
    unit,
    TRIM(
        REGEXP_REPLACE(
            REGEXP_REPLACE(unit, '^MT\s*', '', 'i'),
            '^LGP\s*', '', 'i'
        )
    ) AS unit_clean
FROM kawi.mining_fuel_consumption;

UPDATE kawi.mining_fuel_consumption
SET unit = TRIM(
    REGEXP_REPLACE(
        REGEXP_REPLACE(unit, '^MT\s*', '', 'i'),
        '^LGP\s*', '', 'i'
    )
);