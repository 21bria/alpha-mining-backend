CREATE OR REPLACE VIEW view_selling_barging_temporary AS 
SELECT t1.id,
    t1.date_hauling,
    t1.time_hauling,
    t7.barge_code,
    EXTRACT(week FROM t1.date_hauling) AS minggu,
    EXTRACT(month FROM t1.date_hauling) AS bulan,
    EXTRACT(year FROM t1.date_hauling) AS tahun,
    t1.shift,
    TRIM(BOTH FROM t4.pile_id) AS dome,
    TRIM(BOTH FROM t5.dumping_point) AS stockpile,
    TRIM(BOTH FROM t2.name) AS material,
    TRIM(BOTH FROM t1.unit_code) AS unit_code,
    t1.tonnage,
    TRIM(BOTH FROM t6.code) AS code_lot,
    TRIM(BOTH FROM t1.code_inc) AS code_inc,
    TRIM(BOTH FROM t1.code_sub) AS code_sub,
    TRIM(BOTH FROM t1.type_selling) AS type_selling,
    TRIM(BOTH FROM t1.sale_adjust) AS sale_adjust,
    t1.no_urut,
    t1.description,
    t1.status,
    t1.iup_id,
    t8.iup_code,
    t8.iup_name,
    t1.user_id,
    t9.username,
    t1.created_at
   FROM sellings_barging_temporary t1
     LEFT JOIN master_materials t2 ON t2.id = t1.id_material
     LEFT JOIN master_units t3 ON t3.unit_vendor::text = t1.unit_code::text
     LEFT JOIN master_unit_assignments ua ON ua.unit_id = t3.id AND ua.iup_id = t1.iup_id AND ua.active = true
     LEFT JOIN master_mine_sources_point_dome t4 ON t4.id = t1.id_pile AND t4.iup_id = t1.iup_id
     LEFT JOIN master_mine_sources_point_dumping t5 ON t5.id = t4.id_dumping AND t5.iup_id = t1.iup_id
     LEFT JOIN master_selling_code t6 ON t6.id = t1.code_lot
     LEFT JOIN master_barge t7 ON t7.id = t1.barge_code
     LEFT JOIN master_mine_iup t8 ON t8.id = t1.iup_id
     LEFT JOIN accounts_user t9 ON t9.id = t1.user_id;