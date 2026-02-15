
# Set your variables
PROJECT_ID="ai-coco"
REGION="us-west1"
AGENT_ID="projects/166224675513/locations/us-west1/reasoningEngines/1979560734647910400" # <--- Deployed Monitor Agent ID
TRIGGER_BUCKET="ai-coco.firebasestorage.app" # <--- Your Firebase Storage Bucket Name

echo "Deploying Cloud Function: trigger-monitor-agent (Eventarc GCS Trigger)..."

# Determine GCLOUD command
if command -v gcloud &> /dev/null; then
    GCLOUD_CMD="gcloud"
elif command -v gcloud.cmd &> /dev/null; then
    GCLOUD_CMD="gcloud.cmd"
elif command -v gcloud.exe &> /dev/null; then
    GCLOUD_CMD="gcloud.exe"
# Start searching for Windows path
elif [ -f "/mnt/c/Users/o2360/AppData/Local/Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd" ]; then
    GCLOUD_CMD="/mnt/c/Users/o2360/AppData/Local/Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd"
elif [ -f "/mnt/c/Program Files (x86)/Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd" ]; then
    GCLOUD_CMD="/mnt/c/Program Files (x86)/Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd"
else
    echo "Error: gcloud command not found. Please install Google Cloud SDK."
    echo "If installed on Windows, adding it to your PATH might help."
    exit 1
fi

echo "Using gcloud command: $GCLOUD_CMD"

$GCLOUD_CMD functions deploy trigger-monitor-agent \
    --gen2 \
    --region=$REGION \
    --runtime=python310 \
    --source=. \
    --entry-point=trigger_monitor_agent \
    --trigger-event-filters="type=google.cloud.storage.object.v1.finalized" \
    --trigger-event-filters="bucket=$TRIGGER_BUCKET" \
    --timeout=300s \
    --set-env-vars PROJECT_ID=$PROJECT_ID,LOCATION=$REGION,AGENT_ID=$AGENT_ID

echo "Deployment finished."
