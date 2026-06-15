CREATE OR REPLACE VIEW view_inventory_by_dome AS 
SELECT
    iup_id,
    TRIM(BOTH FROM iup_code) AS iup_code,
    TRIM(BOTH FROM stockpile) AS stockpile,
    TRIM(BOTH FROM pile_id) AS pile_id,
    id_pile,
    TRIM(BOTH FROM nama_material) AS nama_material,
    TRIM(BOTH FROM sale_adjust) AS sale_adjust,
    TRIM(BOTH FROM pile_status) AS pile_status,
    TRIM(BOTH FROM status_dome) AS status_dome,
    SUM(tonnage) AS total_ore,
    SUM(
        CASE
            WHEN roa_ni IS NOT NULL AND sample_number IS NOT NULL
            THEN tonnage::double precision
            ELSE 0::double precision
        END
    ) AS released,
    COALESCE(
        SUM(tonnage::double precision * roa_ni)
        / NULLIF(SUM(CASE WHEN sample_number IS NOT NULL AND roa_ni IS NOT NULL THEN tonnage::double precision ELSE 0::double precision END), 0),
        0
    ) AS ni,
    COALESCE(
        SUM(tonnage::double precision * roa_co)
        / NULLIF(SUM(CASE WHEN sample_number IS NOT NULL AND roa_co IS NOT NULL THEN tonnage::double precision ELSE 0::double precision END), 0),
        0
    ) AS co,
    COALESCE(
        SUM(tonnage::double precision * roa_al2o3)
        / NULLIF(SUM(CASE WHEN sample_number IS NOT NULL AND roa_al2o3 IS NOT NULL THEN tonnage::double precision ELSE 0::double precision END), 0),
        0
    ) AS al2o3,
    COALESCE(
        SUM(tonnage::double precision * roa_cao)
        / NULLIF(SUM(CASE WHEN sample_number IS NOT NULL AND roa_cao IS NOT NULL THEN tonnage::double precision ELSE 0::double precision END), 0),
        0
    ) AS cao,
    COALESCE(
        SUM(tonnage::double precision * roa_cr2o3)
        / NULLIF(SUM(CASE WHEN sample_number IS NOT NULL AND roa_cr2o3 IS NOT NULL THEN tonnage::double precision ELSE 0::double precision END), 0),
        0
    ) AS cr2o3,
    COALESCE(
        SUM(tonnage::double precision * roa_fe2o3)
        / NULLIF(SUM(CASE WHEN sample_number IS NOT NULL AND roa_fe2o3 IS NOT NULL THEN tonnage::double precision ELSE 0::double precision END), 0),
        0
    ) AS fe2o3,
    COALESCE(
        SUM(tonnage::double precision * roa_fe)
        / NULLIF(SUM(CASE WHEN sample_number IS NOT NULL AND roa_fe IS NOT NULL THEN tonnage::double precision ELSE 0::double precision END), 0),
        0
    ) AS fe,
    COALESCE(
        SUM(tonnage::double precision * roa_mgo)
        / NULLIF(SUM(CASE WHEN sample_number IS NOT NULL AND roa_mgo IS NOT NULL THEN tonnage::double precision ELSE 0::double precision END), 0),
        0
    ) AS mgo,
    COALESCE(
        SUM(tonnage::double precision * roa_sio2)
        / NULLIF(SUM(CASE WHEN sample_number IS NOT NULL AND roa_sio2 IS NOT NULL THEN tonnage::double precision ELSE 0::double precision END), 0),
        0
    ) AS sio2,
    COALESCE(
        SUM(tonnage::double precision * roa_mc)
        / NULLIF(SUM(CASE WHEN sample_number IS NOT NULL AND roa_mc IS NOT NULL THEN tonnage::double precision ELSE 0::double precision END), 0),
        0
    ) AS mc,
    COALESCE(
        (
            SUM(tonnage::double precision * roa_sio2)
            / NULLIF(SUM(CASE WHEN sample_number IS NOT NULL AND roa_sio2 IS NOT NULL THEN tonnage::double precision ELSE 0::double precision END), 0)
        )
        /
        NULLIF(
            (
                SUM(tonnage::double precision * roa_mgo)
                / NULLIF(SUM(CASE WHEN sample_number IS NOT NULL AND roa_mgo IS NOT NULL THEN tonnage::double precision ELSE 0::double precision END), 0)
            ),
            0
        ),
        0
    ) AS sm
FROM kawi.view_geology_ore_details_roa
WHERE direct = 'No'::text
GROUP BY
    iup_id,
    iup_code,
    stockpile,
    pile_id,
    id_pile,
    status_dome,
    pile_status,
    nama_material,
    sale_adjust;