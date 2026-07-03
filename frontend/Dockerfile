FROM node:22-slim AS build

WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

# PUBLIC_* vars are baked into the client bundle at build time.
ARG PUBLIC_API_BASE_URL=http://localhost:8000
ENV PUBLIC_API_BASE_URL=$PUBLIC_API_BASE_URL

COPY . .
RUN npm run build

FROM node:22-slim
WORKDIR /app
COPY --from=build /app/build ./build
COPY --from=build /app/package.json ./
ENV PORT=3000
EXPOSE 3000
CMD ["node", "build/index.js"]
