# Multi-stage build with two runtime targets — `dev` (Vite dev server, hot
# module reload, source mounted as a volume) and `production` (a static
# build served by nginx — no Node.js in the final image at all).

FROM node:20-slim AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

# --- Development target ---
FROM deps AS dev
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# --- Build stage: compiles the production static bundle ---
# Vite inlines VITE_-prefixed env vars into the bundle at build time (they
# can't be changed at container-start like a normal runtime env var), so the
# backend's public URL has to be supplied as a build ARG.
FROM deps AS build
ARG VITE_API_BASE_URL=http://localhost:8000/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
COPY . .
RUN npm run build

# --- Production target: nginx serving the static build, nothing else ---
FROM nginx:1.27-alpine AS production
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q -O- http://localhost:80/ || exit 1
CMD ["nginx", "-g", "daemon off;"]
