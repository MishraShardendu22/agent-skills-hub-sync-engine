---
name: docker-first-architecture
scope: generic
description: >-
  Rules, architectures, multi-stage Dockerfile blueprints, and container-first workflows for all microservices, frontends, and backends targeting container registries, AWS ECS/EKS, and self-hosting.
---

# Docker-First & Image-First Architecture Skill

This skill defines the official architectural guidelines, containerization blueprints, and publishing standards across all services. It enforces a **Docker-First and Image-First** doctrine to guarantee infrastructure portability from serverless/PaaS edge environments to cloud container platforms (AWS ECS/EKS) and sovereign self-hosting.

---

## 1. Overview & Objective

Every service—regardless of language or framework—must be fully containerized, reproducible, and ready for container registry publication (`<registry-user>/<image-name>`).

### Portability Roadmap
1. **Phase 1 (Edge/PaaS)**: Edge/serverless frontends, containerized backends, managed/serverless PostgreSQL, container registry.
2. **Phase 2 (Cloud Native)**: Cloud Infrastructure as Code (Terraform, ECS Fargate / EKS, Load Balancers, CloudFront, Container Registry).
3. **Phase 3 (Sovereign Infrastructure)**: Self-Hosted Bare Metal / VPS (Docker Compose / Nomad / K3s, reverse proxy, automated backup sync).

---

## 2. Core Directives & Toolchain Standards

> [!IMPORTANT]
> **OPTIMAL TOOLCHAIN MANDATE**: Always employ the fastest, most deterministic tools:
> - **Node.js / TypeScript**: `pnpm` exclusively, pinned through the `packageManager` field in `package.json` with its sha512 (`corepack use pnpm@<version>` writes `pnpm@<version>+sha512.<hex>`) and installed with `corepack install`, which refuses a tarball with another hash. Never use `npm` or legacy `yarn`.
> - **Python**: `uv` exclusively, from a pinned `ghcr.io/astral-sh/uv:<version>` image declared as a named stage (`FROM ghcr.io/astral-sh/uv:<version> AS uv`) so its pin is one line to update. Never use plain `pip` or slow virtualenv setups.
> - **Go**: Static compilation (`CGO_ENABLED=0`, `-ldflags="-w -s"`). Never deploy dynamic glibc-dependent Go binaries, and use pure-Go drivers (for SQLite, `modernc.org/sqlite`, not the cgo-only `mattn/go-sqlite3`, which compiles to a stub without cgo).
> - **Pinned bases**: never use moving tags such as `latest` or `golang:alpine`; pin to a release series (`alpine:3.24`, `node:22.23-alpine3.24`, `python:3.12-slim-trixie`, the Go builder at the `go.mod` toolchain release) and update them in the weekly dependency check.
> - **Static Frontends (Preact / Svelte / React)**: Multi-stage `pnpm` builder with `nginx:alpine` runner.

### Mandatory Container Hardening Rules:
1. **Multi-Stage Builds**: Build tooling, SDKs, and source compilers MUST NEVER exist in the production runtime stage.
2. **Non-Root Execution**: Every runtime image MUST define and execute as an unprivileged user (`nextjs`, `appuser`, `workeruser`).
3. **Healthcheck Directives**: Every service image MUST include an active `HEALTHCHECK` probing its readiness endpoint on `127.0.0.1` (busybox `wget` resolves `localhost` to `::1` first, which fails for IPv4-only servers) and on the port the service actually reads from its environment.
4. **Minimal Attack Surface**: Base runtime stages on `alpine:3.24`, `python:3.12-slim-trixie`, or `distroless`.
5. **Context Efficiency**: Every project MUST contain a `.dockerignore` pruning `node_modules`, `.git`, test artifacts, and caches.
6. **Automated Container Registry**: Every repository SHOULD include a GitHub Actions workflow building and publishing multi-arch (`linux/amd64`, `linux/arm64`) images with SBOM and provenance attestations: to GHCR (`ghcr.io/<owner>/<image-name>`) with the built-in `GITHUB_TOKEN`, and to Docker Hub (`<registry-user>/<image-name>`) when its credentials are configured.
7. **Run What You Build**: CI MUST start the built images (for example a Docker Compose smoke test that waits for every health endpoint) instead of only building them.
8. **No Default Secrets**: Compose files read secrets from an uncommitted `.env` (template in a committed `.env.example`) and use `${VAR:?message}` for required ones; never ship fallback secret values. Publish database ports on `127.0.0.1` only.

---

## 3. Technology Blueprints

### Blueprint A: Next.js Standalone (Node 22 + pnpm)
- `next.config.ts` must set `output: "standalone"`.
- The base stage copies `package.json` and runs `corepack enable && corepack install`, so pnpm comes from `packageManager`.
- Multi-stage build copies `.next/standalone`, `.next/static`, and `public`.
- Runs as `nextjs:nodejs` on port 3000.

### Blueprint B: Static SPAs (Vite / Preact / Svelte + Nginx)
- Builds static assets to `dist/` with `pnpm build`.
- Deploys into `nginx:alpine`.
- Custom `nginx.conf` handles SPA routing fallback (`try_files $uri $uri/ /index.html;`), gzip compression, and `/health`.

### Blueprint C: Go API / Microservice
- Builder `FROM --platform=$BUILDPLATFORM golang:<go.mod toolchain>-alpine<version>` with `go mod download`, so multi-arch builds cross-compile natively instead of under QEMU.
- Static cross-compilation: `ARG TARGETOS` / `ARG TARGETARCH`, then `CGO_ENABLED=0 GOOS=$TARGETOS GOARCH=$TARGETARCH go build -ldflags="-w -s" -o /bin/<name> ./cmd/<name>`.
- Runtime stage: `alpine:3.24` with `ca-certificates`, `tzdata`, `curl`, running as `appuser`; a program that uses relative data paths gets a `WORKDIR` it can write to.

### Blueprint D: Python AI / API Service (FastAPI + uv)
- Installs `uv` from a pinned `ghcr.io/astral-sh/uv:<version>` stage.
- `uv sync --frozen --no-dev --no-install-project` with `UV_COMPILE_BYTECODE=1`, `UV_PYTHON=/usr/local/bin/python3` and `UV_PYTHON_DOWNLOADS=never`, so the virtualenv is built on the interpreter the runtime stage also has. Keep `.python-version` equal to the image's Python.
- Runtime stage: `python:3.12-slim-trixie` with unprivileged `appuser`.

---

## 4. Verification & Testing Runbook

```bash
# 1. Validate Docker daemon is operational
docker info

# 2. Build image locally with Buildx
docker build -t <service-name>:local .

# 3. Test local container execution & healthcheck
docker run -d --name test-<service-name> -p <port>:<port> <service-name>:local
sleep 5
docker ps --filter name=test-<service-name>
curl -f http://localhost:<port>/health || exit 1
docker rm -f test-<service-name>

# 4. Verify Compose environment
cp .env.example .env   # fill in the required secrets
docker compose up -d --wait
docker compose ps
docker compose down

# 5. Multi-arch build check (cross-compiling Go builders need no QEMU)
docker buildx build --platform linux/amd64,linux/arm64 -f <service>/Dockerfile .
```
