import functions_framework
import os
import uuid
import logging
from google.cloud import firestore
from google.cloud import aiplatform_v1
from datetime import datetime
import traceback

# =================================================================
# Configuration & Logging
# =================================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ID = os.environ.get("PROJECT_ID", "ai-coco")
LOCATION = os.environ.get("LOCATION", "us-west1") 
AGENT_ID = os.environ.get("AGENT_ID")

# Firestore Configuration
FIRESTORE_DB = "(default)"
MONITOR_METADATA_COLLECTION = "monitor_metadata"
SESSION_DOC_ID = "current_session"

# Initialize Clients Globally to reuse across invocations
try:
    db = firestore.Client(project=PROJECT_ID, database=FIRESTORE_DB)
except Exception as e:
    logger.error(f"Failed to initialize Firestore Client: {e}")
    db = None

try:
    client_options = {"api_endpoint": f"{LOCATION}-aiplatform.googleapis.com"}
    agent_client = aiplatform_v1.ReasoningEngineExecutionServiceClient(
        client_options=client_options
    )
except Exception as e:
    logger.error(f"Failed to initialize Vertex AI Client: {e}")
    agent_client = None


def _generate_and_save_session(current_month: str) -> str:
    """Helper to generate a fallback UUID and save it to Firestore."""
    session_id = uuid.uuid4().hex[:16]
    logger.warning(f"Generating fallback session ID: {session_id}")
    
    if db:
        try:
            doc_ref = db.collection(MONITOR_METADATA_COLLECTION).document(SESSION_DOC_ID)
            doc_ref.set({
                "session_id": session_id,
                "month": current_month,
                "updated_at": firestore.SERVER_TIMESTAMP
            })
        except Exception as firestore_error:
            logger.warning(f"Failed to save fallback session to Firestore: {firestore_error}")
    
    return session_id


def get_or_create_session(client, agent_name):
    """
    Firestoreから有効なセッションIDを取得するか、
    エージェント経由で新規作成
    """
    if not db:
        return _generate_and_save_session(datetime.now().strftime('%Y%m'))

    doc_ref = db.collection(MONITOR_METADATA_COLLECTION).document(SESSION_DOC_ID)
    current_month = datetime.now().strftime('%Y%m')
    
    try:
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            stored_month = data.get("month")
            stored_session_id = data.get("session_id")
            
            # 当月のセッションIDが存在する場合
            if stored_month == current_month and stored_session_id:
                logger.info(f"Using existing session from Firestore: {stored_session_id}")
                return stored_session_id
    except Exception as e:
        logger.warning(f"Error reading from Firestore: {e}")

    logger.info("Creating new session via Vertex AI Agent...")
    session_id = None
    
    try:
        # エージェントの create_user_session メソッドを呼び出す
        if not client:
             raise Exception("Vertex AI Client not initialized")

        request = aiplatform_v1.QueryReasoningEngineRequest(
            name=agent_name,
            class_method="create_user_session",
            input={"user_id": "monitor-user"} 
        )
        
        response = client.query_reasoning_engine(request=request)
        
        # レスポンスからセッションIDを抽出
        output = response.output
        if hasattr(output, "struct_value"):
            fields = output.struct_value.fields
            if "session_id" in fields:
                session_id = fields["session_id"].string_value
                logger.info(f"New session created: {session_id}")
            elif "error" in fields:
                error_msg = fields["error"].string_value
                logger.error(f"Error from agent: {error_msg}")
        else:
            logger.warning(f"Unexpected response format: {output}")

        if session_id:
            # Firestoreに保存 (Try-Except Added)
            try:
                doc_ref.set({
                    "session_id": session_id,
                    "month": current_month,
                    "updated_at": firestore.SERVER_TIMESTAMP
                })
            except Exception as e:
                logger.warning(f"Failed to save new session to Firestore: {e}")
            
            return session_id
            
    except Exception as e:
        logger.error(f"Error creating session via agent: {e}")
    
    # Fallback if agent creation failed or Firestore save failed (though we return above)
    return _generate_and_save_session(current_month)


@functions_framework.cloud_event
def trigger_monitor_agent(cloud_event):
    """
    CloudEvent Function to trigger Vertex AI Monitor Agent on GCS Object Finalized.
    """
    try:
        data = cloud_event.data

        bucket = data.get("bucket")
        name = data.get("name")

        if not bucket or not name:
            logger.error("Error: Invalid cloud event data")
            return

        if not AGENT_ID:
            logger.error("Error: AGENT_ID environment variable not set.")
            return

        # Construct GCS URI
        image_uri = f"gs://{bucket}/{name}"
        logger.info(f"Processing image: {image_uri}")

        # Use global client
        if not agent_client:
             logger.error("Agent Client is not initialized.")
             return

        # 1. セッションIDを取得または作成
        session_id = get_or_create_session(agent_client, AGENT_ID)
        
        if not session_id:
            logger.error("Error: Failed to obtain session ID")
            return
        
        logger.info(f"Using session ID: {session_id}")
        
        prompt_text = f"Analyze this image: {image_uri}"

        # 2. chat メソッドを呼び出し
        request = aiplatform_v1.QueryReasoningEngineRequest(
            name=AGENT_ID,
            class_method="chat", 
            input={
                "user_input": prompt_text, 
                "session_id": session_id,
                "user_id": "monitor-user"
            }
        )
        
        response = agent_client.query_reasoning_engine(request=request)
        
        # 3. Log Response
        logger.info(f"Agent Response: {response.output}")
        
    except Exception as e:
        logger.exception("Error in trigger_monitor_agent")