FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Install pipenv
RUN pip install pipenv

# Copy only Pipfile and Pipfile.lock first to leverage Docker cache
COPY Pipfile Pipfile.lock ./

# Install dependencies
RUN pipenv install --deploy --ignore-pipfile

# Copy the rest of the application code
COPY . .

# Run the application
CMD ["pipenv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
