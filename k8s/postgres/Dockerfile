FROM postgres:15


COPY pos_db/01-init.sql   /docker-entrypoint-initdb.d/01-init.sql
COPY pos_db/02-seed_data.sql /docker-entrypoint-initdb.d/02-seed_data.sql


EXPOSE 5432