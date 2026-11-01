-- ANAC warehouse v1; grain: sale month x market x origin x destination.
-- Airports are a role-playing dimension: origin and destination.
CREATE TABLE IF NOT EXISTS dim_month (
  month_key INTEGER PRIMARY KEY,
  sale_year INTEGER NOT NULL,
  sale_month INTEGER NOT NULL,
  sale_quarter INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS dim_market (
  market_key INTEGER PRIMARY KEY,
  market_code VARCHAR NOT NULL UNIQUE,
  market_name VARCHAR NOT NULL,
  currency_code VARCHAR NOT NULL
);
CREATE TABLE IF NOT EXISTS dim_airport (
  airport_code VARCHAR PRIMARY KEY,
  airport_name VARCHAR,
  municipality VARCHAR,
  country_code VARCHAR,
  latitude DOUBLE,
  longitude DOUBLE
);
CREATE TABLE IF NOT EXISTS fact_airfare_route_monthly (
  month_key INTEGER NOT NULL REFERENCES dim_month(month_key),
  market_key INTEGER NOT NULL REFERENCES dim_market(market_key),
  origin_airport_code VARCHAR NOT NULL REFERENCES dim_airport(airport_code),
  destination_airport_code VARCHAR NOT NULL REFERENCES dim_airport(airport_code),
  total_seats BIGINT NOT NULL CHECK (total_seats >= 0),
  priced_seats BIGINT NOT NULL CHECK (priced_seats >= 0),
  fare_weighted_sum DOUBLE NOT NULL,
  source_record_count BIGINT,
  PRIMARY KEY(month_key, market_key, origin_airport_code, destination_airport_code),
  CHECK (priced_seats <= total_seats)
);
INSERT INTO dim_market VALUES
 (1, 'domestic', 'Noi dia', 'BRL'),
 (2, 'international', 'Quoc te', 'USD')
ON CONFLICT (market_key) DO NOTHING;

-- Do not sum fares across currencies; group by currency/market.
CREATE OR REPLACE VIEW vw_monthly_kpi AS
SELECT f.month_key, d.sale_year, d.sale_month, d.sale_quarter,
       m.market_code, m.market_name, m.currency_code,
       SUM(f.total_seats) AS total_seats,
       SUM(f.priced_seats) AS priced_seats,
       SUM(f.fare_weighted_sum) / NULLIF(SUM(f.priced_seats), 0) AS avg_fare,
       SUM(f.priced_seats) * 100.0 / NULLIF(SUM(f.total_seats), 0) AS price_coverage_pct,
       SUM(f.source_record_count) AS source_record_count
FROM fact_airfare_route_monthly f
JOIN dim_month d ON d.month_key = f.month_key
JOIN dim_market m ON m.market_key = f.market_key
GROUP BY f.month_key, d.sale_year, d.sale_month, d.sale_quarter,
         m.market_code, m.market_name, m.currency_code;

CREATE OR REPLACE VIEW vw_route_ranking AS
SELECT d.sale_year, m.market_code, m.currency_code,
       f.origin_airport_code, a.airport_name AS origin_name,
       f.destination_airport_code, b.airport_name AS destination_name,
       SUM(f.total_seats) AS total_seats,
       SUM(f.fare_weighted_sum) / NULLIF(SUM(f.priced_seats), 0) AS avg_fare
FROM fact_airfare_route_monthly f
JOIN dim_month d ON d.month_key=f.month_key
JOIN dim_market m ON m.market_key=f.market_key
LEFT JOIN dim_airport a ON a.airport_code=f.origin_airport_code
LEFT JOIN dim_airport b ON b.airport_code=f.destination_airport_code
GROUP BY d.sale_year, m.market_code, m.currency_code,
         f.origin_airport_code, a.airport_name,
         f.destination_airport_code, b.airport_name;
