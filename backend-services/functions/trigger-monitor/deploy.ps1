
# Set your variables
$PROJECT_ID = "ai-coco"
$REGION = "us-west1"
$AGENT_ID = "YOU_MUST_SET_THIS" # <--- Replace with your actual Agent ID
$TRIGGER_BUCKET = "ai-coco.firebasestorage.app" # <--- Your Firebase Storage Bucket Name

Write-Host "Deploying Cloud Function: trigger-monitor-agent (Eventarc GCS Trigger)..."

gcloud functions deploy trigger-monitor-agent `
    --gen2 `
    --region=$REGION `
    --runtime=python310 `
    --source=. `
    --entry-point=trigger_monitor_agent `
    --trigger-event-filters="type=google.cloud.storage.object.v1.finalized" `
    --trigger-event-filters="bucket=$TRIGGER_BUCKET" `
    --set-env-vars PROJECT_ID=$PROJECT_ID,LOCATION=$REGION,AGENT_ID=$AGENT_ID

Write-Host "Deployment finished."
