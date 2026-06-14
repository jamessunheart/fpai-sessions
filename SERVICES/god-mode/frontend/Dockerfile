# Build Stage
FROM node:18-alpine as build

WORKDIR /app
COPY package*.json ./

# Ensure we get all dependencies (including dev for vite build)
RUN npm install

COPY . .
RUN npm run build

# Verify build output (for debugging logs)
RUN ls -la dist/

# Production Stage
FROM nginx:alpine

# Install apache2-utils for htpasswd
RUN apk add --no-cache apache2-utils

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

EXPOSE 80
CMD ["/entrypoint.sh"]
