SELECT COUNT(*) AS total_rows, COALESCE(SUM(tonnage), 0) AS total_tonnage
FROM view_mining_productions
WHERE date_production >= DATE '2026-04-01'
  AND date_production < DATE '2026-05-01';

SELECT COUNT(*) AS total_rows, COALESCE(SUM(tonnage), 0) AS total_tonnage
FROM mining_productions
WHERE date_production >= DATE '2026-04-01'
  AND date_production < DATE '2026-05-01';


SELECT COUNT(*) AS total_rows, COALESCE(SUM(tonnage), 0) AS total_tonnage
FROM mine_productions
WHERE date_production >= DATE '2026-04-01'
  AND date_production < DATE '2026-05-01';