# Deployment Guide

This document covers how to deploy the Real Talk Coach application using Docker Compose and how to set up local development.

## Docker Compose Deployment

The application is containerized into three main services: `backend`, `frontend`, and `nginx`. Nginx acts as a reverse proxy, publishing port 80.

### 1. Environment Setup

Copy the example environment file and fill in the required credentials:

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` with your LeanCloud credentials, DashScope API key, and other required configuration.

#### Nginx Reverse Proxy Configuration
When deploying behind the included Nginx proxy:
- It is recommended to leave `NEXT_PUBLIC_API_BASE` and `NEXT_PUBLIC_WS_BASE` **unset or empty**.
- The frontend client will use same-origin relative paths, which Nginx routes correctly.
- Server-side fetches from the frontend use `API_BASE_INTERNAL`, which is automatically set to `http://backend:8000` in `docker-compose.yml`.

### 2. Deploy

Run the following command to build and start all services in detached mode:

```bash
docker compose up -d --build
```

### 3. Verification

Verify that the services are healthy using these health endpoints:

```bash
# Verify Nginx is up
curl http://localhost/nginx-health

# Verify Backend API is reachable through Nginx
curl http://localhost/api/healthz
```

**Note:** The main application route is `/scenarios`. Accessing the root `/` may return a 404 depending on your configuration.

### 4. Common Operations

```bash
# View logs
docker compose logs -f

# Stop and remove containers
docker compose down

# Restart services
docker compose restart
```

---

## Local Development (VSCode)

If you prefer to run the application locally for debugging:

### Backend
1. Ensure Python 3.11 is installed.
2. Install dependencies:
   ```bash
   cd backend
   uv sync  # or pip install -r requirements.txt
   ```
3. Run with reload:
   ```bash
   uvicorn app.main:app --reload --env-file .env
   ```

### Frontend
1. Ensure Node.js 20+ and pnpm are installed.
2. Install dependencies:
   ```bash
   cd frontend
   pnpm install
   ```
3. Run development server:
   ```bash
   pnpm dev --port 3000
   ```

### VSCode Debugging
- Use the **Python: FastAPI** launch configuration for the backend.
- Use the **Next.js: Client** or **Next.js: Server** launch configurations for the frontend.
