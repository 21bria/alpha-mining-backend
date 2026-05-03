
CREATE OR REPLACE VIEW view_geology_ore_production AS 
SELECT 
    t1.id,
    t1.tgl_production,
    TRIM(BOTH FROM t1.category) AS category,
    TRIM(BOTH FROM t1.shift) AS shift,
    TRIM(BOTH FROM t3.loading_point) AS prospect_area,
    TRIM(BOTH FROM t4.name) AS mine_block,
    TRIM(BOTH FROM t1.from_rl) AS from_rl,
    TRIM(BOTH FROM t1.to_rl) AS to_rl,
    TRIM(BOTH FROM t2.name) AS nama_material,
    TRIM(BOTH FROM t1.ore_class) AS ore_class,
    t1.grade_expect AS ni_grade,
    TRIM(BOTH FROM t1.grade_control) AS grade_control,
    TRIM(BOTH FROM t1.unit_truck) AS unit_truck,
    TRIM(BOTH FROM t6.dumping_point) AS stockpile,
    TRIM(BOTH FROM t5.pile_id) AS pile_id,
    TRIM(BOTH FROM t1.batch_code) AS batch_code,
    t1.increment,
    TRIM(BOTH FROM t1.batch_status) AS batch_status,
    t1.ritase,
    t1.tonnage,
    TRIM(BOTH FROM t1.pile_status) AS pile_status,
    TRIM(BOTH FROM t1.truck_factor) AS truck_factor,
    t1.remarks,
    TRIM(BOTH FROM t1.no_production) AS no_production,
    t1.created_at,
    COALESCE(TRIM(BOTH FROM t7.sample_number), 'Unprepared'::text) AS sample_number,
    t1.direct,
    t1.iup_id,
    t8.iup_code,
    t8.iup_name,
    t1.user_id,
    t9.username
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
LEFT JOIN master_mine_iup t8 
    ON t8.id = t1.iup_id
LEFT JOIN accounts_user t9 
    ON t9.id = t1.user_id;