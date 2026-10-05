FROM postgres:16-alpine

# Environment variables with defaults
ENV POSTGRES_DB=recipedb
ENV POSTGRES_USER=recipeuser
ENV POSTGRES_PASSWORD=recipepassword

# Copy init script into postgresql init directory
COPY init.sql /docker-entrypoint-initdb.d/

EXPOSE 5432
