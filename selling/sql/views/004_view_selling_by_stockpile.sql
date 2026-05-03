
CREATE OR REPLACE VIEW view_selling_by_stockpile AS 
  SELECT 
	  iup_id,
	  iup_code,
	  stockpile,
    sale_dome,
    material,
    sale_adjust,
    direct,
    sum(tonnage) AS tonnage
  FROM view_selling_details
  WHERE status_barging = 'Complete'::text
  GROUP BY iup_id,iup_code,stockpile, material, sale_adjust, sale_dome, direct;