FROM python:3.11-slim

# Install system utilities including PostgreSQL client tools & curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy application files
COPY . /app

# Expose web dashboard port
EXPOSE 5050

# Environment settings
ENV PYTHONUNBUFFERED=1

CMD ["python", "app.py"]
