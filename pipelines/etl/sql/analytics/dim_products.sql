CREATE OR REPLACE TABLE analytics.dim_products AS

WITH 
product_metrics AS (
    SELECT
        i.product_id,
        SUM(i.quantity) AS units_sold
    FROM staging.order_items i
    INNER JOIN analytics.fct_orders o
        ON i.order_id = o.order_id
    WHERE o.is_valid
      AND o.status <> 'cancelled'
    GROUP BY i.product_id
)

SELECT
    p.product_id,
    p.product_name,
    p.category,
    p.unit_price,
    COALESCE(m.units_sold, 0) AS units_sold,
    p._batch_id,
    p._loaded_at
FROM staging.products p

LEFT JOIN product_metrics m
    ON p.product_id = m.product_id;
