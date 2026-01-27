FROM python:3.11-slim
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p /app/json_folder
RUN mkdir -p /app/web/templates  # Ensure templates directory exists

# Copy all files
COPY . .

# Use main.py as entry point
CMD ["python", "main.py"]