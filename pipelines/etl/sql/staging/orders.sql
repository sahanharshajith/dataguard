DROP TABLE IF EXISTS staging.orders;

CREATE TABLE staging.orders AS
SELECT
    TRY_CAST(order_id AS BIGINT) AS order_id,
    TRY_CAST(customer_id AS BIGINT) AS customer_id,
    TRY_CAST(order_date AS DATE) AS order_date,
    LOWER(TRIM(status)) AS status,
    TRY_CAST(order_total AS DECIMAL(12,2)) AS order_total,
    _batch_id,
    _loaded_at
FROM raw.orders
QUALIFY
    ROW_NUMBER() OVER (
        PARTITION BY order_id ORDER BY _loaded_at DESC
    ) = 1;