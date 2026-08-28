# deploy.ps1 -- Cloud Run deployment script
# Run from project root: .\deploy.ps1
# Requirements: gcloud CLI installed and authenticated

$PROJECT_ID = "YOUR_PROJECT_ID"   # e.g. "myproject-bp"
$SERVICE_NAME = "YOUR_SERVICE_NAME" # e.g. "myproject"
$REGION = "us-central1"

Write-Host "Deploying $SERVICE_NAME to Cloud Run..."

# Commit current state
git add -A
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm"
git commit -m "Deploy: $timestamp" --allow-empty

# Update PROJECT_STATE.md authoritative registry (edit this line to match project)
# (Claude will handle this update during deployment sessions)

git push

# Deploy via Cloud Build -- no local Docker required
gcloud run deploy $SERVICE_NAME `
    --source . `
    --region $REGION `
    --project $PROJECT_ID `
    --allow-unauthenticated `
    --memory 2Gi `
    --concurrency 1

# Print production URL
$url = gcloud run services describe $SERVICE_NAME --region $REGION --project $PROJECT_ID --format="value(status.url)"
Write-Host "Deployed successfully."
Write-Host "Production URL: $url"
