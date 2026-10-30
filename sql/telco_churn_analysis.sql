/* =====================================================================
   TELECOM CUSTOMER CHURN ANALYSIS  |  PostgreSQL
   Dataset : IBM Telco Customer Churn (Kaggle) - 7,043 customers, 21 columns
   Goal    : Find who churns, why, how much revenue it costs, and who to target
   ===================================================================== */


/* =====================================================================
   SECTION 1: SCHEMA & DATA LOAD
   ===================================================================== */

DROP TABLE IF EXISTS telco_raw CASCADE;

CREATE TABLE telco_raw (
    customer_id        VARCHAR(20),
    gender             VARCHAR(10),
    senior_citizen     INT,
    partner            VARCHAR(3),
    dependents         VARCHAR(3),
    tenure             INT,
    phone_service      VARCHAR(3),
    multiple_lines     VARCHAR(25),
    internet_service   VARCHAR(25),
    online_security    VARCHAR(25),
    online_backup      VARCHAR(25),
    device_protection  VARCHAR(25),
    tech_support       VARCHAR(25),
    streaming_tv       VARCHAR(25),
    streaming_movies   VARCHAR(25),
    contract           VARCHAR(25),
    paperless_billing  VARCHAR(3),
    payment_method     VARCHAR(40),
    monthly_charges    NUMERIC(8,2),
    total_charges      VARCHAR(20),     -- loaded as text: 11 rows contain blanks
    churn              VARCHAR(3)
);

-- Run in psql (adjust the path to where you saved the CSV):
-- \copy telco_raw FROM 'WA_Fn-UseC_-Telco-Customer-Churn.csv' WITH (FORMAT csv, HEADER true);


/* =====================================================================
   SECTION 2: DATA CLEANING  (raw -> analysis-ready table)
   ===================================================================== */

DROP TABLE IF EXISTS customers CASCADE;

CREATE TABLE customers AS
SELECT
    customer_id,
    gender,
    senior_citizen::SMALLINT                              AS senior_citizen,
    (partner = 'Yes')                                     AS has_partner,
    (dependents = 'Yes')                                  AS has_dependents,
    tenure                                                AS tenure_months,
    phone_service,
    multiple_lines,
    internet_service,
    online_security,
    online_backup,
    device_protection,
    tech_support,
    streaming_tv,
    streaming_movies,
    contract,
    (paperless_billing = 'Yes')                           AS paperless_billing,
    payment_method,
    monthly_charges,
    CASE WHEN TRIM(total_charges) = '' THEN NULL
         ELSE total_charges::NUMERIC(10,2) END            AS total_charges,
    CASE WHEN churn = 'Yes' THEN 1 ELSE 0 END::SMALLINT   AS churn_flag,
    CASE
        WHEN tenure BETWEEN 0  AND 12 THEN '1. 0-12 months'
        WHEN tenure BETWEEN 13 AND 24 THEN '2. 13-24 months'
        WHEN tenure BETWEEN 25 AND 48 THEN '3. 25-48 months'
        ELSE                               '4. 49+ months'
    END                                                   AS tenure_bucket
FROM telco_raw;

ALTER TABLE customers ADD PRIMARY KEY (customer_id);

-- Data quality checks -------------------------------------------------
-- 2.1 Duplicates (expect 0)
SELECT customer_id, COUNT(*) FROM customers GROUP BY customer_id HAVING COUNT(*) > 1;

-- 2.2 Nulls per key column (expect only total_charges = 11, all tenure = 0)
SELECT
    COUNT(*) FILTER (WHERE total_charges IS NULL)    AS null_total_charges,
    COUNT(*) FILTER (WHERE monthly_charges IS NULL)  AS null_monthly_charges,
    COUNT(*) FILTER (WHERE contract IS NULL)         AS null_contract
FROM customers;

-- 2.3 Fix the 11 null total_charges (new customers who have not been billed yet)
UPDATE customers SET total_charges = 0 WHERE total_charges IS NULL AND tenure_months = 0;


/* =====================================================================
   SECTION 3: BUSINESS QUESTIONS & ANALYSIS
   ===================================================================== */

-- Q1. What is the overall churn rate?
SELECT
    COUNT(*)                                            AS total_customers,
    SUM(churn_flag)                                     AS churned_customers,
    ROUND(100.0 * SUM(churn_flag) / COUNT(*), 2)        AS churn_rate_pct
FROM customers;


-- Q2. Which contract type has the highest churn?
SELECT
    contract,
    COUNT(*)                                            AS customers,
    SUM(churn_flag)                                     AS churned,
    ROUND(100.0 * SUM(churn_flag) / COUNT(*), 2)        AS churn_rate_pct
