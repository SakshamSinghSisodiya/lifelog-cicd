FROM nginxinc/nginx-unprivileged:1.27-alpine

ARG APP_VERSION=dev
ARG GIT_COMMIT=dev
ARG BUILD_NUMBER=dev
LABEL app.version=${APP_VERSION} app.commit=${GIT_COMMIT} app.build=${BUILD_NUMBER}

# Static assets come from the single source of truth in the Flask app
COPY app/static /usr/share/nginx/html/static
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1:8080/nginx-health || exit 1
