CREATE OR REPLACE VIEW view_mining_productions AS 
SELECT 
	t1.id,
    t1.date_production,
    TRIM(BOTH FROM t1.shift) AS shift,
    TRIM(BOTH FROM t1.vendors) AS vendors,
    TRIM(BOTH FROM t1.loader) AS loader,
    t1.bucket,
    TRIM(BOTH FROM t1.hauler) AS hauler,
    TRIM(BOTH FROM t1.hauler_class) AS hauler_class,
    TRIM(BOTH FROM t1.hauler_type) AS hauler_type,
    TRIM(BOTH FROM t2.sources_area) AS sources_area,
    TRIM(BOTH FROM t3.loading_point) AS loading_point,
    TRIM(BOTH FROM t4.dumping_point) AS dumping_point,
    TRIM(BOTH FROM t5.pile_id) AS dome_id,
    TRIM(BOTH FROM t1.category_mine) AS category_mine,
    t1.time_loading,
    t1.time_dumping,
    TRIM(BOTH FROM t1.block_id) AS mine_block,
    TRIM(BOTH FROM t1.from_rl) AS from_rl,
    TRIM(BOTH FROM t1.to_rl) AS to_rl,
    COALESCE(TRIM(BOTH FROM t1.from_rl::text || t1.to_rl::text), ''::text) AS rl,
    TRIM(BOTH FROM t6.name) AS nama_material,
    COALESCE(t6.is_ore, false) AS is_ore,
    COALESCE(t6.is_production, false) AS is_production,
    t1.ritase,
    round(t1.bcm::numeric, 2) AS bcm,
    t1.tonnage,
    t1.remarks,
    EXTRACT(hour FROM t1.time_loading) AS original_t_load,
        CASE
            WHEN t1.shift::text = 'N'::text THEN
            CASE
                WHEN EXTRACT(hour FROM t1.time_loading) >= 7::numeric AND EXTRACT(hour FROM t1.time_loading) <= 18::numeric THEN EXTRACT(hour FROM t1.time_loading) + 12::numeric
                ELSE EXTRACT(hour FROM t1.time_loading)
            END
            ELSE EXTRACT(hour FROM t1.time_loading)
        END AS t_load,
    t1.no_production,
    t1.direct,
    to_char(t1.date_production::timestamp with time zone, 'YYYY-MM-DD'::text) AS ref_material,
    ((replace(to_char(t1.date_production::timestamp with time zone, 'YYYY-MM-DD'::text), ' '::text, ''::text) || replace(TRIM(BOTH FROM t1.category_mine), ' '::text, ''::text)) || replace(TRIM(BOTH FROM t2.sources_area), ' '::text, ''::text)) || replace(TRIM(BOTH FROM t1.vendors), ' '::text, ''::text) AS ref_material_old,
    (((to_char(t1.date_production::timestamp with time zone, 'YYYY-MM-DD'::text) || TRIM(BOTH FROM t1.category_mine)) || TRIM(BOTH FROM t2.sources_area)) || TRIM(BOTH FROM t1.vendors)) || TRIM(BOTH FROM t1.hauler_type) AS ref_truck,
    t1.iup_id,
    t7.iup_code,
    t7.iup_name,
    t1.user_id,
    t8.username,
    t1.created_at
FROM mining_productions t1
LEFT JOIN master_mine_sources_point_loading t3 ON t3.id = t1.loading_point AND t3.iup_id = t1.iup_id
LEFT JOIN master_mine_sources t2 ON t2.id = t3.id_sources AND t2.iup_id = t1.iup_id
LEFT JOIN master_mine_sources_point_dumping t4 ON t4.id = t1.dumping_point AND t4.iup_id = t1.iup_id
LEFT JOIN master_mine_sources_point_dome t5 ON t5.id = t1.dome_id AND t5.iup_id = t1.iup_id
LEFT JOIN master_materials t6 ON t6.id = t1.id_material
LEFT JOIN master_mine_iup t7 ON t7.id = t1.iup_id
LEFT JOIN accounts_user t8 ON t8.id = t1.user_id;