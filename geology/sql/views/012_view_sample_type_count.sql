CREATE OR REPLACE VIEW view_sample_type_count as
SELECT 
    ROW_NUMBER() OVER () AS id,  
    *
FROM (
SELECT 
	DISTINCT t1.sample_number,
    t1.tgl_sample,
    t2.type_sample,
    t3.sample_method,
    t4.delivery,
    t4.waybill_number,
    t4.mral_order,
    t4.roa_order,
        CASE
            WHEN t4.delivery::time without time zone < '10:00:00'::time without time zone THEN t4.tgl_deliver - '1 day'::interval
            ELSE t4.tgl_deliver::timestamp without time zone
        END AS date_production,
    t5.release_mral,
    t6.release_roa,
    t1.iup_id,
    t7.iup_code,
    t7.iup_name
   FROM geology_samples_productions t1
     LEFT JOIN master_sample_type t2 ON t2.id = t1.id_type_sample
     LEFT JOIN master_sample_methods t3 ON t3.id = t1.id_method
     LEFT JOIN geology_waybills t4 ON t1.sample_number::text = t4.sample_id::text and t4.iup_id = t1.iup_id
     LEFT JOIN lab_assay_mral t5 ON t5.sample_id::text = t1.sample_number::text and t5.iup_id = t1.iup_id
     LEFT JOIN lab_assay_roa t6 ON t6.sample_id::text = t1.sample_number::text and t6.iup_id = t1.iup_id
     LEFT JOIN master_mine_iup t7 ON t7.id = t1.iup_id
 ) sub;