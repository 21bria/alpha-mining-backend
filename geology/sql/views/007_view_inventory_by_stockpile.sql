CREATE OR REPLACE VIEW view_inventory_by_stockpile AS 
SELECT 
	iup_id,
	TRIM(BOTH FROM iup_code) AS iup_code,
	TRIM(BOTH FROM stockpile) AS stockpile,
    TRIM(BOTH FROM nama_material) AS nama_material,
    TRIM(BOTH FROM sale_adjust) AS sale_adjust,
    TRIM(BOTH FROM status_dome) AS status_dome,
    sum(tonnage) AS total_ore,
    sum(
        CASE
            WHEN roa_ni IS NOT NULL AND sample_number IS NOT NULL THEN tonnage
            ELSE 0::double precision
        END) AS released,
    COALESCE(to_char(sum(tonnage * roa_ni) / NULLIF(sum(
        CASE
            WHEN sample_number IS NOT NULL AND roa_ni IS NOT NULL THEN tonnage
            ELSE 0::double precision
        END), 0::double precision), 'FM999999990.00'::text), '0'::text) AS ni,
    COALESCE(to_char(sum(tonnage * roa_co) / NULLIF(sum(
        CASE
            WHEN sample_number IS NOT NULL AND roa_co IS NOT NULL THEN tonnage
            ELSE 0::double precision
        END), 0::double precision), 'FM999999990.00'::text), '0'::text) AS co,
    COALESCE(to_char(sum(tonnage * roa_al2o3) / NULLIF(sum(
        CASE
            WHEN sample_number IS NOT NULL AND roa_al2o3 IS NOT NULL THEN tonnage
            ELSE 0::double precision
        END), 0::double precision), 'FM999999990.00'::text), '0'::text) AS al2o3,
    COALESCE(to_char(sum(tonnage * roa_cao) / NULLIF(sum(
        CASE
            WHEN sample_number IS NOT NULL AND roa_cao IS NOT NULL THEN tonnage
            ELSE 0::double precision
        END), 0::double precision), 'FM999999990.00'::text), '0'::text) AS cao,
    COALESCE(to_char(sum(tonnage * roa_cr2o3) / NULLIF(sum(
        CASE
            WHEN sample_number IS NOT NULL AND roa_cr2o3 IS NOT NULL THEN tonnage
            ELSE 0::double precision
        END), 0::double precision), 'FM999999990.00'::text), '0'::text) AS cr2o3,
    COALESCE(to_char(sum(tonnage * roa_fe2o3) / NULLIF(sum(
        CASE
            WHEN sample_number IS NOT NULL AND roa_fe2o3 IS NOT NULL THEN tonnage
            ELSE 0::double precision
        END), 0::double precision), 'FM999999990.00'::text), '0'::text) AS fe2o3,
    COALESCE(to_char(sum(tonnage * roa_fe) / NULLIF(sum(
        CASE
            WHEN sample_number IS NOT NULL AND roa_fe IS NOT NULL THEN tonnage
            ELSE 0::double precision
        END), 0::double precision), 'FM999999990.00'::text), '0'::text) AS fe,
    COALESCE(to_char(sum(tonnage * roa_mgo) / NULLIF(sum(
        CASE
            WHEN sample_number IS NOT NULL AND roa_mgo IS NOT NULL THEN tonnage
            ELSE 0::double precision
        END), 0::double precision), 'FM999999990.00'::text), '0'::text) AS mgo,
    COALESCE(to_char(sum(tonnage * roa_sio2) / NULLIF(sum(
        CASE
            WHEN sample_number IS NOT NULL AND roa_sio2 IS NOT NULL THEN tonnage
            ELSE 0::double precision
        END), 0::double precision), 'FM999999990.00'::text), '0'::text) AS sio2,
    COALESCE(to_char(sum(tonnage * roa_mc) / NULLIF(sum(
        CASE
            WHEN sample_number IS NOT NULL AND roa_mc IS NOT NULL THEN tonnage
            ELSE 0::double precision
        END), 0::double precision), 'FM999999990.00'::text), '0'::text) AS mc,
    to_char(COALESCE(sum(tonnage * roa_sio2) / NULLIF(sum(
        CASE
            WHEN sample_number IS NOT NULL AND roa_ni IS NOT NULL AND roa_mgo <> 0::double precision THEN tonnage
            ELSE 0::double precision
        END), 0::double precision), 0::double precision) / (COALESCE(sum(tonnage * roa_mgo) / NULLIF(sum(
        CASE
            WHEN sample_number IS NOT NULL AND roa_ni IS NOT NULL THEN tonnage
            ELSE 0::double precision
        END), 0::double precision), 0::double precision) + 0.000001::double precision), 'FM999999990.00'::text) AS sm
   FROM view_geology_ore_details_roa
  WHERE direct = 'No'::text
  GROUP BY iup_id,iup_code,stockpile, status_dome, nama_material, sale_adjust;