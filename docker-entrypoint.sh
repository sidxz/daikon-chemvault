#!/bin/bash

# ANSI color codes for red (error), green (success), yellow (warning), and reset (no color)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Function to print error (in red) and exit on failure
function error_exit {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${RED}$1${NC}" 1>&2
    exit 1
}

# Function to print a message with a timestamp
function log {
    local color=$1
    local message=$2
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${color}${message}${NC}"
}

# Extract DB_HOST and DB_PORT from DATABASE_URL
if [ -z "$DATABASE_URL" ]; then
    error_exit "Error: DATABASE_URL is not set. Please provide a valid database connection string."
fi

# Validate and extract database host and port using regex for better security and precision
DB_HOST=$(echo "$DATABASE_URL" | grep -oP '(?<=@)[^:/]+' || error_exit "Error: Failed to extract DB_HOST from DATABASE_URL")
DB_PORT=$(echo "$DATABASE_URL" | grep -oP '(?<=:)\d+(?=/)' || error_exit "Error: Failed to extract DB_PORT from DATABASE_URL")

# Print the database connection details (optional: remove in production to avoid leaking sensitive data)
log "" "Database Host: $DB_HOST"
log "" "Database Port: $DB_PORT"

# Wait for the database to be ready (PostgreSQL example)
log "" "Waiting for database to be ready..."
until pg_isready -h "$DB_HOST" -p "$DB_PORT"; do
    # Yellow warning message when the database is unavailable
    log "${YELLOW}" "Database is unavailable - sleeping"
    sleep 2
done

# Database ready message in green
log "${GREEN}" "Database is ready!"

# Run Alembic migrations with error handling
log "" "Running Alembic migrations..."
if ! pipenv run alembic upgrade head; then
    error_exit "Error: Alembic migration failed."
fi

# Success message for migration in green
log "${GREEN}" "Alembic migrations completed successfully."

# Start the application
log "" "Starting the application..."
if ! pipenv run uvicorn app.main:app --host 0.0.0.0 --port 10001; then
    error_exit "Error: Failed to start the application with Uvicorn."
fi

# Success message for starting the application in green
log "${GREEN}" "Application started successfully on http://0.0.0.0:10001"
