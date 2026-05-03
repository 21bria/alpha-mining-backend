CREATE OR REPLACE VIEW view_master_units AS
SELECT
    u.id,
    u.unit_vendor,
    u.unit_code,
    u.unit_model,
    u.unit_class,
    u.brand,
    u.id_category,
    c.category,
    u.id_vendor,
    u.supports,
    u.status,
    u.description,
    u.commisioning_date,
    u.on_hire,
    u.off_hire,
    u.user_id,
    au.username,
    ua.iup_id,
    i.iup_code,
    i.iup_name,
    ua.start_date AS assignment_start_date,
    ua.end_date AS assignment_end_date,
    ua.active AS assignment_active,
    u.created_at,
    u.updated_at
FROM master_units u
LEFT JOIN master_unit_assignments ua
    ON ua.unit_id = u.id
    AND ua.active = TRUE
LEFT JOIN master_mine_iup i
    ON i.id = ua.iup_id
LEFT JOIN master_units_categories c
    ON c.id = u.id_category
LEFT JOIN accounts_user au
    ON au.id = u.user_id;