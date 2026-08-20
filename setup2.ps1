# ===== SAME 3 VALUES AS BEFORE =====
$PROJECT_ID   = "db-agent-jy-20260820"
$PG_PASSWORD  = "<YOUR_PASSWORD>"
$RO_PASSWORD  = "<YOUR_PASSWORD>"
# ===================================

$REGION   = "us-central1"
$INSTANCE = "db-agent-pg-jy"
$DBNAME   = "agentdb"

gcloud config set project $PROJECT_ID

Write-Host "[0/5] Verifying billing..."
$billing = gcloud billing projects describe $PROJECT_ID --format="value(billingEnabled)"
if ($billing -ne "True") {
    Write-Host "STOP: billing is not enabled on this project. Do STEP A and B first."
    exit 1
}
Write-Host "Billing OK."

Write-Host "[1/5] Enabling APIs (2-3 min)..."
gcloud services enable aiplatform.googleapis.com sqladmin.googleapis.com `
  run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com `
  secretmanager.googleapis.com
if ($LASTEXITCODE -ne 0) { Write-Host "STOP: API enable failed."; exit 1 }

Write-Host "[2/5] Creating Cloud SQL instance (5-10 min)..."
gcloud sql instances create $INSTANCE `
  --database-version=POSTGRES_16 `
  --edition=ENTERPRISE `
  --tier=db-f1-micro `
  --region=$REGION `
  --storage-size=10GB `
  --no-backup
if ($LASTEXITCODE -ne 0) { Write-Host "STOP: instance creation failed."; exit 1 }

Write-Host "[3/5] Creating database and setting admin password..."
gcloud sql users set-password postgres --instance=$INSTANCE --password=$PG_PASSWORD
gcloud sql databases create $DBNAME --instance=$INSTANCE

Write-Host "[4/5] Storing read-only password in Secret Manager..."
$tmp = [System.IO.Path]::GetTempFileName()
[System.IO.File]::WriteAllText($tmp, $RO_PASSWORD, [System.Text.UTF8Encoding]::new($false))
gcloud secrets describe pg-ro-password 2>$null | Out-Null
if ($LASTEXITCODE -eq 0) {
    gcloud secrets versions add pg-ro-password --data-file="$tmp"
} else {
    gcloud secrets create pg-ro-password --data-file="$tmp"
}
Remove-Item $tmp -Force

Write-Host "[5/5] Writing .env and local credentials..."
$CONN = (gcloud sql instances describe $INSTANCE --format="value(connectionName)").Trim()

$envText = @"
GCP_PROJECT=$PROJECT_ID
GCP_LOCATION=$REGION
INSTANCE_CONNECTION_NAME=$CONN
DB_NAME=$DBNAME
DB_ADMIN_USER=postgres
DB_ADMIN_PASSWORD=$PG_PASSWORD
DB_RO_USER=agent_ro
DB_RO_PASSWORD=$RO_PASSWORD
"@
[System.IO.File]::WriteAllText("$PWD\.env", $envText, [System.Text.UTF8Encoding]::new($false))

gcloud auth application-default login

Write-Host ""
Write-Host "DONE."
Write-Host "Instance connection name: $CONN"
Write-Host "Next: gcloud sql connect $INSTANCE --user=postgres --database=$DBNAME"