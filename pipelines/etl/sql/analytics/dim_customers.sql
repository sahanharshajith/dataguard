CREATE OR REPLACE TABLE analytics.dim_customers AS

WITH 
customer_metrics AS (
    SELECT
        customer_id,
        COUNT(*) FILTER (
            WHERE is_valid
        ) AS order_count,
        SUM(order_total) FILTER (
            WHERE is_valid
              AND status <> 'cancelled'
        ) AS total_spent
    FROM analytics.fct_orders
    GROUP BY customer_id
)

SELECT
    c.customer_id,
    c.first_name || ' ' || c.last_name AS full_name,
    c.email,
    c.country,
    c.signup_date,
    COALESCE(m.order_count, 0) AS order_count,
    COALESCE(
        m.total_spent,
        0::DECIMAL(12,2)
    ) AS total_spent,
    c._batch_id,
    c._loaded_at
FROM staging.customers c

LEFT JOIN customer_metrics m
    ON c.customer_id = m.customer_id;
