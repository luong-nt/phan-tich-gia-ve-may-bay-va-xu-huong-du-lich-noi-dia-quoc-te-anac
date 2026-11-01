-- ============================================================================
-- ANAC PORTFOLIO | BUOC 4 - PHAN TICH CHUYEN SAU TREN DUCKDB
-- Phien ban: 1.0 | CHI DOC DU LIEU (SELECT / WITH), khong sua Data Warehouse.
-- CSDL: data_warehouse/anac.duckdb
-- Grain Fact: thang BAN VE x thi truong x san bay di x san bay den.
-- Chu y nghiep vu:
--   (1) ASSENTOS la so GHE BAN, khong dong nghia hanh khach thuc bay.
--   (2) Noi dia = BRL, Quoc te = USD: KHONG cong / so sanh gia truc tiep.
--   (3) 2026 chua du nam; thang 05/2026 noi dia chua co trong DW.
--   (4) Gia gop nhieu thang = SUM(fare_weighted_sum) / SUM(priced_seats).
--   (5) Gia trung binh trong vw_monthly_kpi la binh quan gia co trong so theo ghe.
--   (6) Top route la duong bay CO HUONG (A->B khac B->A).
-- ============================================================================

-- QUERY Q01: Bang KPI theo thang - nen tang cho phan tich
SELECT
    month_key,
    sale_year,
    sale_month,
    market_code,
    market_name,
    currency_code,
    total_seats,
    priced_seats,
    ROUND(avg_fare, 2) AS avg_fare,
    ROUND(price_coverage_pct, 2) AS price_coverage_pct,
    source_record_count
FROM vw_monthly_kpi
ORDER BY market_code, month_key;

-- QUERY Q02: MoM - chi tinh khi hai THANG LIEN TIEP deu ton tai
WITH paired AS (
    SELECT
        cur.month_key, cur.sale_year, cur.sale_month,
        cur.market_code, cur.currency_code,
        cur.total_seats, cur.avg_fare,
        prv.month_key AS previous_month_key,
        prv.total_seats AS previous_seats,
        prv.avg_fare AS previous_fare
    FROM vw_monthly_kpi cur
    LEFT JOIN vw_monthly_kpi prv
      ON prv.market_code = cur.market_code
     AND prv.month_key = CASE
           WHEN cur.sale_month = 1 THEN (cur.sale_year - 1) * 100 + 12
           ELSE cur.month_key - 1
         END
)
SELECT
    month_key, market_code, currency_code,
    previous_month_key,
    total_seats,
    ROUND(avg_fare, 2) AS avg_fare,
    CASE WHEN previous_seats > 0
         THEN ROUND(100.0 * (total_seats / previous_seats - 1), 2)
    END AS mom_seats_pct,
    CASE WHEN previous_fare > 0
         THEN ROUND(100.0 * (avg_fare / previous_fare - 1), 2)
    END AS mom_fare_pct
FROM paired
ORDER BY market_code, month_key;

-- QUERY Q03: YoY theo DUNG THANG cua nam truoc, tung thi truong
SELECT
    cur.month_key, cur.market_code, cur.currency_code,
    prv.month_key AS previous_year_month,
    cur.total_seats,
    ROUND(cur.avg_fare, 2) AS avg_fare,
    CASE WHEN prv.total_seats > 0
         THEN ROUND(100.0 * (cur.total_seats / prv.total_seats - 1), 2)
    END AS yoy_seats_pct,
    CASE WHEN prv.avg_fare > 0
         THEN ROUND(100.0 * (cur.avg_fare / prv.avg_fare - 1), 2)
    END AS yoy_fare_pct
FROM vw_monthly_kpi cur
LEFT JOIN vw_monthly_kpi prv
  ON prv.market_code = cur.market_code
 AND prv.month_key = cur.month_key - 100
ORDER BY cur.market_code, cur.month_key;

