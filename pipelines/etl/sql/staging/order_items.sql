DROP TABLE IF EXISTS staging.order_items;

CREATE TABLE staging.order_items AS
SELECT 
    TRY_CAST(order_item_id AS BIGINT) AS order_item_id, -- Converts the order item ID into an integer type
    TRY_CAST(order_id AS BIGINT) AS order_id, -- Converts the order ID into an integer type
    TRY_CAST(product_id AS BIGINT) AS product_id, -- Converts the product ID into an integer type
    TRY_CAST(quantity AS INT) AS quantity, -- Converts the quantity into an integer type
    CAST(unit_price AS DECIMAL(10, 2)) AS unit_price, -- Converts text prices into decimal format
    CAST(line_total AS DECIMAL(10, 2)) AS line_total, -- Converts text line totals into decimal format
    _batch_id,
    _loaded_at
FROM raw.order_items;