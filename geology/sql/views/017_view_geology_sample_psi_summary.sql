CREATE OR REPLACE VIEW view_geology_sample_psi_summary AS
SELECT
    iup_id,
    iup_code,
    stockpile,
    dome_inventory AS pile_id,
    id_pile,
    material_inventory AS nama_material,
    MAX(total_ore) AS inventory_total_ore,
    MAX(released) AS inventory_released,
    COUNT(sample_id) AS total_sample,
    SUM(allocated_tonnage) AS psi_allocated_tonnage,
    SUM(ni * allocated_tonnage) / NULLIF(SUM(allocated_tonnage), 0) AS ni,
    SUM(co * allocated_tonnage) / NULLIF(SUM(allocated_tonnage), 0) AS co,
    SUM(al2o3 * allocated_tonnage) / NULLIF(SUM(allocated_tonnage), 0) AS al2o3,
    SUM(cao * allocated_tonnage) / NULLIF(SUM(allocated_tonnage), 0) AS cao,
    SUM(cr2o3 * allocated_tonnage) / NULLIF(SUM(allocated_tonnage), 0) AS cr2o3,
    SUM(fe2o3 * allocated_tonnage) / NULLIF(SUM(allocated_tonnage), 0) AS fe2o3,
    SUM(fe * allocated_tonnage) / NULLIF(SUM(allocated_tonnage), 0) AS fe,
    SUM(mgo * allocated_tonnage) / NULLIF(SUM(allocated_tonnage), 0) AS mgo,
    SUM(sio2 * allocated_tonnage) / NULLIF(SUM(allocated_tonnage), 0) AS sio2,
    SUM(mc * allocated_tonnage) / NULLIF(SUM(allocated_tonnage), 0) AS mc,
    CASE
        WHEN SUM(mgo * allocated_tonnage) = 0 THEN NULL
        ELSE
            SUM(sio2 * allocated_tonnage)
            / NULLIF(SUM(mgo * allocated_tonnage), 0)
    END AS sm
FROM view_geology_sample_psi
GROUP BY
    iup_id,
    iup_code,
    stockpile,
    dome_inventory,
    id_pile,
    material_inventory;