-- QUERY Q04: Tong ket theo nam; CANH BAO nam chua du 12 thang
-- Khong dung AVG(avg_fare) vi se lam sai gia binh quan gop nam.
SELECT
    d.sale_year, m.market_code, m.currency_code,
    COUNT(DISTINCT d.sale_month) AS months_observed,
    CASE WHEN COUNT(DISTINCT d.sale_month) = 12
         THEN 'FULL_YEAR' ELSE 'INCOMPLETE_YEAR' END AS coverage_status,
    SUM(f.total_seats) AS total_seats,
    SUM(f.priced_seats) AS priced_seats,
    ROUND(SUM(f.fare_weighted_sum) / NULLIF(SUM(f.priced_seats), 0), 2)
      AS weighted_avg_fare,
    ROUND(100.0 * SUM(f.priced_seats) / NULLIF(SUM(f.total_seats), 0), 2)
      AS price_coverage_pct
FROM fact_airfare_route_monthly f
JOIN dim_month d ON d.month_key = f.month_key
JOIN dim_market m ON m.market_key = f.market_key
GROUP BY d.sale_year, m.market_code, m.currency_code
ORDER BY m.market_code, d.sale_year;

-- QUERY Q05: Like-for-like YTD: 2026 so voi 2025 CHI o cac thang 2026 co mat
-- KHONG so sanh 8 thang 2026 voi du 12 thang 2025.
WITH paired AS (
    SELECT
        a.market_code, a.currency_code, a.sale_month,
        a.total_seats AS seats_2026, b.total_seats AS seats_2025,
        a.avg_fare * a.priced_seats AS fare_x_seats_2026,
        b.avg_fare * b.priced_seats AS fare_x_seats_2025,
        a.priced_seats AS priced_2026, b.priced_seats AS priced_2025
    FROM vw_monthly_kpi a
    JOIN vw_monthly_kpi b
      ON b.market_code = a.market_code
     AND b.sale_month = a.sale_month
     AND b.sale_year = 2025
    WHERE a.sale_year = 2026
)
SELECT
    market_code, currency_code,
    COUNT(DISTINCT sale_month) AS matched_months,
    STRING_AGG(CAST(sale_month AS VARCHAR), ', ' ORDER BY sale_month)
      AS matched_month_list,
    SUM(seats_2025) AS seats_2025_same_months,
    SUM(seats_2026) AS seats_2026_same_months,
    ROUND(100.0 * (SUM(seats_2026) / NULLIF(SUM(seats_2025), 0) - 1), 2)
      AS seats_yoy_pct,
    ROUND(SUM(fare_x_seats_2025) / NULLIF(SUM(priced_2025), 0), 2)
      AS weighted_fare_2025,
    ROUND(SUM(fare_x_seats_2026) / NULLIF(SUM(priced_2026), 0), 2)
      AS weighted_fare_2026,
    ROUND(100.0 * (
       (SUM(fare_x_seats_2026) / NULLIF(SUM(priced_2026), 0)) /
       NULLIF(SUM(fare_x_seats_2025) / NULLIF(SUM(priced_2025), 0), 0) - 1
    ), 2) AS fare_yoy_pct
FROM paired
GROUP BY market_code, currency_code
ORDER BY market_code;

-- QUERY Q06: Mua vu theo thang, chi hai nam da du 12 thang (2024-2025)
-- Cac thang duoc gop THEO TRONG SO GHE CO GIA, khong lay trung binh gia don gian.
SELECT
    market_code, currency_code, sale_month,
    COUNT(DISTINCT sale_year) AS years_observed,
    ROUND(SUM(avg_fare * priced_seats) / NULLIF(SUM(priced_seats), 0), 2)
      AS weighted_avg_fare_2024_2025,
    ROUND(AVG(total_seats), 0) AS avg_monthly_seats_2024_2025
FROM vw_monthly_kpi
WHERE sale_year IN (2024, 2025)
GROUP BY market_code, currency_code, sale_month
ORDER BY market_code, sale_month;

-- QUERY Q07: Pearson r giua gia va so ghe theo thi truong va NAM
-- Luu y: n=12 (nam du) hoac n=8 (noi dia 2026); khong suy ra nhan qua.
SELECT
    sale_year, market_code, currency_code,
    COUNT(*) AS observed_months,
    ROUND(CORR(CAST(avg_fare AS DOUBLE), CAST(total_seats AS DOUBLE)), 4)
      AS pearson_r_fare_vs_seats
FROM vw_monthly_kpi
WHERE avg_fare IS NOT NULL AND total_seats IS NOT NULL
GROUP BY sale_year, market_code, currency_code
HAVING COUNT(*) >= 6
ORDER BY market_code, sale_year;

