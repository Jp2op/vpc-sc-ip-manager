# ---- Build stage ----
FROM node:20-slim AS builder

# Build args — override for different environments
ARG VITE_API_BASE=/llm-blocker/v1
ARG VITE_BASE_PATH=/llm-block/frontend/
ARG VITE_APP_TITLE=LLM Access Manager

ENV VITE_API_BASE=$VITE_API_BASE
ENV VITE_BASE_PATH=$VITE_BASE_PATH
ENV VITE_APP_TITLE=$VITE_APP_TITLE

WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

# ---- Runtime stage ----
FROM nginx:alpine
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 8080
ENTRYPOINT ["/entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
