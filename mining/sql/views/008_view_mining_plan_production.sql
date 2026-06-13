CREATE OR REPLACE VIEW view_mining_plan_productions AS
SELECT
    p.id,
    p.code,
    p.date_plan,
    p.category,
    p.source_code,
    p.vendor_code,
    p.iup_id,
    d.material_code,
    d.material_name,
    m.categories as categories_material,
    ROUND(COALESCE(d.tonnage, 0)::numeric, 1) AS tonnage,
    p.created_at,
    p.updated_at,
    p.user_id
FROM mining_plan_production p
JOIN mining_plan_production_details d ON d.plan_id = p.id
LEFT JOIN master_materials m ON m.name =d.material_name
WHERE p.is_deleted = false;