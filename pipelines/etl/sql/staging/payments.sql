DROP TABLE IF EXISTS staging.payments;

CREATE TABLE staging.payments AS
SELECT
    TRY_CAST(payment_id AS BIGINT) AS payment_id, -- Converts the payment ID into an integer type
    TRY_CAST(order_id AS BIGINT) AS order_id, -- Converts the order ID into an integer type
    LOWER(TRIM(payment_method)) AS payment_method, -- Standardizes payment method names
    TRY_CAST(amount AS DECIMAL(10, 2)) AS amount, -- Converts text amounts into decimal format
    TRY_CAST(paid_at AS TIMESTAMP) AS paid_at,
    LOWER(TRIM(payment_status)) AS payment_status,
    _batch_id,
    _loaded_at
FROM raw.payments;