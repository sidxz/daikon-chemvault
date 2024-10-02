#!/bin/bash

# Function to print error and exit on failure
function error_exit {
    echo "$1" 1>&2
    exit 1
}

# Extract DB_HOST and DB_PORT from DATABASE_URL
if [ -z "$DATABASE_URL" ]; then
    error_exit "Error: DATABASE_URL is not set. Please provide a valid database connection string."
fi

# Validate and extract database host and port using regex for better security and precision
DB_HOST=$(echo "$DATABASE_URL" | grep -oP '(?<=@)[^:/]+' || error_exit "Error: Failed to extract DB_HOST from DATABASE_URL")
DB_PORT=$(echo "$DATABASE_URL" | grep -oP '(?<=:)\d+(?=/)' || error_exit "Error: Failed to extract DB_PORT from DATABASE_URL")

# Print the database connection details (optional: remove in production to avoid leaking sensitive data)
echo "Database Host: $DB_HOST"
echo "Database Port: $DB_PORT"

# Wait for the database to be ready (PostgreSQL example)
echo "Waiting for database to be ready..."
until pg_isready -h "$DB_HOST" -p "$DB_PORT"; do
    echo "Database is unavailable - sleeping"
    sleep 2
done

echo "Database is ready!"

# Run Alembic migrations with error handling
echo "Running Alembic migrations..."
if ! pipenv run alembic upgrade head; then
    error_exit "Error: Alembic migration failed."
fi
echo "Alembic migrations completed successfully."

# Start the application
echo "Starting the application..."
if ! pipenv run uvicorn app.main:app --host 0.0.0.0 --port 10001; then
    error_exit "Error: Failed to start the application with Uvicorn."
fi
