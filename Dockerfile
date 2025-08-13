FROM python:3.10-slim

# Install dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy application code
WORKDIR /app
COPY . /app

# Expose port the app runs on
EXPOSE 8000

# By default, set the environment to production
ENV FLASK_ENV=production

# Start the Flask application
CMD ["python", "app.py"]