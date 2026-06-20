CREATE OR REPLACE VIEW view_geology_sample_pds_na AS 
SELECT t1.id,
    t1.date_sample,
    t1.shift,
    t3.type_sample,
    t4.sample_method,
    COALESCE(t3.is_production, false) AS is_production,
    t5.name as material,
    t6.dumping_point AS sampling_area,
    t7.pile_id AS sampling_point,
    t1.batch_code,
    t1.increments,
    t1.sample_weight,
    t1.sample_number,
    t1.remark,
    t8.ni,
    t8.co,
    t8.al2o3,
    t8.cao,
    t8.cr2o3,
    t8.fe2o3,
    t8.fe,
    t8.mgo,
    t8.sio2,
        CASE
            WHEN t8.mgo = 0::double precision THEN NULL::double precision
            ELSE t8.sio2 / t8.mgo
        END AS sm,
    t8.mc,
    t1.kode_batch,
    t1.iup_id,
    t9.iup_code,
    t9.iup_name
   FROM geology_samples_productions t1
     LEFT JOIN geology_ore_productions t2 ON t1.kode_batch::text = t2.kode_batch::text
     JOIN master_sample_type t3 ON t1.id_type_sample = t3.id
     JOIN master_sample_methods t4 ON t1.id_method = t4.id
     JOIN master_materials t5 ON t1.id_material = t5.id
     JOIN master_mine_sources_point_dumping t6 ON t1.sampling_area = t6.id AND t6.iup_id = t1.iup_id
     JOIN master_mine_sources_point_dome t7 ON t1.sampling_point = t7.id AND t7.iup_id = t1.iup_id
     LEFT JOIN lab_assay_roa t8 ON t8.sample_id::text = t1.sample_number::text AND t8.iup_id = t1.iup_id
     LEFT JOIN kawi.master_mine_iup t9 ON t9.id = t1.iup_id
  WHERE t3.is_production = true
  AND t2.kode_batch IS NULL;