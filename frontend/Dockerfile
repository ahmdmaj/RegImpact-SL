FROM node:20-alpine

WORKDIR /app

# Install dependencies based on lockfile
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Copy application source
COPY frontend/ ./

ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NODE_ENV=production
ENV PORT=3000

# Build Next.js production bundle
RUN npm run build

EXPOSE 3000

CMD ["npm", "start"]
