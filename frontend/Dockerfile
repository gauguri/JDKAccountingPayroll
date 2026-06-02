FROM node:20-slim

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .

EXPOSE 3000
# Dev server with API proxy to the backend (see vite.config.ts).
CMD ["npm", "run", "dev"]
