FROM node:24.18.0-bookworm-slim AS base
WORKDIR /workspace
RUN corepack enable

COPY package.json pnpm-workspace.yaml pnpm-lock.yaml tsconfig.base.json eslint.config.mjs .prettierrc.json .prettierignore .nvmrc ./
COPY apps ./apps
COPY packages ./packages

RUN corepack pnpm install --frozen-lockfile

WORKDIR /workspace/apps/reviewer
EXPOSE 3001
USER node
CMD ["sh", "-lc", "corepack pnpm exec next dev --hostname 0.0.0.0 --port 3001"]
