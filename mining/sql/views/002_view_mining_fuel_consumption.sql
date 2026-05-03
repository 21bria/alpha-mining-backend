CREATE OR REPLACE VIEW view_mining_fuel_consumption AS 
SELECT 
    t1.id,
    t1.date,
    t1.shift,
    t1.unit,
    t2.id AS unit_id,
    t3.category,
    t1.hours_metre,
    t1.drivers,
    t1.charging_time,
    t1.volume,
    t1.storage,
    t1.operator,
    t4.code,
    t1.iup_id,
    t5.iup_code,
    t5.iup_name,
    t1.user_id,
    t6.username,
    t1.created_at
FROM mining_fuel_consumption t1
-- cari dulu unit berdasarkan kode/nama unit yang tersimpan di fuel
LEFT JOIN master_units t2 
  ON t2.unit_code::text = t1.unit::text
-- setelah dapat unit_id, baru cek assignment sesuai IUP
LEFT JOIN master_unit_assignments ua
  ON ua.unit_id = t2.id
 AND ua.iup_id = t1.iup_id
 AND ua.active = true
LEFT JOIN master_units_categories t3 
  ON t3.id = t2.id_category
LEFT JOIN master_vendors t4 
  ON t4.id = t2.id_vendor
LEFT JOIN master_mine_iup t5 
  ON t5.id = t1.iup_id
LEFT JOIN accounts_user t6 
  ON t6.id = t1.user_id;