-- 1
SELECT COUNT(*) FROM companies;

-- 2
SELECT COUNT(*) FROM profitandloss;

-- 3
SELECT COUNT(*) FROM balancesheet;

-- 4
SELECT COUNT(*) FROM cashflow;

-- 5
SELECT company_id, AVG(sales) AS avg_sales
FROM profitandloss
GROUP BY company_id
ORDER BY avg_sales DESC
LIMIT 10;

-- 6
SELECT company_id, MAX(net_profit) AS max_profit
FROM profitandloss
GROUP BY company_id
ORDER BY max_profit DESC
LIMIT 10;

-- 7
SELECT broad_sector, COUNT(*) AS companies
FROM sectors
GROUP BY broad_sector;

-- 8
SELECT company_id, COUNT(*) AS price_records
FROM stock_prices
GROUP BY company_id
ORDER BY price_records DESC
LIMIT 10;

-- 9
SELECT *
FROM financial_ratios
LIMIT 10;

-- 10
SELECT *
FROM companies
LIMIT 10;