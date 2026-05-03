CREATE OR REPLACE VIEW view_mining_fuel_hauler_ore
AS 
WITH fuel_hauler AS (
       SELECT 
       		mf.iup_id,
       		mf.date,
           TRIM(BOTH FROM mf.unit) AS hauler,
           SUM(mf.volume) AS total_fuel
        FROM mining_fuel_consumption as mf
        WHERE mf.unit::text ~~ 'E-%'::text
        GROUP BY mf.iup_id,mf.date, (TRIM(BOTH FROM mf.unit))
        ), 
        prod_hauler AS (
         SELECT
            mp.iup_id,
         	mp.date_production,
            TRIM(BOTH FROM mp.hauler) AS hauler,
            SUM(mp.tonnage) AS total_tonnage,
            0 AS total_hauler,
            sum(mp.bcm) AS total_bcm
          FROM mining_productions as mp
          LEFT JOIN master_materials as m ON m.id = mp.id_material
          WHERE m.name::text = ANY (ARRAY['LIM'::character varying::text, 'SAP'::character varying::text])
          GROUP BY mp.iup_id,mp.date_production, (TRIM(BOTH FROM mp.hauler))
        )
 SELECT 
 	p.date_production,
    p.hauler,
    p.iup_id,
    p.total_tonnage,
    p.total_bcm,
    COALESCE(f.total_fuel, 0::double precision) AS total_fuel_hauler,
    ROUND(COALESCE(f.total_fuel, 0::double precision)::numeric / NULLIF(p.total_tonnage, 0::double precision)::numeric, 3) AS fuel_ratio_per_ton,
    p.total_hauler
   FROM prod_hauler p
   LEFT JOIN fuel_hauler f ON f.date = p.date_production AND f.hauler = p.hauler and f.iup_id=p.iup_id
  ORDER BY p.date_production, p.hauler;
