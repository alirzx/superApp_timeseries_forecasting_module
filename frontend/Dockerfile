FROM node:22-alpine AS build
WORKDIR /src
COPY frontend/package.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build
FROM nginx:1.27-alpine
RUN addgroup -S -g 10001 app && adduser -S -D -u 10001 -G app app
COPY --from=build /src/dist /usr/share/nginx/html
COPY ops/nginx.conf.template /etc/nginx/conf.d/default.conf.template
COPY ops/nginx-entrypoint.sh /entrypoint.sh
RUN rm -f /etc/nginx/conf.d/default.conf && chown -R app:app /usr/share/nginx/html
USER app
EXPOSE 8080
ENTRYPOINT ["/entrypoint.sh"]
