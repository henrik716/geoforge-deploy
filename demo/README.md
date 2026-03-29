# Sykehus — Deploy Kit

Autogenerert fra Waystones · Deployment target: **Fly.io**

## Tjenester

| Tjeneste | Beskrivelse | URL |
|----------|-------------|-----|
| pygeoapi | OGC API – Features | https://sykehus-pygeoapi.fly.dev |
| QGIS Server | WMS kartlag | https://sykehus-qgis.fly.dev/ows/?SERVICE=WMS&REQUEST=GetCapabilities |

## Kom i gang med Fly.io

### Forutsetninger

1. Installer [flyctl](https://fly.io/docs/getting-started/installing-flyctl/)
2. Logg inn: `fly auth login`

### Deploy

```bash
# Første gang — opprett appene
fly launch --config fly.toml --copy-config --no-deploy
fly launch --config fly.qgis.toml --copy-config --no-deploy

# Last opp GeoPackage-data
fly volumes create geodata --region ams --size 1 -a sykehus-pygeoapi
# Kopier filen inn (bruk fly ssh console + scp, eller bak inn i imaget)

# Deploy pygeoapi
fly deploy --config fly.toml

# Deploy QGIS Server
fly deploy --config fly.qgis.toml
```

> **Merk:** `PYGEOAPI_SERVER_URL` og `QGIS_SERVER_SERVICE_URL` er forhåndsutfylt i `fly.toml` / `fly.qgis.toml` basert på det genererte appnavnet. Oppdater disse om du setter opp et eget domene.

### Automatisk deploy

Legg til `FLY_API_TOKEN` som GitHub Secret. GitHub Actions deployer automatisk ved push til main.

Hent token: `fly tokens create deploy -x 999999h`

## Filer

| Fil | Beskrivelse |
|-----|-------------|
| `model.json` | Datamodell (Waystones) |
| `Dockerfile` | pygeoapi container |
| `pygeoapi-config.yml` | OGC API-konfigurasjon |
| `Dockerfile.qgis` | QGIS Server container |
| `project.qgs` | QGIS-prosjekt med lag og stil |
| `fly.toml` | Fly.io-konfigurasjon (pygeoapi) |
| `fly.qgis.toml` | Fly.io-konfigurasjon (QGIS) |
| `.env.template` | Mal for miljøvariabler |
