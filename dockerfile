# Base image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /SPD_FINALPROJECT-2

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy project dependencies
COPY requirements.txt /SPD_FINALPROJECT-2/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code into the container
COPY . /SPD_FINALPROJECT-2/

# Expose the Flask default port
EXPOSE 5000

# Ensure the SQLite database file is included
COPY smart_neighborhood.db /SPD_FINALPROJECT-2/smart_neighborhood.db

# Command to run the application
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
