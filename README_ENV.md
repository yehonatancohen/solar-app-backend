# Environments quick guide (testing + prod)

## Windows/WSL setup
- Install Docker Desktop for Windows and enable **WSL 2 backend**.
- Start Docker Desktop before running any `docker` commands.
- Alternatively, use **Ubuntu on WSL** and install Docker Engine inside WSL.
- Verify Docker is up:
  - PowerShell: `docker version`
  - WSL: `service docker status` or `sudo dockerd` (if not using Desktop).

## Commands

### Local testing (backend + DB in Docker)
```bash
cp .env.testing .env
ENV_FILE=.env.testing docker compose --profile testing up --build
# API: http://localhost:8000  |  DB: localhost:5432 (inside compose network use 'db')
```

### Production (customer)
```bash
cp .env.prod .env
ENV_FILE=.env.prod docker compose --profile prod up -d --build
# Set real DATABASE_URL with sslmode=require and real ALLOWED_ORIGINS
```

## CORS
- Testing: `http://localhost:3000,http://127.0.0.1:3000`
- Prod: the customer domain only.

## Database
- testing: Postgres in Docker (`postgresql+psycopg://solar:solar@db:5432/solar`)
- prod: customer Postgres with `?sslmode=require`

## Health checks
- API: `GET /health` → `{"status":"ok"}`
- OpenAPI: `/openapi.json`
