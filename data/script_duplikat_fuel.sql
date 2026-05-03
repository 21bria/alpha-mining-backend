SELECT
    s."date",
    s.shift,
    s.unit,
    COUNT(*) AS total_duplikat
FROM mine_units_fuel_consumption s
GROUP BY
    s."date",
    s.shift,
    s.unit
HAVING COUNT(*) > 1
ORDER BY
    s."date",
    s.shift,
    s.unit;

--- hapus duplikat
DELETE FROM mine_units_fuel_consumption
WHERE id IN (
    SELECT id FROM (
        SELECT
            id,
            ROW_NUMBER() OVER (
                PARTITION BY "date", shift, unit
                ORDER BY updated_at DESC NULLS LAST,
                         created_at DESC NULLS LAST,
                         id DESC
            ) AS rn
        FROM mine_units_fuel_consumption
    ) t
    WHERE t.rn > 1
);

-- Alternatif lebih cepat (kalau tabel besar banget)
DELETE FROM mine_units_fuel_consumption a
USING mine_units_fuel_consumption b
WHERE a.id < b.id
  AND a."date" = b."date"
  AND a.shift = b.shift
  AND a.unit = b.unit;