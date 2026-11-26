CREATE OR REPLACE TABLE analytics.daily_sales AS

SELECT
    order_date,
    COUNT(*) AS order_count,
    SUM(order_total) AS revenue,
    ROUND(
        SUM(order_total) / COUNT(*),
        2
    ) AS avg_order_value,
    MAX(_batch_id) AS _batch_id,
    MAX(_loaded_at) AS _loaded_at
FROM analytics.fct_orders

WHERE is_valid
  AND status <> 'cancelled'

GROUP BY order_date;