FROM customers
GROUP BY contract
ORDER BY churn_rate_pct DESC;


-- Q3. When do customers leave? (churn by tenure bucket)
SELECT
    tenure_bucket,
    COUNT(*)                                            AS customers,
    SUM(churn_flag)                                     AS churned,
    ROUND(100.0 * SUM(churn_flag) / COUNT(*), 2)        AS churn_rate_pct
FROM customers
GROUP BY tenure_bucket
ORDER BY tenure_bucket;


-- Q4. Does internet service type or payment method drive churn?
SELECT
    internet_service,
    payment_method,
    COUNT(*)                                            AS customers,
    ROUND(100.0 * SUM(churn_flag) / COUNT(*), 2)        AS churn_rate_pct
FROM customers
GROUP BY internet_service, payment_method
HAVING COUNT(*) >= 50                                   -- ignore tiny segments
ORDER BY churn_rate_pct DESC;


-- Q5. Do add-on services (security, tech support, backup) reduce churn?
--     UNPIVOT-style: compare churn for customers WITH vs WITHOUT each service
WITH services AS (
    SELECT customer_id, churn_flag, 'Online Security'  AS service, online_security  AS status FROM customers WHERE internet_service <> 'No'
    UNION ALL
    SELECT customer_id, churn_flag, 'Tech Support',               tech_support               FROM customers WHERE internet_service <> 'No'
    UNION ALL
    SELECT customer_id, churn_flag, 'Online Backup',              online_backup              FROM customers WHERE internet_service <> 'No'
    UNION ALL
    SELECT customer_id, churn_flag, 'Device Protection',          device_protection          FROM customers WHERE internet_service <> 'No'
)
SELECT
    service,
    status,
    COUNT(*)                                            AS customers,
    ROUND(100.0 * SUM(churn_flag) / COUNT(*), 2)        AS churn_rate_pct
FROM services
GROUP BY service, status
ORDER BY service, status;


-- Q6. How much revenue are we losing to churn?
SELECT
    ROUND(SUM(monthly_charges) FILTER (WHERE churn_flag = 1), 2)         AS monthly_revenue_lost,
    ROUND(SUM(monthly_charges) FILTER (WHERE churn_flag = 1) * 12, 2)    AS annualized_revenue_lost,
    ROUND(100.0 * SUM(monthly_charges) FILTER (WHERE churn_flag = 1)
                / SUM(monthly_charges), 2)                               AS pct_of_total_mrr_lost
FROM customers;


-- Q7. Which segments cost us the most revenue? (CTE + window function)
WITH segment_loss AS (
    SELECT
        contract,
        internet_service,
        COUNT(*) FILTER (WHERE churn_flag = 1)                           AS churned_customers,
        ROUND(SUM(monthly_charges) FILTER (WHERE churn_flag = 1), 2)     AS monthly_revenue_lost
    FROM customers
    GROUP BY contract, internet_service
)
SELECT
    contract,
    internet_service,
    churned_customers,
    monthly_revenue_lost,
    ROUND(100.0 * monthly_revenue_lost / SUM(monthly_revenue_lost) OVER (), 2)  AS pct_of_total_loss,
    RANK() OVER (ORDER BY monthly_revenue_lost DESC)                            AS loss_rank
FROM segment_loss
ORDER BY loss_rank;


-- Q8. Rank payment methods by churn WITHIN each contract type (window function)
SELECT *
FROM (
    SELECT
        contract,
        payment_method,
        COUNT(*)                                        AS customers,
        ROUND(100.0 * SUM(churn_flag) / COUNT(*), 2)    AS churn_rate_pct,
        DENSE_RANK() OVER (
            PARTITION BY contract
            ORDER BY SUM(churn_flag)::NUMERIC / COUNT(*) DESC
        )                                               AS risk_rank_in_contract
    FROM customers
    GROUP BY contract, payment_method
) t
ORDER BY contract, risk_rank_in_contract;


-- Q9. Do higher-paying customers churn more? (quartiles with NTILE)
WITH priced AS (
    SELECT
        churn_flag,
        monthly_charges,
        NTILE(4) OVER (ORDER BY monthly_charges) AS price_quartile
    FROM customers
)
SELECT
    price_quartile,
    MIN(monthly_charges)                                AS min_price,
    MAX(monthly_charges)                                AS max_price,
    ROUND(100.0 * SUM(churn_flag) / COUNT(*), 2)        AS churn_rate_pct
FROM priced
GROUP BY price_quartile
ORDER BY price_quartile;


