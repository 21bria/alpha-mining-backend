CREATE OR REPLACE VIEW view_selling_monitoring AS 
SELECT 
    t1.date_barge_in,
    t1.date_barge_out,
    t1.date_hauling,
    TRIM(BOTH FROM t1.shift) AS shift,
    TRIM(BOTH FROM t4.pile_id) AS dome,
    TRIM(BOTH FROM t5.dumping_point) AS stockpile,
    TRIM(BOTH FROM t2.name) AS material,
    TRIM(BOTH FROM t3.barge_code) AS barge_code,
    TRIM(BOTH FROM t3.barge_name) AS barge_name,
    t1.tonnage,
    TRIM(BOTH FROM t1.batch) AS batch,
    TRIM(BOTH FROM t1.code_inc) AS code_inc,
    TRIM(BOTH FROM t1.code_sub) AS code_sub,
    TRIM(BOTH FROM t1.code_monitoring) AS code_monitoring,
    TRIM(BOTH FROM t1.code_lot) AS code_lot,
    TRIM(BOTH FROM t6.factory_stock) AS factory_stock,
    TRIM(BOTH FROM t1.type_selling) AS type_selling,
    TRIM(BOTH FROM t1.sale_adjust) AS sale_adjust,
    TRIM(BOTH FROM t1.sale_dome) AS sale_dome,
    TRIM(BOTH FROM t7.sample_number) AS sample_number,
    t8.ni,
    t8.fe,
    t8.co,
    t8.mgo,
    t8.al2o3,
    t8.sio2,
    t8.cao,
    t8.cr2o3,
    t8.mno,
    t8.mc,
        CASE
            WHEN t8.mgo = 0::double precision THEN NULL::double precision
            ELSE t8.sio2 / t8.mgo
        END AS sm,
    t1.iup_id,
	t9.iup_code,
	t9.iup_name,
	t1.user_id,
	t10.username    
    FROM selling_barging t1
    LEFT JOIN master_materials t2 ON t2.id = t1.id_material
    LEFT JOIN master_barge t3 ON t3.id = t1.barge_code
    LEFT JOIN master_mine_sources_point_dome t4 ON t4.id = t1.id_pile AND t4.iup_id = t1.iup_id
    LEFT JOIN master_mine_sources_point_dumping t5 ON t5.id = t4.id_dumping AND t5.iup_id = t1.iup_id
    LEFT JOIN master_stock_factories t6 ON t6.id = t1.id_factory
    LEFT JOIN geology_samples_productions t7 ON t7.sale_monitoring::text = t1.code_monitoring::text AND t7.iup_id = t1.iup_id
    LEFT JOIN lab_assay_roa t8 ON t8.sample_id::text = t7.sample_number::text AND t8.iup_id = t1.iup_id
    LEFT JOIN master_mine_iup t9 ON t9.id = t1.iup_id
    LEFT JOIN accounts_user t10 ON t10.id = t1.user_id;