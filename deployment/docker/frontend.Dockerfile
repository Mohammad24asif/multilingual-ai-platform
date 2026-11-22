# syntax=docker/dockerfile:1
# STATUS: written but NOT built or run in the authoring sandbox (no Docker there).
FROM node:22-alpine AS build
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json* ./
# Use `npm ci` once package-lock.json is committed (run `npm install` once on your machine to create it).
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM nginx:1.27-alpine
COPY deployment/docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /web/dist /usr/share/nginx/html
EXPOSE 80
