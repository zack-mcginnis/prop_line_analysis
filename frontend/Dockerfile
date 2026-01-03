# Frontend Dockerfile for Railway deployment
FROM node:18-alpine as builder

WORKDIR /app

# Copy package files
COPY package.json yarn.lock ./

# Install dependencies
RUN yarn install --frozen-lockfile

# Copy source code
COPY . .

# Build the application
RUN yarn build

# Production stage - serve with a lightweight server
FROM node:18-alpine

WORKDIR /app

# Install serve to host static files
RUN npm install -g serve

# Copy built assets from builder
COPY --from=builder /app/dist ./dist

# Expose port (Railway will override with PORT env var)
EXPOSE 3000

# Serve the static files
# Use shell form to allow PORT variable expansion
# -l 0.0.0.0 ensures Railway can reach the service
CMD ["sh", "-c", "serve -s dist -l 0.0.0.0:${PORT:-3000}"]

