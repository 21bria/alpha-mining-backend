
CREATE OR REPLACE VIEW view_mining_loader_ore_productivity AS
WITH prod_loader AS (
    SELECT 
        mp.iup_id,
        mp.date_production,
        pl.loading_point,
        TRIM(mp.loader) AS loader,
        SUM(mp.tonnage) AS total_tonnage
    FROM mining_productions mp
    LEFT JOIN master_materials m ON m.id = mp.id_material
    LEFT JOIN master_mine_sources_point_loading pl ON pl.id = mp.loading_point
    WHERE m.name IN ('LIM', 'SAP')
    GROUP BY mp.iup_id, mp.date_production, pl.loading_point, TRIM(mp.loader)
),
hm_working AS (
    SELECT 
        h.iup_id,
        h.date,
        l.name AS location_name,
        TRIM(u.unit_code) AS loader,
        SUM(d.duration_min) / 60.0 AS working_hours
    FROM mining_hm_unit h
    JOIN mining_hm_unit_detail d ON d.hm_unit_id = h.id
    LEFT JOIN master_activity_categories c ON d.status_id = c.id
    JOIN master_units u ON u.id = h.unit_id
    LEFT JOIN master_activity_locations l ON l.id = d.location_id
    WHERE c.code = 'EWH'
    GROUP BY h.iup_id, h.date, l.name, TRIM(u.unit_code)
),
fleet_count AS (
    SELECT 
        date_production,
        iup_id,
        COUNT(DISTINCT loader) AS total_fleet
    FROM prod_loader
    GROUP BY date_production, iup_id
)
SELECT 
    p.date_production,
    p.loader,
    p.iup_id,
    p.loading_point,
    p.total_tonnage,
    COALESCE(h.working_hours, 0) AS working_hours,
    ROUND(
        (p.total_tonnage / NULLIF(h.working_hours, 0))::numeric,
        2
    ) AS productivity_ton_per_hour,
    f.total_fleet
FROM prod_loader p
LEFT JOIN hm_working h 
    ON h.date = p.date_production
    AND h.loader = p.loader
    AND h.iup_id = p.iup_id
LEFT JOIN fleet_count f
    ON f.date_production = p.date_production
    AND f.iup_id = p.iup_id
    -- AND h.location = p.loading_point
ORDER BY p.date_production, p.loader;