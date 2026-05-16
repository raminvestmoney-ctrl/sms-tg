# Use the official Playwright image which includes Python and Browsers
FROM mcr.microsoft.com/playwright/python:v1.41.0-jammy

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (already in the base image, but to be safe)
RUN playwright install chromium

# Copy the rest of the code
COPY . .

# Run the script
CMD ["python", "advanced_traffic_loader.py"]
