CREATE OR REPLACE VIEW view_geology_waybills AS
    SELECT 
        t1.id,
        t1.tgl_deliver,
        t1.delivery_time,
        TRIM(BOTH FROM t1.waybill_number) AS waybill_number,
        t1.qty,
        TRIM(BOTH FROM t1.sample_id) AS sample_id,
        CASE 
            WHEN t2.sample_number IS NOT NULL THEN 'ready'
            ELSE 'not ready'
        END AS sample_status,
        TRIM(BOTH FROM t1.mral_order) AS mral_order,
        TRIM(BOTH FROM t1.roa_order) AS roa_order,
        t1.remarks,
        t1.iup_id,
        t3.iup_code,
        t3.iup_name,
        t1.user_id,
        t4.username
    FROM geology_waybills AS t1
    LEFT JOIN geology_samples_productions t2
        ON t2.sample_number::text = t1.sample_id::text
        AND t2.iup_id = t1.iup_id
    LEFT JOIN master_mine_iup AS t3 
        ON t3.id = t1.iup_id   
    LEFT JOIN accounts_user AS t4 
        ON t4.id = t1.user_id;