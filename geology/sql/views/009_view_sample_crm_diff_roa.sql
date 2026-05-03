CREATE OR REPLACE VIEW view_sample_crm_diff_roa AS
SELECT
    ROW_NUMBER() OVER (ORDER BY sample_number, iup_id) AS id,
    *
FROM (
    SELECT DISTINCT
        t2.oreas_name,
        round(t2.ni::numeric, 3) AS ni,
        round(t2.co::numeric, 3) AS co,
        round(t2.fe2o3::numeric, 3) AS fe2o3,
        round(t2.fe::numeric, 3) AS fe,
        round(t2.mgo::numeric, 3) AS mgo,
        round(t2.sio2::numeric, 3) AS sio2,
        round(t2.al2o3::numeric, 3) AS al2o3,
        t1.sample_number,
        t1.sampling_deskripsi,
        t3.sample_id,
        t3.release_date,
        round(t3.ni::numeric, 3) AS roa_ni,
        round(t3.co::numeric, 3) AS roa_co,
        round(t3.fe2o3::numeric, 3) AS roa_fe2o3,
        round(t3.fe::numeric, 3) AS roa_fe,
        round(t3.mgo::numeric, 3) AS roa_mgo,
        round(t3.sio2::numeric, 3) AS roa_sio2,
        round(t3.al2o3::numeric, 3) AS roa_al2o3,
        round(abs((t3.ni::numeric - t2.ni::numeric) / NULLIF((t3.ni::numeric + t2.ni::numeric) / 2::numeric, 0::numeric) * 100::numeric), 3) AS diff_ni,
        round(abs((t3.co::numeric - t2.co::numeric) / NULLIF((t3.co::numeric + t2.co::numeric) / 2::numeric, 0::numeric) * 100::numeric), 3) AS diff_co,
        round(abs((t3.fe2o3::numeric - t2.fe2o3::numeric) / NULLIF((t3.fe2o3::numeric + t2.fe2o3::numeric) / 2::numeric, 0::numeric) * 100::numeric), 3) AS diff_fe2o3,
        round(abs((t3.fe::numeric - t2.fe::numeric) / NULLIF((t3.fe::numeric + t2.fe::numeric) / 2::numeric, 0::numeric) * 100::numeric), 3) AS diff_fe,
        round(abs((t3.mgo::numeric - t2.mgo::numeric) / NULLIF((t3.mgo::numeric + t2.mgo::numeric) / 2::numeric, 0::numeric) * 100::numeric), 3) AS diff_mgo,
        round(abs((t3.sio2::numeric - t2.sio2::numeric) / NULLIF((t3.sio2::numeric + t2.sio2::numeric) / 2::numeric, 0::numeric) * 100::numeric), 3) AS diff_sio2,
        round(abs((t3.al2o3::numeric - t2.al2o3::numeric) / NULLIF((t3.al2o3::numeric + t2.al2o3::numeric) / 2::numeric, 0::numeric) * 100::numeric), 3) AS diff_al2o3,
        t1.iup_id,
        t5.iup_code,
        t5.iup_name
    FROM geology_samples_productions t1
    JOIN geology_sample_crm_certified t2
      ON t2.oreas_name::text = t1.sampling_deskripsi::text
    JOIN lab_assay_roa t3
      ON t3.sample_id::text = t1.sample_number::text
     AND t3.iup_id = t1.iup_id
    LEFT JOIN master_sample_type t4
      ON t4.id = t1.id_type_sample
    LEFT JOIN master_mine_iup t5
      ON t5.id = t1.iup_id
    WHERE t4.type_sample = 'QAQC'
) sub;