CREATE OR REPLACE VIEW view_geology_samples AS 
SELECT 
    t1.id,
    t1.tgl_sample AS date_sample,
    EXTRACT(week FROM t1.tgl_sample) AS week,
    EXTRACT(month FROM t1.tgl_sample) AS month,
    EXTRACT(year FROM t1.tgl_sample) AS year,
    TRIM(BOTH FROM t1.shift) AS shift,
    TRIM(BOTH FROM t2.type_sample) AS type_sample,
    TRIM(BOTH FROM t2.category) AS category,
    TRIM(BOTH FROM t3.sample_method) AS sample_method,
    TRIM(BOTH FROM t4.name) AS material,
    concat(COALESCE(TRIM(BOTH FROM t5.dumping_point), ''::text), COALESCE(TRIM(BOTH FROM t7.factory_stock), ''::text)) AS sampling_area,
    concat(COALESCE(TRIM(BOTH FROM t6.pile_id), ''::text), COALESCE(TRIM(BOTH FROM t8.code), ''::text)) AS sampling_point,
    TRIM(BOTH FROM t5.dumping_point) AS area_sampling,
    TRIM(BOTH FROM t7.factory_stock) AS factory_stock,
    TRIM(BOTH FROM t6.pile_id) AS point_sampling,
    TRIM(BOTH FROM t8.code) AS selling_code,
    TRIM(BOTH FROM t1.batch_code) AS batch,
    t1.increments,
    t1.size,
    t1.sample_weight,
    TRIM(BOTH FROM t1.sample_number) AS sample_id,
    t1.remark,
    t1.primer_raw,
    t1.duplicate_raw,
    TRIM(BOTH FROM t1.sampling_deskripsi) AS sampling_desc,
    TRIM(BOTH FROM t1.kode_batch) AS code_batch,
    t1.no_sample,
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
     LEFT JOIN master_mine_sources_point_dumping t5 ON t1.sampling_area = t5.id AND t5.iup_id = t1.iup_id
     LEFT JOIN master_mine_sources_point_dome t6 ON t1.sampling_point = t6.id AND t6.iup_id = t1.iup_id
     LEFT JOIN master_stock_factories t7 ON t7.id = t1.discharge_area
     LEFT JOIN master_selling_code t8 ON t8.id = t1.product_code AND t8.iup_id = t1.iup_id
     LEFT JOIN master_mine_iup t9 ON t9.id = t1.iup_id
     LEFT JOIN accounts_user t10 ON t10.id = t1.user_id;