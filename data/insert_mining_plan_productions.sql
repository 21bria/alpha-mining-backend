INSERT INTO kawi.mining_plan_productions (
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
    topsoil,
    ob,
    lglo,
    mglo,
    hglo,
    waste,
    mws,
    lgso,
    uglo,
    mgso,
    hgso,
    lim,
    sap,
    quarry,
    ballast,
    biomass,
    ref_plan,
    task_id,
    iup_id,
    user_id
)
SELECT
    COALESCE(s.created_at, now()),
    COALESCE(s.updated_at, now()),
    -- CODE: IUP + DATE + CATEGORY
    'PLAN-IUP-001-' ||
    TO_CHAR(s.date_plan, 'YYYYMMDD') || '-' ||
    COALESCE(NULLIF(s.category, ''), 'UNKNOWN'),
    false,
    NULL,
    -- UUID
    gen_random_uuid(),
    s.date_plan,
    s.category,
    s.sources,
    s.vendors,
    -- NUMERIC SAFE
    COALESCE(NULLIF(s.topsoil::text, '')::numeric, 0),
    COALESCE(NULLIF(s.ob::text, '')::numeric, 0),
    COALESCE(NULLIF(s.lglo::text, '')::numeric, 0),
    COALESCE(NULLIF(s.mglo::text, '')::numeric, 0),
    COALESCE(NULLIF(s.hglo::text, '')::numeric, 0),
    COALESCE(NULLIF(s.waste::text, '')::numeric, 0),
    COALESCE(NULLIF(s.mws::text, '')::numeric, 0),
    COALESCE(NULLIF(s.lgso::text, '')::numeric, 0),
    COALESCE(NULLIF(s.uglo::text, '')::numeric, 0),
    COALESCE(NULLIF(s.mgso::text, '')::numeric, 0),
    COALESCE(NULLIF(s.hgso::text, '')::numeric, 0),
    COALESCE(NULLIF(s.lim::text, '')::numeric, 0),
    COALESCE(NULLIF(s.sap::text, '')::numeric, 0),
    COALESCE(NULLIF(s.quarry::text, '')::numeric, 0),
    COALESCE(NULLIF(s.ballast::text, '')::numeric, 0),
    COALESCE(NULLIF(s.biomass::text, '')::numeric, 0),
    s.ref_plan,
    NULL AS task_id,
    -- IUP FIX
    1 AS iup_id,
    -- USER SAFE
    1 AS user_id
FROM ext_kqms.plan_productions s

-- ANTI DUPLICATE (LOGICAL)
-- WHERE NOT EXISTS (
--     SELECT 1
--     FROM kawi.mining_plan_productions t
--     WHERE t.iup_id = 1
--       AND t.date_plan = s.date_plan
--       AND t.category = s.category
-- );