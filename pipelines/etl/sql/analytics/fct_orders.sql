CREATE OR REPLACE TABLE analytics.fct_orders AS

WITH 
item_totals AS (
    SELECT
        order_id,
        SUM(line_total) AS items_total,
        COUNT(*) AS item_count
    FROM staging.order_items
    GROUP BY order_id
),

payment_statuses AS (
    SELECT
        order_id,
        MAX(payment_status) AS payment_status
    FROM staging.payments
    GROUP BY order_id
),

order_details AS (
    SELECT
        o.order_id,
        o.customer_id,
        o.order_date,
        o.status,
        o.order_total,
        COALESCE(i.items_total, 0::DECIMAL(12,2))
            AS items_total,
        COALESCE(i.item_count, 0)
            AS item_count,
        p.payment_status,
        o._batch_id,
        o._loaded_at,
        EXISTS (
            SELECT 1
            FROM staging.customers c
            WHERE c.customer_id = o.customer_id
        ) AS customer_exists
    FROM staging.orders o
    LEFT JOIN item_totals i
        ON o.order_id = i.order_id
    LEFT JOIN payment_statuses p
        ON o.order_id = p.order_id
)

SELECT
    order_id,
    customer_id,
    order_date,
    status,
    order_total,
    items_total,
    item_count,
    payment_status,
    COALESCE(
        customer_id IS NOT NULL
        AND customer_exists
        AND order_date IS NOT NULL
        AND order_total > 0
        AND order_total = items_total,
        FALSE
    ) AS is_valid,
    _batch_id,
    _loaded_at

FROM order_details;
