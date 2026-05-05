
CREATE EXTENSION IF NOT EXISTS postgres_fdw;
CREATE SERVER db_kqms_server
FOREIGN DATA WRAPPER postgres_fdw
OPTIONS (
    host '127.0.0.1',
    dbname 'db_kqms',
    port '5432'
);

CREATE USER MAPPING FOR CURRENT_USER
SERVER db_kqms_server
OPTIONS (
    user 'postgres',
    password '211989'
);

CREATE SCHEMA IF NOT EXISTS ext_kqms;

IMPORT FOREIGN SCHEMA public
LIMIT TO (
    assay_roas,
    samples_productions,
    waybills,
    productions_mines,
    plan_productions,
    mine_units_fuel_consumption,
    mine_weather,
    master_barge,
    ore_selling_code_product,
    ore_sellings_barging,
    ore_sellings_barging_temp,
    status_dome,
    status_dome_finish,
    mine_hm_unit,
    v_mine_hm_unit_migration,
    mine_hm_unit_detail,
    v_mine_unit_location_uuid,
    v_mine_hm_unit_detail_uuid,
    mine_unit_activity,
    mine_sources_point_loading,
    mine_sources_point_dome,
    mine_sources_point_dumping
)
FROM SERVER db_kqms_server
INTO ext_kqms;

-- Truncate tables before insert data from source
--ALTER SEQUENCE master_mine_sources_point_dome_id_seq RESTART WITH 229;

TRUNCATE TABLE master_mine_sources_point_loading RESTART IDENTITY CASCADE;
TRUNCATE TABLE master_mine_sources_point_dome RESTART IDENTITY CASCADE;
TRUNCATE TABLE master_mine_sources_point_dumping RESTART IDENTITY CASCADE;
TRUNCATE TABLE master_activity_locations RESTART IDENTITY CASCADE;

TRUNCATE TABLE geology_samples_productions RESTART IDENTITY CASCADE;
TRUNCATE TABLE geology_waybills RESTART IDENTITY CASCADE;
TRUNCATE TABLE lab_assay_roa RESTART IDENTITY CASCADE;
TRUNCATE TABLE geology_ore_productions RESTART IDENTITY CASCADE;

TRUNCATE TABLE geology_dome_close RESTART IDENTITY CASCADE;
TRUNCATE TABLE geology_dome_compositing RESTART IDENTITY CASCADE;
TRUNCATE TABLE geology_dome_finish RESTART IDENTITY CASCADE;


TRUNCATE TABLE master_units RESTART IDENTITY CASCADE;
TRUNCATE TABLE master_unit_assignments RESTART IDENTITY CASCADE;
TRUNCATE TABLE mining_rainfall RESTART IDENTITY CASCADE;
TRUNCATE TABLE mining_weather RESTART IDENTITY CASCADE;

TRUNCATE TABLE mining_productions RESTART IDENTITY CASCADE;
TRUNCATE TABLE mining_hm_unit_detail RESTART IDENTITY CASCADE;
TRUNCATE TABLE mining_hm_unit RESTART IDENTITY CASCADE;

TRUNCATE TABLE mining_fuel_consumption RESTART IDENTITY CASCADE;

TRUNCATE TABLE master_selling_code RESTART IDENTITY CASCADE;
TRUNCATE TABLE master_barge RESTART IDENTITY CASCADE;
TRUNCATE TABLE selling_barging RESTART IDENTITY CASCADE;
TRUNCATE TABLE selling_plan_barging RESTART IDENTITY CASCADE;

TRUNCATE TABLE import_job_row RESTART IDENTITY CASCADE;
TRUNCATE TABLE import_job RESTART IDENTITY CASCADE;

-- ============ Insert data from source to target tables ============
-- public.details_selling_monitoring source
select * from view_geology_samples
where type_sample in ('LIS_CKS','SAS_CKS')


update selling_barging 
set code_monitoring=CONCAT(type_selling,'_CKS' ,id_material,code_lot,code_sub,code_inc);

SELECT st.type_sample,msc.code,sp.id_material,sp.batch_code,sp.increments 
FROM geology_samples_productions as sp
left join master_sample_type as st on st.id =sp.id_type_sample 
left join master_selling_code msc  on msc.id =sp.product_code 
WHERE id_type_sample IN (
    SELECT id
    FROM master_sample_type
    WHERE type_sample IN ('LIS_CKS', 'SAS_CKS')
);


UPDATE geology_samples_productions sp
SET sale_monitoring = CONCAT(
    st.type_sample,
    sp.id_material,
    msc.code,
    sp.batch_code,
    sp.increments
)
FROM master_sample_type st,
     master_selling_code msc
WHERE st.id = sp.id_type_sample
  AND msc.id = sp.product_code
  AND st.type_sample IN ('LIS_CKS', 'SAS_CKS');

--SELECT *
--FROM geology_samples_productions
--WHERE DATE(created_at) = CURRENT_DATE;

--DELETE FROM geology_samples_productions
--WHERE DATE(created_at) = CURRENT_DATE;

UPDATE kawi.mining_weather 
SET category ='Rainy'
WHERE category ='Rain'


DELETE FROM mine_unit_location
WHERE ctid IN (
    SELECT ctid
    FROM (
        SELECT ctid,
               ROW_NUMBER() OVER (PARTITION BY id, code, name ORDER BY name DESC) AS rn
        FROM mine_unit_location
    ) t
    WHERE t.rn > 1
);