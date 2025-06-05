FROM python:3.11-slim

# Set working directory
WORKDIR /app


# Update OS packages to path CVEs like CVE-2023-45853
RUN apt-get update \
    &&  app-get upgrade -y --no-install-recommends \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
#COPY . .

# Expose Flask Port
#Expose 5000

# Run the application

#CMD ["python", "app.py"]