-- QUERY Q08: Cac thang gia va ghe bien dong NGUOC CHIEU (MoM lien tiep)
WITH changes AS (
    SELECT
        a.month_key, a.market_code, a.currency_code,
        ROUND(100.0 * (a.avg_fare / NULLIF(b.avg_fare, 0) - 1), 2)
          AS mom_fare_pct,
        ROUND(100.0 * (a.total_seats / NULLIF(b.total_seats, 0) - 1), 2)
          AS mom_seats_pct
    FROM vw_monthly_kpi a
    JOIN vw_monthly_kpi b
      ON b.market_code = a.market_code
     AND b.month_key = CASE WHEN a.sale_month = 1
           THEN (a.sale_year - 1) * 100 + 12 ELSE a.month_key - 1 END
)
SELECT
    month_key, market_code, currency_code, mom_fare_pct, mom_seats_pct,
    CASE WHEN mom_fare_pct > 0 THEN 'FARE_UP_SEATS_DOWN'
         ELSE 'FARE_DOWN_SEATS_UP' END AS signal
FROM changes
WHERE (mom_fare_pct > 0 AND mom_seats_pct < 0)
   OR (mom_fare_pct < 0 AND mom_seats_pct > 0)
ORDER BY market_code, month_key;

-- QUERY Q09: Top 20 TUYEN CO HUONG theo so ghe, nam 2024/2025 DU 12 THANG
WITH ranked AS (
    SELECT
        sale_year, market_code, currency_code,
        origin_airport_code, origin_name,
        destination_airport_code, destination_name,
        total_seats, ROUND(avg_fare, 2) AS avg_fare,
        ROW_NUMBER() OVER (
          PARTITION BY sale_year, market_code
          ORDER BY total_seats DESC, origin_airport_code, destination_airport_code
        ) AS route_rank
    FROM vw_route_ranking
    WHERE sale_year IN (2024, 2025)
)
SELECT * FROM ranked
WHERE route_rank <= 20
ORDER BY market_code, sale_year, route_rank;

-- QUERY Q10: Top 20 tuyen tang/giảm manh 2024->2025; co nguong ghe hai nam
-- Nguong 10,000 ghe/nam giup tranh % tang vo cung lon tu tuyen sieu nho.
WITH a AS (
    SELECT * FROM vw_route_ranking WHERE sale_year = 2024
), b AS (
    SELECT * FROM vw_route_ranking WHERE sale_year = 2025
), paired AS (
    SELECT
        a.market_code, a.currency_code,
        a.origin_airport_code, a.destination_airport_code,
        a.total_seats AS seats_2024, b.total_seats AS seats_2025,
        ROUND(100.0 * (b.total_seats / NULLIF(a.total_seats, 0) - 1), 2)
          AS yoy_seats_pct
    FROM a
    JOIN b ON b.market_code = a.market_code
          AND b.origin_airport_code = a.origin_airport_code
          AND b.destination_airport_code = a.destination_airport_code
    WHERE a.total_seats >= 10000 AND b.total_seats >= 10000
)
SELECT * FROM paired
ORDER BY ABS(yoy_seats_pct) DESC, market_code
LIMIT 20;

-- QUERY Q11: Muc do tap trung mang luoi - 10 tuyen lon nhat chiem bao nhieu % ghe?
-- Day la do tap trung theo TUYEN, khong phai thi phan hang hang khong / HHI.
WITH routes AS (
    SELECT
        d.sale_year, m.market_code,
        f.origin_airport_code, f.destination_airport_code,
        SUM(f.total_seats) AS route_seats
    FROM fact_airfare_route_monthly f
    JOIN dim_month d ON d.month_key = f.month_key
    JOIN dim_market m ON m.market_key = f.market_key
    WHERE d.sale_year IN (2024, 2025)
    GROUP BY d.sale_year, m.market_code,
             f.origin_airport_code, f.destination_airport_code
), ranked AS (
    SELECT *, ROW_NUMBER() OVER (
        PARTITION BY sale_year, market_code
        ORDER BY route_seats DESC, origin_airport_code, destination_airport_code
    ) AS rn FROM routes
)
SELECT
    sale_year, market_code,
    SUM(route_seats) AS all_route_seats,
    SUM(CASE WHEN rn <= 10 THEN route_seats ELSE 0 END) AS top10_route_seats,
    ROUND(100.0 * SUM(CASE WHEN rn <= 10 THEN route_seats ELSE 0 END)
          / NULLIF(SUM(route_seats), 0), 2) AS top10_seat_share_pct,
    COUNT(*) AS distinct_directional_routes
