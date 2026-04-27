# Slim Python image for production
FROM python:3.12-slim

# Environment variables to prevent Python from buffering output and writing bytecode 
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Create working directory
WORKDIR /app    

# Install system dependencies for psycopg2 and other packages
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
# Note: in production the .env file will be removed, for local testing it can be used to set environment variables
COPY . .

# Expose the port the app runs on
EXPOSE 5000

# Command to run the application with Gunicorn, using 4 workers and a timeout of 120 seconds. Logs are sent to stdout and stderr.
CMD ["gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "4", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "src.main:app"]