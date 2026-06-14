CREATE OR REPLACE VIEW view_geology_sample_psi AS
SELECT
    s.iup_id,
    i.iup_code,
    s.date_sample,
    s.sample_id,
    s.type_sample,
    s.batch AS batch_code,
    s.material AS material_psi,
    i.nama_material AS material_inventory,
    s.sampling_point AS dome_psi,
    i.pile_id AS dome_inventory,
    i.id_pile,
    i.stockpile,
    i.total_ore,
    i.released,
    COUNT(*) OVER (
        PARTITION BY s.iup_id, s.sampling_point, s.material
    ) AS total_psi_sample,

    i.total_ore / NULLIF(
        COUNT(*) OVER (
            PARTITION BY s.iup_id, s.sampling_point, s.material
        ),
        0
    ) AS allocated_tonnage,
    a.ni - 0.05::double precision AS ni,
    a.co,
    a.al2o3,
    a.cao,
    a.cr2o3,
    a.fe2o3,
    a.fe,
    a.mgo,
    a.sio2,
    CASE
        WHEN a.mgo = 0::double precision THEN NULL::double precision
        ELSE a.sio2 / a.mgo
    END AS sm,
    a.mc
FROM view_geology_samples s
JOIN view_inventory_by_dome i
    ON i.iup_id = s.iup_id
   AND i.pile_id = s.sampling_point
LEFT JOIN lab_assay_roa a
    ON a.sample_id::text = s.sample_id::text
   AND a.iup_id = s.iup_id
WHERE UPPER(s.type_sample) = 'PSI';