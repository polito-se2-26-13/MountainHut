
# ==========================================
# STAGE 1: Build frontend React
# ==========================================
FROM node:22-alpine AS frontend-build

WORKDIR /app/client

# Install frontend dependencies
COPY client/package*.json ./
RUN npm ci --ignore-scripts

# Copy frontend source and build
COPY client/ ./
RUN npm run build


# ==========================================
# STAGE 2: Final image
# ==========================================
FROM python:3.12-slim

WORKDIR /app

# Install Nginx, Supervisor and create application user
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        nginx \
        supervisor \
    && rm -f /etc/nginx/sites-enabled/default \
    && useradd --system \
        --no-create-home \
        --shell /usr/sbin/nologin \
        appuser \
    && rm -rf /var/lib/apt/lists/*

# Install backend dependencies
COPY server/requirements.txt ./server/requirements.txt

RUN pip install --no-cache-dir \
    --only-binary :all: \
    -r server/requirements.txt

# Copy backend source code
COPY server/ ./server/

# Copy compiled frontend
COPY --from=frontend-build \
    /app/client/dist \
    /usr/share/nginx/html

# Configure Nginx
COPY client/nginx/default.conf /etc/nginx/conf.d/default.conf

# Configure Supervisor
COPY deploy/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Configure Nginx for non-root execution

# Configure Nginx for non-root execution
RUN sed -i 's#^[[:space:]]*pid .*;#pid /tmp/nginx.pid;#' /etc/nginx/nginx.conf \
    && sed -i '/^[[:space:]]*user[[:space:]]/d' /etc/nginx/nginx.conf \
    && sed -i 's#^[[:space:]]*error_log .*;#error_log /dev/stderr;#' /etc/nginx/nginx.conf \
    && sed -i 's#^[[:space:]]*access_log .*;#access_log /dev/stdout;#' /etc/nginx/nginx.conf \
    && mkdir -p \
        /data \
        /tmp/nginx/client_body \
        /tmp/nginx/proxy \
        /tmp/nginx/fastcgi \
        /tmp/nginx/uwsgi \
        /tmp/nginx/scgi \
    && chown -R appuser:appuser \
        /app \
        /data \
        /tmp/nginx \
        /var/lib/nginx \
        /usr/share/nginx/html


# Database location
ENV DB_PATH=/data/mountainHut.sqlite

# Python configuration
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Nginx listens on port 8080
EXPOSE 8080

# Run as non-root user
USER appuser

# Apply migrations and start services
CMD ["sh", "-c", "python -m server.scripts.db_setup migrate && exec supervisord -n"]
