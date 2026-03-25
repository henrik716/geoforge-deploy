# fmedata — Deploy Kit

Autogenerert fra Waystones · Deployment target: **Railway**

## Tjenester

| Tjeneste | Beskrivelse | URL |
|----------|-------------|-----|
| pygeoapi | OGC API – Features | https://\<app\>.up.railway.app |
| QGIS Server | WMS/WFS kartlag | https://<qgis-service>.up.railway.app/ows/?SERVICE=WMS&REQUEST=GetCapabilities |

## Kom i gang med Railway

### Steg

1. Gå til [railway.app](https://railway.app) og opprett en konto
2. Klikk **"New Project"** → **"Deploy from GitHub Repo"**
3. Velg dette repoet
4. Railway oppdager `Dockerfile` automatisk og starter deploy

### Miljøvariabler

Sett disse under **Variables** i Railway dashboard:

| Variabel | Verdi |
|----------|-------|
| `PYGEOAPI_SERVER_URL` | `https://<din-app>.up.railway.app` (kopier fra Railway dashboard) |
| `QGIS_SERVER_PUBLIC_URL` | `https://<qgis-service>.up.railway.app/ows/` |
| `POSTGRES_HOST` | *(din verdi)* |
| `POSTGRES_PORT` | *(din verdi)* |
| `POSTGRES_DB` | *(din verdi)* |
| `POSTGRES_USER` | *(din verdi)* |
| `POSTGRES_PASSWORD` | *(din verdi)* |
| `POSTGRES_SCHEMA` | *(din verdi)* |
| `OUTPUT_DIR` | *(din verdi)* |
| `SYNC_INTERVAL_SECONDS` | *(din verdi)* |
| `DOWNLOAD_PORT` | *(din verdi)* |

> **Merk:** Railway setter `PORT` automatisk — ikke overstyr denne.

### QGIS Server (WMS/WFS)

Railway deployer én tjeneste per repo som standard. For å kjøre QGIS Server i tillegg:

1. Klikk **"+ New"** → **"GitHub Repo"** i samme prosjekt
2. Velg dette repoet igjen
3. Under **Settings → Build**, sett Dockerfile path til `Dockerfile.qgis`
4. Under **Settings → Deploy**, sett health check path til `/ows/?SERVICE=WMS&REQUEST=GetCapabilities` og timeout til **300s**
5. Bekreft at porten vises som **80** under **Settings → Networking**

### Automatisk deploy

Railway deployer automatisk ved push til main. Ingen GitHub Actions nødvendig.

## Delta-eksport (Automatisert)

Delta-eksporten kjører automatisk i bakgrunnen og håndterer **inserts, updates og deletes**.

> **Note:** **Oppdatering krever en timestamp-kolonne.** Hvis ingen timestamp-kolonne er konfigurert i Waystones (Kilde → lagkobling), spores kun inserts og deletes — endringer i eksisterende features eksporteres ikke.

### Slik fungerer det

**Første kjøring:** alltid full eksport — alle features skrives til `<lag>_full.gpkg` og gjeldende PKer lagres i `.delta_state.json`.

**Manuell kjøring:**
```bash
python delta_export.py          # full eksport, nullstiller state
python delta_export.py --since last         # delta siden siste kjøring
python delta_export.py --since 2024-01-01   # delta siden en bestemt dato
```

## Filer

| Fil | Beskrivelse |
|-----|-------------|
| `model.json` | Datamodell (Waystones) |
| `Dockerfile` | pygeoapi container |
| `pygeoapi-config.yml` | OGC API-konfigurasjon |
| `Dockerfile.qgis` | QGIS Server container |
| `project.qgs` | QGIS-prosjekt med lag og stil |
| `railway.json` | Railway-konfigurasjon (pygeoapi) |
| `railway.qgis.json` | Railway-konfigurasjon (QGIS Server) |
| `.env.template` | Mal for miljøvariabler |
| `delta_export.py` | Script for inkrementell GeoPackage-eksport |
| `nginx-stac.conf` | Nginx-konfigurasjon med riktige MIME-typer |

## STAC Catalog

| Ressurs | URL |
|---------|-----|
| Root Catalog | https://<downloads-url>/stac/catalog.json |
| Collection | https://<downloads-url>/stac/collections/5qects4/collection.json |
| zones items | https://<downloads-url>/stac/zones/catalog.json |

Items skrives automatisk av `delta_export.py` ved siden av hver `.gpkg`-eksport.