FROM ranked
GROUP BY sale_year, market_code
ORDER BY market_code, sale_year;

-- QUERY Q12: Top 10 san bay DEN theo ghe, chi xet cac luong co DI tu Brazil
-- Loc theo country_code co the bo qua san bay chua map duoc quoc gia.
WITH dest AS (
    SELECT
        d.sale_year, m.market_code, m.currency_code,
        f.destination_airport_code,
        MAX(a_to.airport_name) AS destination_name,
        MAX(a_to.country_code) AS destination_country,
        SUM(f.total_seats) AS seats_sold
    FROM fact_airfare_route_monthly f
    JOIN dim_month d ON d.month_key = f.month_key
    JOIN dim_market m ON m.market_key = f.market_key
    LEFT JOIN dim_airport a_from
      ON a_from.airport_code = f.origin_airport_code
    LEFT JOIN dim_airport a_to
      ON a_to.airport_code = f.destination_airport_code
    WHERE d.sale_year IN (2024, 2025)
      AND a_from.country_code = 'BR'
      AND (
        (m.market_code = 'domestic' AND a_to.country_code = 'BR')
        OR
        (m.market_code = 'international' AND a_to.country_code <> 'BR')
      )
    GROUP BY d.sale_year, m.market_code, m.currency_code,
             f.destination_airport_code
), ranked AS (
    SELECT *, ROW_NUMBER() OVER (
        PARTITION BY sale_year, market_code
        ORDER BY seats_sold DESC, destination_airport_code
    ) AS dest_rank FROM dest
)
SELECT * FROM ranked
WHERE dest_rank <= 10
ORDER BY market_code, sale_year, dest_rank;

-- QUERY Q13: Tuyen gia ve cao trong cac tuyen du quy mo (>=10,000 ghe/nam)
-- Gia la binh quan ghe co gia; loc 2024-2025 (nam du 12 thang).
WITH ranked AS (
    SELECT
        sale_year, market_code, currency_code,
        origin_airport_code, destination_airport_code,
        total_seats, ROUND(avg_fare, 2) AS avg_fare,
        ROW_NUMBER() OVER (
            PARTITION BY sale_year, market_code
            ORDER BY avg_fare DESC, origin_airport_code, destination_airport_code
        ) AS expensive_rank
    FROM vw_route_ranking
    WHERE sale_year IN (2024, 2025)
      AND total_seats >= 10000
      AND avg_fare IS NOT NULL
)
SELECT * FROM ranked
WHERE expensive_rank <= 10
ORDER BY market_code, sale_year, expensive_rank;

-- QUERY Q14: Canh bao BIEN DONG BAT THUONG theo nguong thuc hanh
-- Nguong 20% gia / 30% ghe la heuristic, KHONG phai phat hien outlier duoc xac nhan.
WITH changes AS (
    SELECT
        a.month_key, a.market_code, a.currency_code,
        ROUND(100.0 * (a.avg_fare / NULLIF(b.avg_fare, 0) - 1), 2)
          AS mom_fare_pct,
        ROUND(100.0 * (a.total_seats / NULLIF(b.total_seats, 0) - 1), 2)
          AS mom_seats_pct
    FROM vw_monthly_kpi a
    JOIN vw_monthly_kpi b
      ON b.market_code = a.market_code
     AND b.month_key = CASE WHEN a.sale_month = 1
           THEN (a.sale_year - 1) * 100 + 12 ELSE a.month_key - 1 END
)
SELECT
    month_key, market_code, currency_code,
    mom_fare_pct, mom_seats_pct,
    CASE WHEN ABS(mom_fare_pct) >= 20 THEN 'FARE_MOVE_20PCT' END AS fare_flag,
    CASE WHEN ABS(mom_seats_pct) >= 30 THEN 'SEATS_MOVE_30PCT' END AS seats_flag
