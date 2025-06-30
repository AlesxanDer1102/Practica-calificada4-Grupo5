FROM postgres:15

ENV POSTGRES_DB=pc_db
ENV POSTGRES_USER=postgres
ENV POSTGRES_PASSWORD=12345


COPY pos_db/init.sql /docker-entrypoint-initdb.d/01-init.sql
COPY pos_db/seed_data.sql /docker-entrypoint-initdb.d/02-seed_data.sql


EXPOSE 5432