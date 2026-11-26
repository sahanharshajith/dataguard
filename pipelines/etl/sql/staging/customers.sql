DROP TABLE IF EXISTS staging.customers;

CREATE TABLE staging.customers AS
SELECT
    TRY_CAST(customer_id AS BIGINT) AS customer_id, -- Converts the customer ID into an integer type
    TRIM(first_name) AS first_name, -- Removes leading and trailing spaces
    TRIM(last_name) AS last_name, -- Removes leading and trailing spaces
    LOWER(TRIM(email)) AS email, -- Standardizes email addresses
    UPPER(TRIM(country)) AS country,
    TRY_CAST(signup_date AS DATE) AS signup_date, -- Converts text dates into dates
    _batch_id,
    _loaded_at
FROM raw.customers;