FROM changes
WHERE ABS(mom_fare_pct) >= 20 OR ABS(mom_seats_pct) >= 30
ORDER BY market_code, month_key;

-- QUERY Q15: Do phu toa do san bay cua FACT theo nam va thi truong
-- Khong xoa fact: loai tuy chon khi ve ban do, nhung BAO CAO ty le ghe bi anh huong.
WITH flags AS (
    SELECT
        d.sale_year, m.market_code,
        f.total_seats,
        CASE WHEN a.latitude IS NULL OR a.longitude IS NULL
               OR b.latitude IS NULL OR b.longitude IS NULL
             THEN 1 ELSE 0 END AS missing_geo
    FROM fact_airfare_route_monthly f
    JOIN dim_month d ON d.month_key = f.month_key
    JOIN dim_market m ON m.market_key = f.market_key
    LEFT JOIN dim_airport a ON a.airport_code = f.origin_airport_code
    LEFT JOIN dim_airport b ON b.airport_code = f.destination_airport_code
)
SELECT
    sale_year, market_code,
    COUNT(*) AS fact_rows,
    SUM(missing_geo) AS rows_missing_geo,
    ROUND(100.0 * SUM(missing_geo) / NULLIF(COUNT(*), 0), 2)
      AS rows_missing_geo_pct,
    SUM(total_seats) AS total_seats,
    SUM(CASE WHEN missing_geo = 1 THEN total_seats ELSE 0 END)
      AS seats_on_routes_missing_geo,
    ROUND(100.0 * SUM(CASE WHEN missing_geo = 1 THEN total_seats ELSE 0 END)
          / NULLIF(SUM(total_seats), 0), 2) AS seats_missing_geo_pct
FROM flags
GROUP BY sale_year, market_code
ORDER BY market_code, sale_year;

-- QUERY Q16: Phat hien KY TRONG ben trong moi nam-thi-truong
-- Chi kiem tra tu thang 01 den thang da xuat hien CUOI CUNG cua nam do.
-- Khong duoc khang dinh ANAC chua cong bo chi tu ket qua DW nay.
WITH coverage AS (
    SELECT sale_year, market_code, MAX(sale_month) AS latest_month
    FROM vw_monthly_kpi
    GROUP BY sale_year, market_code
), expected AS (
    SELECT c.sale_year, c.market_code, series.m AS sale_month
    FROM coverage c
    CROSS JOIN generate_series(1, 12) AS series(m)
    WHERE series.m <= c.latest_month
)
SELECT
    e.sale_year, e.market_code, e.sale_month,
    e.sale_year * 100 + e.sale_month AS missing_month_key,
    'NOT_IN_WAREHOUSE_CHECK_SOURCE' AS status
FROM expected e
LEFT JOIN vw_monthly_kpi k
  ON k.sale_year = e.sale_year
 AND k.market_code = e.market_code
 AND k.sale_month = e.sale_month
WHERE k.month_key IS NULL
ORDER BY e.market_code, e.sale_year, e.sale_month;

-- QUERY Q17: KPI theo QUY; chi cac quy co DU 3 thang du lieu
-- Quy 2/2026 noi dia khong du vi thieu 2026-05 => khong xuat quy do.
WITH quarter_kpi AS (
    SELECT
        d.sale_year, d.sale_quarter,
        m.market_code, m.currency_code,
        COUNT(DISTINCT d.sale_month) AS months_present,
        SUM(f.total_seats) AS seats_sold,
        SUM(f.priced_seats) AS priced_seats,
        SUM(f.fare_weighted_sum) AS fare_weighted_sum
    FROM fact_airfare_route_monthly f
    JOIN dim_month d ON d.month_key = f.month_key
    JOIN dim_market m ON m.market_key = f.market_key
    GROUP BY d.sale_year, d.sale_quarter, m.market_code, m.currency_code
)
SELECT
    sale_year, sale_quarter, market_code, currency_code,
    seats_sold,
    ROUND(fare_weighted_sum / NULLIF(priced_seats, 0), 2)
      AS weighted_avg_fare
FROM quarter_kpi
WHERE months_present = 3
ORDER BY market_code, sale_year, sale_quarter;
