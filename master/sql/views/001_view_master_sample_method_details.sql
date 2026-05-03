CREATE OR REPLACE VIEW view_master_sample_method_details AS
SELECT 
    t1.id_method AS id,
    t3.sample_method,
    t1.id_type_id AS type_id,
    t2.type_sample
FROM master_sample_type_details t1
JOIN master_sample_type t2 ON t1.id_type_id = t2.id
JOIN master_sample_methods t3 ON t1.id_method = t3.id;