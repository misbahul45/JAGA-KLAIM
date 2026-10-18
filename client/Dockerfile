# syntax=docker/dockerfile:1

FROM node:24-bookworm-slim AS base
COPY --from=oven/bun:1.4.0 /usr/local/bin/bun /usr/local/bin/bun
ENV NEXT_TELEMETRY_DISABLED=1
RUN install -d -o node -g node /app
WORKDIR /app
USER node

FROM base AS deps
COPY --chown=node:node package.json bun.lock ./
RUN --mount=type=cache,target=/home/node/.bun/install/cache,uid=1000,gid=1000 \
    bun install --frozen-lockfile

FROM base AS dev
ENV NODE_ENV=development
COPY --from=deps --chown=node:node /app/node_modules ./node_modules
COPY --chown=node:node . .
RUN mkdir .next
EXPOSE 3000
CMD ["bun", "run", "dev", "-H", "0.0.0.0"]

FROM base AS build
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
COPY --from=deps --chown=node:node /app/node_modules ./node_modules
COPY --chown=node:node . .
RUN bun run build

FROM node:24-bookworm-slim AS runner
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0
RUN install -d -o node -g node /app
WORKDIR /app
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
COPY --from=build --chown=node:node /app/public ./public
USER node
EXPOSE 3000
CMD ["node", "server.js"]
