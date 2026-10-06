# EVE Incursions

Tracker for [EVE Online](https://www.eveonline.com/) incursions — live spawn status,
influence history, spawn history, community list and Sansha rat stats. Data is pulled
from CCP's [ESI API](https://esi.evetech.net/).

> **Status: retired.** This project is being sunset and is no longer maintained.
> It is published as-is for anyone who wants to read, fork, or self-host it. I will
> **not** be providing any support, fixes, reviews, or help with setup, and I will not
> be responding to issues or pull requests. You are entirely on your own — please do
> not contact me for assistance. See the [LICENSE](LICENSE) for the (lack of) warranty.

## Architecture

A npm-workspaces monorepo with three services, wired together with Docker Compose:

| Package           | What it is                              | Port (host) |
| ----------------- | --------------------------------------- | ----------- |
| `packages/server` | GraphQL API + ESI scrapers (TypeScript) | `4001`      |
| `packages/ws`     | WebSocket server (push live updates)    | `4003`      |
| `packages/frontend` | Next.js site (SSR)                    | `4002`      |

Backing services: **MariaDB** (`3313` on host) and **Redis** (internal). In production a
[caddy-docker-proxy](https://github.com/lucaslorentz/caddy-docker-proxy) container routes
everything under one host; locally you can hit the services directly or run caddy too.

## Prerequisites

- Docker + Docker Compose
- A root `.env` file (see below)

## Configuration

Create a `.env` in the repo root (it is gitignored):

```env
MYSQL_HOST=mysql
MYSQL_USER=root
MYSQL_PASSWORD=your-db-password
MYSQL_DB=eve-incursions

# GCS HMAC credentials for the database-backup container (production only).
# Used by the `mysql_backup` service via Google's S3-compatible API. Omit for local dev.
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
```

`MYSQL_HOST` is the compose service name (`mysql`) when running in Docker. The `AWS_*`
keys are the HMAC credentials the `mysql_backup` service (see `docker-compose.prod.yml`)
uses to push dumps to a Google Cloud Storage bucket through its S3-compatible endpoint —
they are not needed for local development.

## Run it locally

The base `docker-compose.yml` is the production definition; the dev overlay
`docker-compose.dev.yml` adds the start commands, an `init` step that runs `npm install`,
and published ports.

```bash
# 1. one-time: create the external network the compose files expect
docker network create caddy

# 2. (optional) start the caddy reverse proxy → serves everything on http://localhost
cd caddy && docker compose up -d && cd ..

# 3. bring up the dev stack (installs deps, then starts all services)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

Then open:

- **http://localhost:4002** — the frontend directly, or
- **http://localhost** — via caddy (only if you did step 2)

> Note: hit port **4002** for the frontend. `http://localhost` only works when the caddy
> proxy from step 2 is running.

### Seed the data

A fresh MariaDB starts empty, so the homepage will have nothing to show until it is
populated. `seed/eve-incursions-seed.sql.gz` is a gzipped MariaDB dump of all 11 tables
(systems, spawns, communities, rat stats, etc.), taken on 2026-08-03. It contains only
public EVE/game data — no user data. Pipe it into the running `mysql` container:

```bash
gunzip -c seed/eve-incursions-seed.sql.gz | \
  docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T mysql \
  mariadb -uroot -p"$MYSQL_PASSWORD" eve-incursions
```

## Useful commands

```bash
DC="docker compose -f docker-compose.yml -f docker-compose.dev.yml"

$DC up                       # start everything (foreground)
$DC up -d                    # start detached
$DC logs -f frontend         # tail a service
$DC exec frontend sh         # shell into a container
$DC down                     # stop the stack
```

Server scripts (run inside the `server` container, or from `packages/server`):

| Script                  | Purpose                              |
| ----------------------- | ------------------------------------ |
| `npm start`             | GraphQL API (watch mode)             |
| `npm run scheduler`     | Periodic ESI update jobs             |
| `npm run spawns:update` | One-off: refresh active spawns       |
| `npm run systems:update`| One-off: refresh system data         |
| `npm run sov:update`    | One-off: refresh sovereignty         |
| `npm run rats:update`   | One-off: refresh rat stats           |
| `npm test`              | Vitest                               |

## Production

`docker-compose.yml` + `docker-compose.prod.yml` (and `docker-compose.stage.yml` for
staging) define the deployed stack, routed by the external caddy proxy in `caddy/`.

## Tech stack

Next.js · React · TypeScript · GraphQL · MariaDB · Redis · Docker · Chart.js
