
CREATE OR REPLACE VIEW view_laboratory_performance_tat AS 
SELECT 
    DISTINCT t1.sample_number,
    t1.tgl_sample,
    t2.type_sample,
    t3.sample_method,
    CASE
        WHEN t2.type_sample::text = 'CKS'::text
             AND (
                 t3.sample_method::text = ANY (
                     ARRAY[
                         'BS'::character varying::text,
                         'CS'::character varying::text,
                         'FS'::character varying::text,
                         'GRB'::character varying::text,
                         'TP'::character varying::text,
                         'BS_DT'::character varying::text,
                         'BS_ADT'::character varying::text
                     ]
                 )
             )
        THEN 'GC_CKS'::text

        WHEN t2.type_sample::text = 'SPC'::text
             AND t3.sample_method::text = 'SPC_GC'::text
        THEN 'GC_SPC'::text

        WHEN t2.type_sample::text = 'PDS'::text
             AND (
                 t3.sample_method::text = ANY (
                     ARRAY[
                         'BS_DT'::character varying::text,
                         'BS_ADT'::character varying::text,
                         'TS_DT'::character varying::text,
                         'TS_ADT'::character varying::text,
                         'GRB_DT'::character varying::text,
                         'GRB_ADT'::character varying::text,
                         'GRB_DT20'::character varying::text,
                         'GRB_DT30'::character varying::text,
                         'TS_DT20'::character varying::text,
                         'TS_DT30'::character varying::text
                     ]
                 )
             )
        THEN 'QA_PDS'::text
        WHEN t2.type_sample::text = 'QAQC'::text
             AND (
                 t3.sample_method::text = ANY (
                     ARRAY[
                         'CRM'::character varying::text,
                         'DUP_PDS'::character varying::text
                     ]
                 )
             )
        THEN 'QAQC'::text
        WHEN t2.type_sample::text = 'SPC'::text
             AND t3.sample_method::text = 'SPC_QA'::text
        THEN 'QA_SPC'::text
        WHEN t2.type_sample::text = 'GCDQAQC'::text
             AND (
                 t3.sample_method::text = ANY (
                     ARRAY[
                         'DUP_GCD'::character varying::text,
                         'GCDCRM'::character varying::text
                     ]
                 )
             )
        THEN 'GCD_QAQC'::text
        WHEN t2.type_sample::text = 'GCD'::text
             AND t3.sample_method::text = 'CORE'::text
        THEN 'GCD'::text
        WHEN t2.type_sample::text IN ('LIS', 'CKS_LIS') THEN 'LIS'::text
        WHEN t2.type_sample::text IN ('SAS', 'CKS_SAS') THEN 'SAS'::text
        ELSE 'no relation'::text
    END AS section,
    t4.delivery,
    t4.waybill_number,
    t4.mral_order,
    t4.roa_order,
    t5.job_number AS job_mral,
    t5.release_mral,
    to_char(
        '00:00:01'::interval * EXTRACT(epoch FROM t5.release_mral - t4.delivery)::double precision,
        'HH24:MI:SS'::text
    ) AS tat_mral,
    CASE
        WHEN (EXTRACT(epoch FROM t5.release_mral - t4.delivery) / 60::numeric) > 180::numeric
        THEN 'Late'::text
        ELSE 'OnTime'::text
    END AS mral_remark,
    t6.job_number AS job_roa,
    t6.release_roa,
    to_char(
        '00:00:01'::interval * EXTRACT(epoch FROM t6.release_roa - t4.delivery)::double precision,
        'HH24:MI:SS'::text
    ) AS tat_roa,
    t6.release_roa::date - t4.delivery::date AS tat_day,
    CASE
        WHEN (EXTRACT(epoch FROM t6.release_roa - t4.delivery) / 60::numeric) > 7200::numeric
        THEN 'Late'::text
        ELSE 'OnTime'::text
    END AS roa_remark,
    CASE
        WHEN t4.delivery::time without time zone < '10:00:00'::time without time zone
        THEN t4.tgl_deliver - '1 day'::interval
        ELSE t4.tgl_deliver::timestamp without time zone
    END AS tgl_produksi,
    t1.iup_id,
    t7.iup_code,
    t7.iup_name
FROM geology_samples_productions t1
LEFT JOIN master_sample_type t2
    ON t2.id = t1.id_type_sample
LEFT JOIN master_sample_methods t3
    ON t3.id = t1.id_method
LEFT JOIN geology_waybills t4
    ON t1.sample_number::text = t4.sample_id::text
   AND t4.iup_id = t1.iup_id
LEFT JOIN lab_assay_mral t5
    ON t5.sample_id::text = t1.sample_number::text
   AND t5.iup_id = t1.iup_id
LEFT JOIN lab_assay_roa t6
    ON t6.sample_id::text = t1.sample_number::text
   AND t6.iup_id = t1.iup_id
LEFT JOIN master_mine_iup t7
    ON t7.id = t1.iup_id;