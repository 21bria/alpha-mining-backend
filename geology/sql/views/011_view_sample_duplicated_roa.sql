CREATE OR REPLACE VIEW view_sample_duplicated_roa AS
SELECT 
    ROW_NUMBER() OVER () AS id,  
    *
FROM (
SELECT DISTINCT 
	t1.sample_number,
    t3.sample_method,
    roa.release_date,
    t1.sampling_deskripsi,
    t4.name as material,
    round(roa.ni::numeric, 3) AS ni,
    round(roa.co::numeric, 3) AS co,
    round(roa.fe::numeric, 3) AS fe,
    round(roa.mgo::numeric, 3) AS mgo,
    round(roa.sio2::numeric, 3) AS sio2,
    t1.sample_dup AS sample_original,
    round(roa_ori.ni::numeric, 3) AS ni_ori,
    round(roa_ori.co::numeric, 3) AS co_ori,
    round(roa_ori.fe::numeric, 3) AS fe_ori,
    round(roa_ori.mgo::numeric, 3) AS mgo_ori,
    round(roa_ori.sio2::numeric, 3) AS sio2_ori,
    round((roa_ori.ni - roa.ni)::numeric, 3) AS ni_diff,
    round((roa_ori.co - roa.co)::numeric, 3) AS co_diff,
    round((roa_ori.fe - roa.fe)::numeric, 3) AS fe_diff,
    round((roa_ori.mgo - roa.mgo)::numeric, 3) AS mgo_diff,
    round((roa_ori.sio2 - roa.sio2)::numeric, 3) AS sio2_diff,
        CASE
            WHEN ((roa_ori.ni + roa.ni) / 2::double precision) <> 0::double precision THEN round(((roa_ori.ni - roa.ni) / ((roa_ori.ni + roa.ni) / 2::double precision))::numeric * 100::numeric, 3)
            ELSE 0::numeric
        END AS ni_rel_diff,
        CASE
            WHEN ((roa_ori.ni + roa.ni) / 2::double precision) <> 0::double precision THEN abs(round(((roa_ori.ni - roa.ni) / ((roa_ori.ni + roa.ni) / 2::double precision) * 100::double precision)::numeric / 100::numeric, 3))
            ELSE 0::numeric
        END AS ni_rel_abs,
        CASE
            WHEN ((roa_ori.ni + roa.ni) / 2::double precision) <> 0::double precision THEN
            CASE
                WHEN abs(round(((roa_ori.ni - roa.ni) / ((roa_ori.ni + roa.ni) / 2::double precision) * 100::double precision)::numeric / 100::numeric, 3)) > 0.2 THEN '0'::text
                ELSE '1'::text
            END
            ELSE '1'::text
        END AS ni_error,
        CASE
            WHEN ((roa_ori.co + roa.co) / 2::double precision) <> 0::double precision THEN round(((roa_ori.co - roa.co) / ((roa_ori.co + roa.co) / 2::double precision))::numeric * 100::numeric, 3)
            ELSE 0::numeric
        END AS co_rel_diff,
        CASE
            WHEN ((roa_ori.co + roa.co) / 2::double precision) <> 0::double precision THEN abs(round(((roa_ori.co - roa.co) / ((roa_ori.co + roa.co) / 2::double precision) * 100::double precision)::numeric / 100::numeric, 3))
            ELSE 0::numeric
        END AS co_rel_abs,
        CASE
            WHEN ((roa_ori.co + roa.co) / 2::double precision) <> 0::double precision THEN
            CASE
                WHEN abs(round(((roa_ori.co - roa.co) / ((roa_ori.co + roa.co) / 2::double precision) * 100::double precision)::numeric / 100::numeric, 3)) > 0.2 THEN '0'::text
                ELSE '1'::text
            END
            ELSE '1'::text
        END AS co_error,
        CASE
            WHEN ((roa_ori.fe + roa.fe) / 2::double precision) <> 0::double precision THEN round(((roa_ori.fe - roa.fe) / ((roa_ori.fe + roa.fe) / 2::double precision))::numeric * 100::numeric, 3)
            ELSE 0::numeric
        END AS fe_rel_diff,
        CASE
            WHEN ((roa_ori.fe + roa.fe) / 2::double precision) <> 0::double precision THEN abs(round(((roa_ori.fe - roa.fe) / ((roa_ori.fe + roa.fe) / 2::double precision) * 100::double precision)::numeric / 100::numeric, 3))
            ELSE 0::numeric
        END AS fe_rel_abs,
        CASE
            WHEN ((roa_ori.fe + roa.fe) / 2::double precision) <> 0::double precision THEN
            CASE
                WHEN abs(round(((roa_ori.fe - roa.fe) / ((roa_ori.fe + roa.fe) / 2::double precision) * 100::double precision)::numeric / 100::numeric, 3)) > 0.2 THEN '0'::text
                ELSE '1'::text
            END
            ELSE '1'::text
        END AS fe_error,
        CASE
            WHEN ((roa_ori.mgo + roa.mgo) / 2::double precision) <> 0::double precision THEN round(((roa_ori.mgo - roa.mgo) / ((roa_ori.mgo + roa.mgo) / 2::double precision))::numeric * 100::numeric, 3)
            ELSE 0::numeric
        END AS mgo_rel_diff,
        CASE
            WHEN ((roa_ori.mgo + roa.mgo) / 2::double precision) <> 0::double precision THEN abs(round(((roa_ori.mgo - roa.mgo) / ((roa_ori.mgo + roa.mgo) / 2::double precision) * 100::double precision)::numeric / 100::numeric, 3))
            ELSE 0::numeric
        END AS mgo_rel_abs,
        CASE
            WHEN ((roa_ori.mgo + roa.mgo) / 2::double precision) <> 0::double precision THEN
            CASE
                WHEN abs(round(((roa_ori.mgo - roa.mgo) / ((roa_ori.mgo + roa.mgo) / 2::double precision) * 100::double precision)::numeric / 100::numeric, 3)) > 0.2 THEN '0'::text
                ELSE '1'::text
            END
            ELSE '1'::text
        END AS mgo_error,
        CASE
            WHEN ((roa_ori.sio2 + roa.sio2) / 2::double precision) <> 0::double precision THEN round(((roa_ori.sio2 - roa.sio2) / ((roa_ori.sio2 + roa.sio2) / 2::double precision))::numeric * 100::numeric, 3)
            ELSE 0::numeric
        END AS sio2_rel_diff,
        CASE
            WHEN ((roa_ori.sio2 + roa.sio2) / 2::double precision) <> 0::double precision THEN abs(round(((roa_ori.sio2 - roa.sio2) / ((roa_ori.sio2 + roa.sio2) / 2::double precision) * 100::double precision)::numeric / 100::numeric, 3))
            ELSE 0::numeric
        END AS sio2_rel_abs,
        CASE
            WHEN ((roa_ori.sio2 + roa.sio2) / 2::double precision) <> 0::double precision THEN
            CASE
                WHEN abs(round(((roa_ori.sio2 - roa.sio2) / ((roa_ori.sio2 + roa.sio2) / 2::double precision) * 100::double precision)::numeric / 100::numeric, 3)) > 0.2 THEN '0'::text
                ELSE '1'::text
            END
            ELSE '1'::text
        END AS sio2_error,
    t1.iup_id,
    t5.iup_code,
    t5.iup_name
   FROM geology_samples_productions t1
     LEFT JOIN master_sample_type t2 ON t2.id = t1.id_type_sample
     LEFT JOIN master_sample_methods t3 ON t3.id = t1.id_method
     LEFT JOIN master_materials t4 ON t4.id = t1.id_material
     LEFT JOIN lab_assay_roa roa ON roa.sample_id::text = t1.sample_number::text AND roa.iup_id = t1.iup_id
     LEFT JOIN lab_assay_roa roa_ori ON roa_ori.sample_id::text = t1.sample_dup::text AND roa_ori.iup_id = t1.iup_id
    LEFT JOIN master_mine_iup t5 ON t5.id = t1.iup_id
  WHERE t2.type_sample::text = 'QAQC'::text 
    AND t3.sample_method::text ~~ '%DUP%'::text 
    AND roa_ori.ni IS NOT NULL 
    AND roa.ni IS NOT NULL
) sub;