# Stage 1: dependencies
FROM node:20-slim AS deps
WORKDIR /app

# Enable corepack to use pnpm version from package.json
RUN corepack enable

# Copy dependency manifests
COPY package.json pnpm-lock.yaml* ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# Stage 2: build
FROM deps AS builder
WORKDIR /app

# Copy source files
COPY . .

# Build-time env vars (baked into the build)
ARG NEXT_PUBLIC_API_BASE
ARG NEXT_PUBLIC_WS_BASE
ARG NEXT_PUBLIC_ADMIN_TOKEN
ENV NEXT_PUBLIC_API_BASE=${NEXT_PUBLIC_API_BASE}
ENV NEXT_PUBLIC_WS_BASE=${NEXT_PUBLIC_WS_BASE}
ENV NEXT_PUBLIC_ADMIN_TOKEN=${NEXT_PUBLIC_ADMIN_TOKEN}

# Build the app
RUN pnpm build

# Stage 3: runner
FROM node:20-slim AS runner
WORKDIR /app

# Enable corepack
RUN corepack enable

ENV NODE_ENV=production

COPY package.json pnpm-lock.yaml* ./
RUN pnpm install --prod --frozen-lockfile && chown -R node:node /app

USER node

COPY --from=builder /app/.next ./.next

COPY --from=builder /app/next.config.mjs ./
COPY --from=builder /app/package.json ./

# Runtime env (can be overridden at container run)
ARG NEXT_PUBLIC_API_BASE
ARG NEXT_PUBLIC_WS_BASE
ARG NEXT_PUBLIC_ADMIN_TOKEN
ENV NEXT_PUBLIC_API_BASE=${NEXT_PUBLIC_API_BASE}
ENV NEXT_PUBLIC_WS_BASE=${NEXT_PUBLIC_WS_BASE}
ENV NEXT_PUBLIC_ADMIN_TOKEN=${NEXT_PUBLIC_ADMIN_TOKEN}

EXPOSE 3000

CMD ["pnpm", "start"]
