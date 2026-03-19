#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE nova_metadata;
    CREATE DATABASE nova_temporal;
    CREATE DATABASE nova_temporal_visibility;
EOSQL

echo "Postgres databases initialized: nova_metadata, nova_temporal, nova_temporal_visibility"
