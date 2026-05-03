CREATE OR REPLACE VIEW view_selling_official
AS SELECT 
    t1.id,
    t1.surveyor_id,
    t2.name_surveyor,
    t1.id_factory,
    t3.factory_stock,
    t1.type_selling,
    t1.tonnage,
    t1.ni,
    t1.co,
    t1.al2o3,
    t1.cao,
    t1.cr2o3,
    t1.fe,
    t1.mgo,
    t1.sio2,
    t1.mno,
    COALESCE(t1.mc, 0::double precision) AS mc,
        CASE
            WHEN t1.mgo = 0::double precision THEN NULL::double precision
        ELSE t1.sio2 / t1.mgo
    END AS sm,
    t1.so_number,
    t1.product_code,
    t1.barge_code,
    t1.start_date,
    t1.end_date,
    t1.re_assay,
    t1.iup_id,
    t4.iup_code,
    t4.iup_name,
    t1.user_id,
    t5.username,
    t1.created_at
FROM selling_official t1
LEFT JOIN master_surveyor t2 ON t2.id = t1.surveyor_id
LEFT JOIN master_stock_factories t3 ON t3.id = t1.id_factory
LEFT JOIN master_mine_iup t4 ON t4.id = t1.iup_id
LEFT JOIN accounts_user t5 ON t5.id = t1.user_id;