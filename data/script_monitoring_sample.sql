--update selling_barging 
--set code_monitoring=CONCAT(type_selling,'_CKS' ,id_material,code_lot,code_sub,code_inc);

SELECT st.type_sample,msc.code,sp.id_material,sp.batch_code,sp.increments 
FROM geology_samples_productions as sp
left join master_sample_type as st on st.id =sp.id_type_sample 
left join master_selling_code msc  on msc.id =sp.product_code 
WHERE id_type_sample IN (
    SELECT id
    FROM master_sample_type
    WHERE type_sample IN ('LIS_CKS', 'SAS_CKS')
);


UPDATE geology_samples_productions sp
SET sale_monitoring = CONCAT(
    st.type_sample,
    msc.code,
    sp.id_material,
    sp.batch_code,
    sp.increments
)

FROM master_sample_type st,
     master_selling_code msc
WHERE st.id = sp.id_type_sample
  AND msc.id = sp.product_code
  AND st.type_sample IN ('LIS_CKS', 'SAS_CKS');
