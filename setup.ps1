# ===== EDIT THESE 3 VALUES =====
$PROJECT_ID   = "db-agent-jy-20260820"
$PG_PASSWORD  = "<YOUR_PASSWORD>"
$RO_PASSWORD  = "<YOUR_PASSWORD>"
# ===============================

$ErrorActionPreference = "Stop"

$REGION   = "us-central1"
$INSTANCE = "db-agent-pg"
$DBNAME   = "agentdb"
$SA_NAME  = "db-agent-sa"
$SA_EMAIL = "$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"

Write-Host "[1/8] Logging in..."
gcloud auth login

Write-Host "[2/8] Creating project..."
gcloud projects create $PROJECT_ID
gcloud config set project $PROJECT_ID

Write-Host ""
Write-Host "ACTION REQUIRED: link a billing account to this project, then press Enter."
Write-Host "https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID"
Read-Host "Press Enter when done"

Write-Host "[3/8] Enabling APIs (2-3 min)..."
gcloud services enable aiplatform.googleapis.com sqladmin.googleapis.com `
  run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com `
  secretmanager.googleapis.com

Write-Host "[4/8] Creating Cloud SQL instance (5-10 min)..."
gcloud sql instances create $INSTANCE `
  --database-version=POSTGRES_16 `
  --edition=ENTERPRISE `
  --tier=db-f1-micro `
  --region=$REGION `
  --storage-size=10GB `
  --no-backup

Write-Host "[5/8] Creating database and admin password..."
gcloud sql users set-password postgres --instance=$INSTANCE --password=$PG_PASSWORD
gcloud sql databases create $DBNAME --instance=$INSTANCE

Write-Host "[6/8] Creating service account and granting roles..."
gcloud iam service-accounts create $SA_NAME --display-name="DB Agent"
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SA_EMAIL" --role="roles/aiplatform.user" --quiet
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SA_EMAIL" --role="roles/cloudsql.client" --quiet
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SA_EMAIL" --role="roles/secretmanager.secretAccessor" --quiet

Write-Host "[7/8] Storing read-only password in Secret Manager..."
$tmp = [System.IO.Path]::GetTempFileName()
[System.IO.File]::WriteAllText($tmp, $RO_PASSWORD, [System.Text.UTF8Encoding]::new($false))
gcloud secrets create pg-ro-password --data-file="$tmp"
Remove-Item $tmp -Force

Write-Host "[8/8] Writing .env and setting up local credentials..."
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