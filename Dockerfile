FROM python:3.10-slim

# Install dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy application code
WORKDIR /app
COPY . /app

# Create data directory with proper permissions
RUN mkdir -p /app/data && chmod 755 /app/data

# Ensure proper ownership
RUN chown -R root:root /app && chmod -R 755 /app

# Expose port
EXPOSE 8000

# Set environment to production
ENV FLASK_ENV=production

# Start Flask application
CMD ["python", "app.py"]