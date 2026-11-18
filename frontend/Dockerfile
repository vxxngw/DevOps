FROM node:24.22.1-alpine3.24 AS build
WORKDIR /app
COPY package*.json .
RUN npm ci
COPY . .
RUN npm run build
FROM nginx:1.30.6-alpine3.24@sha256:901e593c95dc85f5a729f5765516321366ef4ac401821431d408897e95287d0a
COPY nginx.conf /etc/nginx/nginx.conf
COPY --from=build --chown=nginx:nginx /app/dist /usr/share/nginx/html
USER nginx
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --retries=5 CMD wget -q -O /dev/null http://127.0.0.1:8080/health
