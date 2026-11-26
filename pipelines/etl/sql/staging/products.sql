DROP TABLE IF EXISTS staging.products;

CREATE TABLE staging.products AS
SELECT
    TRY_CAST(product_id AS BIGINT) AS product_id, -- Converts the product ID into an integer type
    TRIM(product_name) AS product_name, -- Removes leading and trailing spaces
    LOWER(TRIM(category)) AS category, -- Standardizes category names
    CAST(unit_price AS DECIMAL(10, 2)) AS unit_price, -- Converts text prices into decimal format
    _batch_id,
    _loaded_at
FROM raw.products;