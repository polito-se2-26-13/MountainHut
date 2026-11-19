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

# Install Nginx and Supervisor
RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx supervisor \
    && rm -f /etc/nginx/sites-enabled/default \
    && rm -rf /var/lib/apt/lists/*

# Install backend dependencies
COPY server/requirements.txt ./server/requirements.txt
RUN pip install --no-cache-dir --only-binary :all: -r server/requirements.txt

# Copy backend source code
COPY server/ ./server/

# Copy compiled frontend from stage 1
COPY --from=frontend-build /app/client/dist /usr/share/nginx/html

# Configure Nginx
COPY client/nginx/default.conf /etc/nginx/conf.d/default.conf

# Configure Supervisor
COPY deploy/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# The app runs as an unprivileged user: nginx keeps its pid, temporary files and logs
# in folders of that user, and the database folder belongs to it
RUN useradd --system --no-create-home --uid 10001 mountainhut \
    && sed -i -e '/^user /d' -e 's#^pid .*#pid /tmp/nginx.pid;#' /etc/nginx/nginx.conf \
    && mkdir -p /data \
    && chown -R mountainhut:mountainhut /data /var/lib/nginx /var/log/nginx

# Database location
ENV DB_PATH=/data/mountainHut.sqlite

# Nginx listens on port 80 (Docker lets a normal user open ports below 1024 inside a container)
EXPOSE 80

USER mountainhut

# Apply database migrations and start both services
CMD ["sh", "-c", "python -m server.scripts.db_setup migrate && exec supervisord -n -c /etc/supervisor/conf.d/supervisord.conf"]
