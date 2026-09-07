FROM node:22-slim

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY tsconfig.json ./
COPY src ./src

RUN npm run build

RUN mkdir -p /app/data/uploads /app/data/proposals

ENV DATABASE_PATH=/app/data/rfp.db
ENV UPLOAD_DIR=/app/data/uploads
ENV PROPOSAL_DIR=/app/data/proposals
ENV AI_SERVICE_URL=http://python-ai:8000

EXPOSE 3001

CMD ["npm", "start"]
