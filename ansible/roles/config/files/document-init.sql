-- der-control-api gets its own database in this container, not the `document`
-- database device-api owns — a second Hibernate ddl-auto=update tenant in
-- device-api's schema would be an ownership hazard. Mirrors the cloud's
-- dedicated Aurora "dercontrol" slice. docker-entrypoint-initdb.d runs this
-- once on a fresh volume (arcnode is the POSTGRES_USER, so it's a superuser
-- here and can CREATE DATABASE).
CREATE DATABASE dercontrol;
