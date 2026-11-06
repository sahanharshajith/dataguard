FROM node:24-alpine

ENV NEXT_TELEMETRY_DISABLED=1

WORKDIR /app

# Install dependencies first so Docker can cache this layer.
COPY package.json package-lock.json ./
RUN npm ci

# Application code
COPY . .

EXPOSE 3000

# Development server.
CMD ["npm", "run", "dev", "--", "--hostname", "0.0.0.0"]