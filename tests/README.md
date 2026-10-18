# Docker tests

Automated verification for the single-container deployment (see the
[Docker section](../README.md#docker-single-container) in the root README and
[`Dockerfile`](../Dockerfile) / [`docker-compose.yml`](../docker-compose.yml)).

## `docker_smoke_test.sh`

Builds the image, starts it under its own compose project on its own port, and
checks the container end to end. It answers "does this newly built container
actually work?" — for CI, for a fresh VPS, or after changing the Dockerfile.

```bash
tests/docker_smoke_test.sh
```

It exits `0` only if every check passes, `1` if a check fails, `2` if the build
or startup failed (with the relevant log tail printed).

### What it asserts

| Area | Checks |
|---|---|
| Image | `docker-compose build` succeeds |
| Shape | exactly one container; exactly one published port (`8000/tcp`); host port is `${SMOKE_PORT}`; a volume is mounted at `/data` |
| Site | `GET /` and `/menu` return 200 and are **server-rendered** (seeded DB rows appear in the HTML); `window.__MAREA_ALTA_DATA__` is seeded; security headers present; `/docs` is 404 in production mode; a hashed asset is served |
| API | `GET /api/schedule` is a 7-day JSON array |
| Admin | admin created in the container; login returns 303; authenticated `/admin` is 200; a CSRF-protected `PUT /api/schedule/0` returns 200 and shows on the public API |
| Persistence | the SQLite file is on the volume (`/data/marea_alta.db`); after `down` + `up` (volume kept) the saved change **and** the admin account survive |

### Isolation and cleanup

The test uses compose project `marea_alta_smoke` and host port `18080` by
default, so it will not collide with a running production container on `8080`.
It removes its container **and** its volume on exit. Leave it up to poke at it:

```bash
SMOKE_KEEP=1 tests/docker_smoke_test.sh
# then, when done:
docker-compose -p marea_alta_smoke down -v
```

### Configuration

| Variable | Default | Purpose |
|---|---|---|
| `COMPOSE_BIN` | `docker-compose` | Compose command to use (set to `docker compose` wrapper if needed) |
| `SMOKE_PROJECT` | `marea_alta_smoke` | Compose project name (isolates container + volume) |
| `SMOKE_PORT` | `18080` | Host port to publish and test against |
| `SMOKE_ADMIN_USER` | `smokeadmin` | Admin username created during the test |
| `SMOKE_ADMIN_PASS` | `smoke-<timestamp>` | Admin password |
| `SMOKE_KEEP` | `0` | `1` leaves the stack running after the test |

### Requirements

Docker Engine with either `docker-compose` (v1, what this repo targets) or the
`docker compose` plugin, plus `curl`, `awk` and `jq` on the host.
