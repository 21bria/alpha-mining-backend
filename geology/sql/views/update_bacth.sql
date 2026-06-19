-- Production
UPDATE geology_ore_productions
SET
    kode_batch = CONCAT('PDS', id_material, unit_truck, id_pile, batch_code),
    truck_factor = unit_truck
WHERE direct='No';

-- Sample Production
SELECT
    t1.type,
    t2.type_sample,
    t1.id_material,
    t1.unit_truck,
    t1.sampling_point,
    t1.batch_code,
    t1.kode_batch AS kode_batch_lama,
    CONCAT('PDS', t1.id_material, t1.unit_truck, t1.sampling_point, t1.batch_code) AS kode_batch_baru
FROM geology_samples_productions AS t1
LEFT JOIN master_sample_type AS t2 ON t2.id = t1.id_type_sample
WHERE t2.is_production = true;

-- Update 
WITH updated AS (
    UPDATE geology_samples_productions AS t1
    SET
        kode_batch = CONCAT('PDS', t1.id_material, t1.unit_truck, t1.sampling_point, t1.batch_code)
    FROM master_sample_type AS t2
    WHERE t2.id = t1.id_type_sample
      AND t2.is_production = true
    RETURNING t1.id
)
SELECT COUNT(*) AS total_updated
FROM updated;