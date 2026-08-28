# Module: Google Cloud Run Hosting

**Status:** Complete -- verified on ITSMweb (2026-06-13)
**Cost:** Free tier covers light traffic; ~$0-5/month for moderate use
**RAM:** 2Gi (required for LibreOffice); concurrency=1

---

## One-Time Setup (per project)

### 1. Install gcloud CLI

https://cloud.google.com/sdk/docs/install

### 2. Authenticate

```powershell
gcloud auth login
gcloud auth application-default login
```

### 3. Create GCP Project

```powershell
gcloud projects create [PROJECT_ID] --name="[Project Name]"
gcloud config set project [PROJECT_ID]
```

PROJECT_ID must be globally unique. If taken, try `[project]-bp` or `[project]-[initials]`.

### 4. Enable Billing

Go to console.cloud.google.com -> Billing -> Link billing account to project.
Cloud Build requires billing to be enabled (even if cost is zero).

### 5. Enable APIs

```powershell
gcloud services enable cloudbuild.googleapis.com run.googleapis.com artifactregistry.googleapis.com
```

### 6. Grant IAM Permissions

```powershell
$PROJECT_NUM = $(gcloud projects describe [PROJECT_ID] --format='value(projectNumber)')
$COMPUTE_SA = "${PROJECT_NUM}-compute@developer.gserviceaccount.com"

gcloud projects add-iam-policy-binding [PROJECT_ID] `
    --member="serviceAccount:${COMPUTE_SA}" `
    --role="roles/cloudbuild.builds.builder"
gcloud projects add-iam-policy-binding [PROJECT_ID] `
    --member="serviceAccount:${COMPUTE_SA}" `
    --role="roles/storage.objectAdmin"
gcloud projects add-iam-policy-binding [PROJECT_ID] `
    --member="serviceAccount:${COMPUTE_SA}" `
    --role="roles/artifactregistry.writer"
gcloud projects add-iam-policy-binding [PROJECT_ID] `
    --member="serviceAccount:${COMPUTE_SA}" `
    --role="roles/logging.logWriter"
```

### 7. Set Environment Variables on Cloud Run

After first deploy (step below), go to Cloud Run -> [service] -> Edit & Deploy New Revision -> Variables:

```
FLASK_SECRET_KEY=[generate with: python3 -c "import secrets; print(secrets.token_hex(32))"]
FLASK_ENV=production
GMAIL_ADDRESS=[itsmbvf@gmail.com or project-specific address]
GMAIL_APP_PASSWORD=[app password]
AUTH0_DOMAIN=
AUTH0_CLIENT_ID=
AUTH0_CLIENT_SECRET=
GOOGLE_SHEET_ID=[from Google Sheets URL]
GOOGLE_CREDENTIALS_JSON=[full service account JSON, one line]
```

---

## deploy.ps1 Template

```powershell
# deploy.ps1 -- run from project root
$PROJECT_ID = "[YOUR_PROJECT_ID]"
$SERVICE_NAME = "[YOUR_SERVICE_NAME]"
$REGION = "us-central1"

# Commit current state
git add -A
git commit -m "Deploy: $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
git push

# Deploy via Cloud Build (no local Docker required)
gcloud run deploy $SERVICE_NAME `
    --source . `
    --region $REGION `
    --project $PROJECT_ID `
    --allow-unauthenticated `
    --memory 2Gi `
    --concurrency 1

Write-Host "Deployed. URL: https://$(gcloud run services describe $SERVICE_NAME --region $REGION --project $PROJECT_ID --format='value(status.url)')"
```

---

## Dockerfile Template

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libreoffice \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_ENV=production
EXPOSE 8080
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--timeout", "300", "app:create_app()"]
```

---

## .dockerignore Template

```
venv/
env/
.venv/
.env
*.pyc
__pycache__/
.git/
~$*
```

**Never add *.xlsx, *.xlsm, or *.pptx** -- these are reference data committed to git and needed in the container. (P029)

---

## Known Issues

- **First deploy IAM error:** Cloud Build service account needs the 4 roles above. Grant them, then re-deploy.
- **~$WORKBOOK lock file:** Excel creates a `~$WORKBOOK.xlsx` temp file. If git uploads it, gcloud source upload fails. Add `~$*` to .dockerignore and .gitignore.
- **LibreOffice OOM:** If RAM is insufficient, upgrade from 2Gi. Do not downgrade below 2Gi.
