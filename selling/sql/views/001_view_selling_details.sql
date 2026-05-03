
CREATE OR REPLACE VIEW view_selling_details AS
  SELECT 
        t1.id,
        t1.date_barge_in,
        t1.date_barge_out,
        t7.barge_code,
        EXTRACT(week FROM t1.date_hauling) AS minggu,
        EXTRACT(month FROM t1.date_hauling) AS bulan,
        EXTRACT(year FROM t1.date_hauling) AS tahun,
        t1.shift,
        TRIM(BOTH FROM t4.pile_id) AS dome,
        TRIM(BOTH FROM t5.dumping_point) AS stockpile,
        TRIM(BOTH FROM t2.name) AS material,
        TRIM(BOTH FROM t3.unit_code) AS unit_code,
        t1.ritase_group AS ritase,
        t1.tonnage,
        t1.ton_barge_load,
        t1.ton_barge_unload,
        t1.fill_adjust,
        TRIM(BOTH FROM t1.batch) AS batch,
        TRIM(BOTH FROM t1.code_inc) AS code_inc,
        TRIM(BOTH FROM t1.code_sub) AS code_sub,
        TRIM(BOTH FROM t1.code_batch_in) AS code_batch_in,
        TRIM(BOTH FROM t1.code_batch_ex) AS code_batch_ex,
        TRIM(BOTH FROM t1.code_batch_pulp) AS code_batch_pulp,
        TRIM(BOTH FROM t1.surv_order) AS surv_order,
        TRIM(BOTH FROM t1.code_monitoring) AS code_fix_batch,
        TRIM(BOTH FROM t1.code_lot) AS code_lot,
        TRIM(BOTH FROM t6.factory_stock) AS factory_stock,
        TRIM(BOTH FROM t1.type_selling) AS type_selling,
        t1.date_hauling,
        t1.time_hauling,
        TRIM(BOTH FROM t1.sale_adjust) AS sale_adjust,
        TRIM(BOTH FROM t1.sale_dome) AS sale_dome,
        TRIM(BOTH FROM t1.direct) AS direct,
        TRIM(BOTH FROM t1.status_barging) AS status_barging,
        t1.description,
        TRIM(BOTH FROM t1.no_input) AS no_input,
        t1.iup_id,
	      t8.iup_code,
	      t8.iup_name,
	      t1.user_id,
	      t9.username,
        t1.created_at
  FROM selling_barging t1
  LEFT JOIN master_materials t2 ON t2.id = t1.id_material
	LEFT JOIN master_units t3  ON t3.unit_vendor::text = t1.unit_code::text
	LEFT JOIN master_unit_assignments ua ON ua.unit_id = t3.id AND ua.iup_id = t1.iup_id  AND ua.active = TRUE
	LEFT JOIN master_mine_sources_point_dome t4  ON t4.id = t1.id_pile AND t4.iup_id = t1.iup_id
	LEFT JOIN master_mine_sources_point_dumping t5 ON t5.id = t4.id_dumping  AND t5.iup_id = t1.iup_id
	LEFT JOIN master_stock_factories t6 ON t6.id = t1.id_factory
	LEFT JOIN master_barge t7 ON t7.id = t1.barge_code
	LEFT JOIN master_mine_iup t8 ON t8.id = t1.iup_id
	LEFT JOIN accounts_user t9 ON t9.id = t1.user_id;