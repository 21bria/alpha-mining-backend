-- insert from old to New :

INSERT INTO kawi.mining_plan_production (
    created_at,
    updated_at,
    code,
    is_deleted,
    deleted_at,
    id,
    date_plan,
    category,
    source_code,
    vendor_code,
    ref_plan,
    task_id,
    iup_id,
    user_id
)
SELECT
    created_at,
    updated_at,
    code,
    is_deleted,
    deleted_at,
    id,
    date_plan,
    category,
    sources,
    vendors,
    ref_plan,
    task_id,
    iup_id,
    user_id
FROM kawi.mining_plan_productions
ON CONFLICT (id) DO NOTHING;

-- Insert Details
INSERT INTO kawi.mining_plan_production_details (
    id,
    plan_id,
    material_code,
    material_name,
    tonnage
)
SELECT gen_random_uuid(), id, 'TOPSOIL', 'Top Soil', topsoil
FROM kawi.mining_plan_productions
WHERE COALESCE(topsoil, 0) <> 0

UNION ALL
SELECT gen_random_uuid(), id, 'OB', 'OB', ob
FROM kawi.mining_plan_productions
WHERE COALESCE(ob, 0) <> 0

UNION ALL
SELECT gen_random_uuid(), id, 'WASTE', 'Waste', waste
FROM kawi.mining_plan_productions
WHERE COALESCE(waste, 0) <> 0

UNION ALL
SELECT gen_random_uuid(), id, 'LIM', 'LIM', lim
FROM kawi.mining_plan_productions
WHERE COALESCE(lim, 0) <> 0

UNION ALL
SELECT gen_random_uuid(), id, 'SAP', 'SAP', sap
FROM kawi.mining_plan_productions
WHERE COALESCE(sap, 0) <> 0

UNION ALL
SELECT gen_random_uuid(), id, 'QUARRY', 'Quarry', quarry
FROM kawi.mining_plan_productions
WHERE COALESCE(quarry, 0) <> 0

UNION ALL
SELECT gen_random_uuid(), id, 'BALLAST', 'Ballast', ballast
FROM kawi.mining_plan_productions
WHERE COALESCE(ballast, 0) <> 0

UNION ALL
SELECT gen_random_uuid(), id, 'BIOMASS', 'Biomass', biomass
FROM kawi.mining_plan_productions
WHERE COALESCE(biomass, 0) <> 0;