-- 1. Di server, export dulu data permission

-- Jalankan di server:
SELECT
    g.name AS group_name,
    ct.app_label,
    ct.model,
    p.codename
FROM kawi.auth_group_permissions gp
JOIN kawi.auth_group g ON g.id = gp.group_id
JOIN kawi.auth_permission p ON p.id = gp.permission_id
JOIN kawi.django_content_type ct ON ct.id = p.content_type_id
ORDER BY g.name, ct.app_label, ct.model, p.codename;

-- Export hasilnya ke CSV.

-- 2. Di lokal, import CSV ke temporary table biasa
-- Buat dulu di lokal:
DROP TABLE IF EXISTS kawi.tmp_group_permissions;

CREATE TABLE kawi.tmp_group_permissions (
    group_name text,
    app_label text,
    model text,
    codename text
);

-- Lalu import CSV server ke tabel:
-- kawi.tmp_group_permissions

-- 3. Insert ke tabel asli lokal

INSERT INTO kawi.auth_group_permissions (group_id, permission_id)
SELECT DISTINCT
    g.id,
    p.id
FROM kawi.tmp_group_permissions t
JOIN kawi.auth_group g
    ON g.name = t.group_name
JOIN kawi.django_content_type ct
    ON ct.app_label = t.app_label
   AND ct.model = t.model
JOIN kawi.auth_permission p
    ON p.content_type_id = ct.id
   AND p.codename = t.codename
ON CONFLICT DO NOTHING;