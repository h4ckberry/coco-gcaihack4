import functions_framework
import os
import uuid
from google.cloud import firestore
from google.cloud import aiplatform_v1
from datetime import datetime

# =================================================================
# Configuration
# =================================================================
PROJECT_ID = os.environ.get("PROJECT_ID", "ai-coco")
LOCATION = os.environ.get("LOCATION", "us-west1") 
AGENT_ID = os.environ.get("AGENT_ID")

# Firestore Configuration
FIRESTORE_DB = "(default)"
MONITOR_METADATA_COLLECTION = "monitor_metadata"
SESSION_DOC_ID = "current_session"

# Initialize Firestore Client (Global to reuse across invocations)
db = firestore.Client(project=PROJECT_ID, database=FIRESTORE_DB)

def get_or_create_session(client, agent_name):
    """
    Firestoreから有効なセッションIDを取得するか、
    エージェント経由で新規作成
    """
    doc_ref = db.collection(MONITOR_METADATA_COLLECTION).document(SESSION_DOC_ID)
    doc = doc_ref.get()
    
    current_month = datetime.now().strftime('%Y%m')
    session_id = None
    
    if doc.exists:
        data = doc.to_dict()
        stored_month = data.get("month")
        stored_session_id = data.get("session_id")
        
        # 当月のセッションIDが存在する場合
        if stored_month == current_month and stored_session_id:
            print(f"Using existing session from Firestore: {stored_session_id}")
            return stored_session_id

    print("Creating new session via Vertex AI Agent...")
    
    try:
        # エージェントの create_user_session メソッドを呼び出す
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
                print(f"New session created: {session_id}")
            elif "error" in fields:
                error_msg = fields["error"].string_value
                print(f"Error from agent: {error_msg}")
                session_id = None
        else:
            print(f"Warning: Unexpected response format: {output}")

        if session_id:
            # Firestoreに保存
            doc_ref.set({
                "session_id": session_id,
                "month": current_month,
                "updated_at": firestore.SERVER_TIMESTAMP
            })
            return session_id
        else:
            # create_user_sessionが失敗した場合のフォールバック
            print("Warning: create_user_session failed, generating simple UUID")
            session_id = uuid.uuid4().hex[:16]
            
            doc_ref.set({
                "session_id": session_id,
                "month": current_month,
                "updated_at": firestore.SERVER_TIMESTAMP
            })
            return session_id
            
    except Exception as e:
        print(f"Error creating session: {e}")
        # エラー時のフォールバック
        session_id = uuid.uuid4().hex[:16]
        print(f"Fallback: Using generated session ID: {session_id}")
        
        try:
            doc_ref.set({
                "session_id": session_id,
                "month": current_month,
                "updated_at": firestore.SERVER_TIMESTAMP
            })
        except Exception as firestore_error:
            print(f"Warning: Failed to save session to Firestore: {firestore_error}")
        
        return session_id


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
            print("Error: Invalid cloud event data")
            return

        if not AGENT_ID:
            print("Error: AGENT_ID environment variable not set.")
            return

        # Construct GCS URI
        image_uri = f"gs://{bucket}/{name}"
        print(f"Processing image: {image_uri}")

        # Initialize client
        client_options = {"api_endpoint": f"{LOCATION}-aiplatform.googleapis.com"}
        client = aiplatform_v1.ReasoningEngineExecutionServiceClient(
            client_options=client_options
        )
        
        # 1. セッションIDを取得または作成
        session_id = get_or_create_session(client, AGENT_ID)
        
        if not session_id:
            print("Error: Failed to obtain session ID")
            return
        
        print(f"Using session ID: {session_id}")
        
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
        
        response = client.query_reasoning_engine(request=request)
        
        # 3. Log Response
        print(f"Agent Response: {response.output}")
        
    except Exception as e:
        print(f"Error in trigger_monitor_agent: {e}")
        import traceback
        traceback.print_exc()