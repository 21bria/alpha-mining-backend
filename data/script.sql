
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
    mine_unit_activity
)
FROM SERVER db_kqms_server
INTO ext_kqms;