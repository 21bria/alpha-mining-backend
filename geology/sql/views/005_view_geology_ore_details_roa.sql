CREATE OR REPLACE VIEW view_geology_ore_details_roa AS 
SELECT 
    DISTINCT COALESCE(TRIM(BOTH FROM t7.sample_number), 'Unprepared'::text) AS sample_number,
    t1.id,
    t1.tgl_production,
    t1.shift,
    TRIM(BOTH FROM t1.category) AS category,
    TRIM(BOTH FROM t3.loading_point) AS prospect_area,
    TRIM(BOTH FROM t4.name) AS mine_block,
    TRIM(BOTH FROM t1.from_rl) AS from_rl,
    TRIM(BOTH FROM t1.to_rl) AS to_rl,
    TRIM(BOTH FROM t2.name) AS nama_material,
    t1.grade_expect AS ni_grade,
    TRIM(BOTH FROM t1.grade_control) AS grade_control,
    TRIM(BOTH FROM t1.unit_truck) AS unit_truck,
    TRIM(BOTH FROM t6.dumping_point) AS stockpile,
    TRIM(BOTH FROM t5.pile_id) AS pile_id,
    t1.id_pile,
    COALESCE(t5.plan_ni_min, 0::double precision) AS plan_ni_min,
    COALESCE(t5.plan_ni_max, 0::double precision) AS plan_ni_max,
    TRIM(BOTH FROM t1.batch_code) AS batch_code,
    t1.increment,
    TRIM(BOTH FROM t1.batch_status) AS batch_status,
    t1.ritase,
    t1.tonnage,
    CASE
        WHEN t8.mc = 0::double precision THEN NULL::double precision
        ELSE t1.tonnage * (1::double precision - t8.mc / 100::double precision)
    END AS tonnage_dry,
    t1.pile_status,
    t1.remarks,
    t8.ni - 0.05::double precision AS roa_ni,
    t8.co AS roa_co,
    t8.al2o3 AS roa_al2o3,
    t8.cao AS roa_cao,
    t8.cr2o3 AS roa_cr2o3,
    t8.fe2o3 AS roa_fe2o3,
    t8.fe AS roa_fe,
    t8.mgo AS roa_mgo,
    t8.sio2 AS roa_sio2,
    CASE
        WHEN t8.mgo = 0::double precision THEN NULL::double precision
        ELSE t8.sio2 / t8.mgo
    END AS roa_sm,
    t8.mc AS roa_mc,
    TRIM(BOTH FROM t1.ore_class) AS ore_class,
    TRIM(BOTH FROM t1.status_dome) AS status_dome,
    TRIM(BOTH FROM t1.sale_adjust) AS sale_adjust,
    TRIM(BOTH FROM t5.direct_sale) AS direct,
    t1.iup_id,
    t9.iup_code,
    t9.iup_name,
    t1.user_id,
    t10.username
FROM geology_ore_productions t1
JOIN master_materials t2 
    ON t2.id = t1.id_material
LEFT JOIN master_mine_sources_point_loading t3 
    ON t3.id = t1.id_prospect_area
   AND t3.iup_id = t1.iup_id
LEFT JOIN master_blocks t4 
    ON t4.id = t1.id_block
   AND t4.iup_id = t1.iup_id
LEFT JOIN master_mine_sources_point_dome t5 
    ON t5.id = t1.id_pile
   AND t5.iup_id = t1.iup_id
LEFT JOIN master_mine_sources_point_dumping t6 
    ON t6.id = t5.id_dumping
   AND t6.iup_id = t1.iup_id
LEFT JOIN geology_samples_productions t7 
    ON t7.kode_batch::text = t1.kode_batch::text
   AND t7.iup_id = t1.iup_id
LEFT JOIN lab_assay_roa t8 
    ON t7.sample_number::text = t8.sample_id::text
   AND t8.iup_id = t1.iup_id
LEFT JOIN master_mine_iup t9 
    ON t9.id = t1.iup_id
LEFT JOIN accounts_user t10 
    ON t10.id = t1.user_id;