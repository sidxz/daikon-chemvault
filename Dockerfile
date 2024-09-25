# Use the official Python slim base image
FROM python:3.12-slim

# Set the working directory
WORKDIR /project

# Install pipenv and set PIPENV_VENV_IN_PROJECT to create the virtualenv inside the project directory
ENV PIPENV_VENV_IN_PROJECT=1

# Install build dependencies to compile Python packages
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    libxrender1 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Install pipenv first
RUN pip install --no-cache-dir pipenv

# Copy Pipfile and Pipfile.lock to leverage Docker cache
COPY Pipfile Pipfile.lock ./

# Install dependencies without the Pipfile (only from lock file)
#RUN pipenv install --deploy --ignore-pipfile
RUN pipenv install --deploy

# Ensure uvicorn is installed
#RUN pipenv install uvicorn --deploy

# Copy the rest of the application code
COPY . .

# Expose the port
EXPOSE 10001

# Run the application

CMD ["pipenv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10001"]
#CMD ["pipenv", "run", "/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10001"]
# Optional: Clean up cached files to reduce image size
RUN rm -rf /root/.cache
