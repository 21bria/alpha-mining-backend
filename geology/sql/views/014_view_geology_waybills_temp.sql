CREATE OR REPLACE VIEW view_waybill_temporary AS 
SELECT 
    t1.id,
    t1.sample_id,
    t2.type_sample,
    t3.sample_method,
    t4.name AS material,
    CASE 
        WHEN t2.is_production = TRUE OR t2.is_geology = TRUE
            THEN t5.dumping_point
        WHEN t2.is_selling = TRUE OR t2.is_monitoring = TRUE
            THEN t7.factory_stock
        ELSE NULL
    END AS sampling_area,

    CASE 
        WHEN t2.is_production = TRUE OR t2.is_geology = TRUE
            THEN t6.pile_id
        WHEN t2.is_selling = TRUE OR t2.is_monitoring = TRUE
            THEN t8.code
        ELSE NULL
    END AS sampling_point,
    t1.batch_code,
    t1.no_save,
    t1.status_input,
    t1.iup_id,
    t9.iup_code,
    t9.iup_name,
    t1.user_id,
    t10.username,
    t1.created_at
FROM geology_waybill_temps t1
LEFT JOIN master_sample_type t2 
    ON t1.id_type_sample = t2.id
LEFT JOIN master_sample_methods t3 
    ON t1.id_method = t3.id
LEFT JOIN master_materials t4 
    ON t1.id_material = t4.id
LEFT JOIN master_mine_sources_point_dumping t5 
    ON (t2.is_production = TRUE OR t2.is_geology = TRUE)
    AND t1.sampling_area = t5.id 
    AND t5.iup_id = t1.iup_id
LEFT JOIN master_mine_sources_point_dome t6 
    ON (t2.is_production = TRUE OR t2.is_geology = TRUE)
    AND t1.sampling_point = t6.id 
    AND t6.iup_id = t1.iup_id
LEFT JOIN master_stock_factories t7 
    ON (t2.is_selling = TRUE OR t2.is_monitoring = TRUE)
    AND t7.id = t1.sampling_area
LEFT JOIN master_selling_code t8 
    ON (t2.is_selling = TRUE OR t2.is_monitoring = TRUE)
    AND t8.id = t1.sampling_point 
    AND t8.iup_id = t1.iup_id
LEFT JOIN master_mine_iup t9 
    ON t9.id = t1.iup_id
LEFT JOIN accounts_user t10 
    ON t10.id = t1.user_id;