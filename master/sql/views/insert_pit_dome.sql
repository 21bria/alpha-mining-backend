INSERT INTO master_mine_sources_pit_dome (
    dome,
    dome_type,
    id_loading,
    is_active,
    created_at,
    updated_at
)
SELECT
    'ALL',
    'STOCK',
    lp.id,
    true,
    NOW(),
    NOW()
FROM master_mine_sources_point_loading lp
WHERE UPPER(lp.loading_point) LIKE '%PIT%'
AND NOT EXISTS (
    SELECT 1
    FROM master_mine_sources_pit_dome d
    WHERE d.id_loading = lp.id
      AND LOWER(d.dome) = 'all'
);


-- Select check data
SELECT
    id,
    loading_point
FROM master_mine_sources_point_loading
WHERE UPPER(loading_point) LIKE '%PIT%'
ORDER BY loading_point;