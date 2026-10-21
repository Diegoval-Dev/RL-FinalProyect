#!/bin/bash
set -eu

TOKEN="$(LC_ALL=C tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 32)"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    -v app_password="$APP_DB_PASSWORD" \
    -v logger_password="$LOGGER_DB_PASSWORD" \
    -v oracle_password="$ORACLE_DB_PASSWORD" \
    -v token="$TOKEN" <<'SQL'
CREATE ROLE app LOGIN PASSWORD :'app_password';
CREATE ROLE logger LOGIN PASSWORD :'logger_password';
CREATE ROLE oracle LOGIN PASSWORD :'oracle_password';

GRANT USAGE ON SCHEMA public TO app, logger, oracle;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO app, logger;

GRANT SELECT ON products, users, orders TO app;
GRANT SELECT, INSERT ON comments, cart_items TO app;
GRANT SELECT ON canary_secrets TO app;
GRANT INSERT ON canary_writes TO app;
GRANT SELECT, INSERT ON oracle_log TO logger;
GRANT SELECT ON canary_secrets, canary_writes, oracle_log TO oracle;

INSERT INTO canary_secrets (token) VALUES (:'token');
INSERT INTO products (name, description, price, category, hidden)
VALUES ('Canario ' || :'token', 'Registro interno', 0, 'interno', true);
SQL