-- Q10. Cumulative share of churners by tenure month (running total)
WITH churn_by_month AS (
    SELECT tenure_months, COUNT(*) AS churners
    FROM customers
    WHERE churn_flag = 1
    GROUP BY tenure_months
)
SELECT
    tenure_months,
    churners,
    SUM(churners) OVER (ORDER BY tenure_months)         AS cumulative_churners,
    ROUND(100.0 * SUM(churners) OVER (ORDER BY tenure_months)
                / SUM(churners) OVER (), 2)             AS cumulative_pct
FROM churn_by_month
ORDER BY tenure_months;


-- Q11. Estimated customer lifetime value (CLV): churned vs retained
SELECT
    CASE WHEN churn_flag = 1 THEN 'Churned' ELSE 'Retained' END   AS status,
    COUNT(*)                                                       AS customers,
    ROUND(AVG(tenure_months), 1)                                   AS avg_tenure_months,
    ROUND(AVG(monthly_charges), 2)                                 AS avg_monthly_charge,
    ROUND(AVG(total_charges), 2)                                   AS avg_lifetime_revenue
FROM customers
GROUP BY churn_flag;


/* =====================================================================
   SECTION 4: CHURN RISK SCORING MODEL (rule-based, in pure SQL)
   Points are assigned from the patterns found in Q2-Q5.
   Adjust weights after viewing your own results.
   ===================================================================== */

DROP VIEW IF EXISTS v_customer_risk;

CREATE VIEW v_customer_risk AS
WITH scored AS (
    SELECT
        customer_id,
        contract,
        internet_service,
        payment_method,
        tenure_months,
        monthly_charges,
        churn_flag,
        (CASE WHEN contract = 'Month-to-month'          THEN 3 ELSE 0 END
       + CASE WHEN tenure_months <= 12                  THEN 2 ELSE 0 END
       + CASE WHEN internet_service = 'Fiber optic'     THEN 1 ELSE 0 END
       + CASE WHEN payment_method = 'Electronic check'  THEN 2 ELSE 0 END
       + CASE WHEN tech_support = 'No'                  THEN 1 ELSE 0 END
       + CASE WHEN online_security = 'No'               THEN 1 ELSE 0 END) AS risk_score
    FROM customers
)
SELECT
    *,
    CASE
        WHEN risk_score >= 7 THEN 'High Risk'
        WHEN risk_score >= 4 THEN 'Medium Risk'
        ELSE                      'Low Risk'
    END AS risk_band
FROM scored;

-- Validate the model: does a higher risk band actually churn more?
SELECT
    risk_band,
    COUNT(*)                                            AS customers,
    ROUND(100.0 * SUM(churn_flag) / COUNT(*), 2)        AS actual_churn_rate_pct,
    ROUND(SUM(monthly_charges), 2)                      AS monthly_revenue_at_stake
FROM v_customer_risk
GROUP BY risk_band
ORDER BY actual_churn_rate_pct DESC;

-- Action list: high-risk customers who have NOT churned yet (retention targets)
SELECT customer_id, contract, tenure_months, monthly_charges, risk_score
FROM v_customer_risk
WHERE risk_band = 'High Risk' AND churn_flag = 0
ORDER BY monthly_charges DESC
LIMIT 50;


/* =====================================================================
   SECTION 5: PERFORMANCE OPTIMIZATION
   Run EXPLAIN ANALYZE before and after; screenshot both for your README.
   ===================================================================== */

-- BEFORE
EXPLAIN ANALYZE
SELECT contract, COUNT(*), SUM(churn_flag)
FROM customers
WHERE churn_flag = 1 AND contract = 'Month-to-month'
GROUP BY contract;

CREATE INDEX idx_customers_contract_churn ON customers (contract, churn_flag);
CREATE INDEX idx_customers_tenure         ON customers (tenure_months);
ANALYZE customers;

-- AFTER
EXPLAIN ANALYZE
SELECT contract, COUNT(*), SUM(churn_flag)
FROM customers
WHERE churn_flag = 1 AND contract = 'Month-to-month'
GROUP BY contract;


/* =====================================================================
   SECTION 6: DASHBOARD-READY VIEW (connect Power BI / Tableau here)
   ===================================================================== */

CREATE OR REPLACE VIEW v_churn_dashboard AS
SELECT
    c.customer_id,
    c.gender,
    c.senior_citizen,
    c.contract,
    c.internet_service,
    c.payment_method,
    c.tenure_bucket,
    c.monthly_charges,
    c.total_charges,
    c.churn_flag,
    r.risk_score,
    r.risk_band
FROM customers c
JOIN v_customer_risk r USING (customer_id);
