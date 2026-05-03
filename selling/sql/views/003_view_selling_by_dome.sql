CREATE OR REPLACE VIEW view_selling_by_dome AS 
SELECT
	iup_id,
	iup_code,
	stockpile,
    dome,
    sale_dome,
    material,
    sale_adjust,
    sum(tonnage) AS tonnage
  FROM view_selling_details
  WHERE status_barging = 'Complete'::text
  GROUP BY iup_id,iup_code,stockpile, dome, material, sale_adjust, sale_dome;