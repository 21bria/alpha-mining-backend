CREATE OR REPLACE VIEW view_geology_samples_dome AS 
SELECT t1.id,
    t1.tgl_sample AS date_sample,
    TRIM(BOTH FROM t1.shift) AS shift,
    TRIM(BOTH FROM t2.type_sample) AS type_sample,
    COALESCE(t2.is_production, false) AS is_production,
    COALESCE(t2.is_geology, false) AS is_geology,
    TRIM(BOTH FROM t3.sample_method) AS sample_method,
    TRIM(BOTH FROM t4.name) AS material,
    COALESCE(TRIM(BOTH FROM t5.pile_id), ''::text) AS sampling_point,
    TRIM(BOTH FROM t1.batch_code) AS batch,
    t1.increments,
    t1.sample_weight,
    TRIM(BOTH FROM t1.sample_number) AS sample_id,
    --t1.remark,
    TRIM(BOTH FROM t1.sampling_deskripsi) AS sampling_desc,
    t6.ni AS ni,
    t6.co AS co,
    t6.al2o3 AS al2o3,
    t6.cao AS cao,
    t6.cr2o3 AS cr2o3,
    t6.fe2o3 AS fe2o3,
    t6.fe AS fe,
    t6.mgo AS mgo,
    t6.sio2 AS sio2,
        CASE
            WHEN t6.mgo = 0::double precision THEN NULL::double precision
            ELSE t6.sio2 / t6.mgo
        END AS sm,
    t6.mc AS mc,
    t1.iup_id,
    t9.iup_code,
    t9.iup_name,
    t1.user_id,
    t10.username,
    t1.created_at
   FROM geology_samples_productions t1
     LEFT JOIN master_sample_type t2 ON t1.id_type_sample = t2.id
     LEFT JOIN master_sample_methods t3 ON t1.id_method = t3.id
     LEFT JOIN master_materials t4 ON t1.id_material = t4.id
     LEFT JOIN master_mine_sources_point_dome t5 ON t1.sampling_point = t5.id AND t5.iup_id = t1.iup_id
     LEFT JOIN lab_assay_roa t6 ON t6.sample_id::text = t1.sample_number::text AND t6.iup_id = t1.iup_id
     LEFT JOIN master_mine_iup t9 ON t9.id = t1.iup_id
     LEFT JOIN accounts_user t10 ON t10.id = t1.user_id
