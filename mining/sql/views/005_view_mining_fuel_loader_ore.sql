CREATE OR REPLACE VIEW view_mining_fuel_loader_ore
AS 
WITH fuel_loader AS (
        SELECT 
       	    mf.iup_id,
       	    mf.date,
            TRIM(BOTH FROM mf.unit) AS loader,
            SUM(mf.volume) AS total_fuel
        FROM mining_fuel_consumption as mf
        WHERE mf.unit::text ~~ 'E-%'::text
        GROUP BY mf.iup_id,mf.date, (TRIM(BOTH FROM mf.unit))
        ), 
        prod_loader AS (
        SELECT
            mp.iup_id,
         	mp.date_production,
            TRIM(BOTH FROM mp.loader) AS loader,
            SUM(mp.tonnage) AS total_tonnage,
            0 AS total_loader,
            sum(mp.bcm) AS total_bcm
        FROM mining_productions as mp
        LEFT JOIN master_materials as m ON m.id = mp.id_material
        WHERE m.name::text = ANY (ARRAY['LIM'::character varying::text, 'SAP'::character varying::text])
        GROUP BY mp.iup_id,mp.date_production, (TRIM(BOTH FROM mp.loader))
        )
SELECT 
 	p.date_production,
    p.loader,
    p.iup_id,
    p.total_tonnage,
    p.total_bcm,
    COALESCE(f.total_fuel, 0::double precision) AS total_fuel_loader,
    ROUND(COALESCE(f.total_fuel, 0::double precision)::numeric / NULLIF(p.total_tonnage, 0::double precision)::numeric, 3) AS fuel_ratio_per_ton,
    p.total_loader
FROM prod_loader p
LEFT JOIN fuel_loader f ON f.date = p.date_production AND f.loader = p.loader and f.iup_id=p.iup_id
ORDER BY p.date_production, p.loader;