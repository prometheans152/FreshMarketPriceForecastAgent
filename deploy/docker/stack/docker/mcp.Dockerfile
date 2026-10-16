FROM node:22-alpine
WORKDIR /app
COPY mcp/package.json mcp/package-lock.json ./
RUN npm ci --omit=dev --ignore-scripts --no-audit --no-fund
COPY mcp/src ./src
ENV NODE_ENV=production NODE_OPTIONS=--max-old-space-size=110 TZ=Asia/Taipei
EXPOSE 9000
CMD ["node", "src/main.mjs"]
