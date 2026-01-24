import os
import json
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False, # Disable credentials to allow wildcard origin
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Gemini
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("Warning: GOOGLE_API_KEY not found in environment variables.")

genai.configure(api_key=GOOGLE_API_KEY)

from google.adk.agents import LlmAgent
from agents import RealtimeObserver, ContextHistorian, CausalDetective, PhysicalExplorer, AgentResponse, ObjectDetail, AnalysisResult
import datetime
import json

# Initialize Agents
observer = RealtimeObserver()
historian = ContextHistorian()
detective = CausalDetective()
explorer = PhysicalExplorer()

# Orchestrator Agent (using ADK LlmAgent)
# We use LlmAgent to handle the intent classification and transcription
orchestrator = LlmAgent(
    name="Orchestrator",
    model="gemini-3-flash-preview",
    instruction="""
    You are the Orchestrator of an object finding system.
    Your task is to:
    1. Transcribe the user's Japanese audio.
    2. Extract the search query.
    3. Determine the intent: "search" or "move".
    
    Output JSON:
    {
        "transcription": "...",
        "query": "...",
        "intent": "search" | "move"
    }
    """
)

# Direct model instance for multi-modal operations
orchestrator_model = genai.GenerativeModel("gemini-3-flash-preview")

@app.post("/analyze", response_model=AnalysisResult)
async def analyze_image_and_audio(
    image: UploadFile = File(...),
    audio: Optional[UploadFile] = File(None), # Audio is optional for re-scan
    is_subsequent_run: bool = Form(False),
    previous_query: str = Form(None)
):
    try:
        # Read files
        image_content = await image.read()
        image_mime = image.content_type if image.content_type != "application/octet-stream" else "image/jpeg"
        
        # Determine Query and Intent
        if is_subsequent_run and previous_query:
            # Re-scan mode: Use previous query, Intent is implicitly "search"
            query = previous_query
            intent = "search"
            transcription = "(Re-scan)"
            print(f"\n [Orchestrator] Re-scan for query: {query}")
        else:
            # First run: Process Audio
            if not audio:
                 raise HTTPException(status_code=400, detail="Audio is required for first run")
            
            audio_content = await audio.read()
            audio_mime = audio.content_type if audio.content_type != "application/octet-stream" else "audio/webm"

            # --- 1. Orchestrator: Transcribe & Understand Intent ---
            print(f"\n [Orchestrator] Start Analysis")
            
            intent_prompt = """
            You are the Orchestrator.
            The user is speaking in **Japanese**.
            1. Transcribe the user's audio strictly in Japanese. Do NOT translate to English.
            2. Extract the search query (what they are looking for) in Japanese.
            3. Determine the intent: "search" (looking for object) or "move" (change view, e.g. "look right").
            
            Output JSON:
            {
                "transcription": "...",
                "query": "...",
                "intent": "search" | "move" | "other"
            }
            """
            
            # Direct model call for multi-modal input
            orch_response = orchestrator_model.generate_content([
                intent_prompt,
                {"mime_type": audio_mime, "data": audio_content}
            ])
            
            try:
                orch_text = orch_response.text.strip()
                if orch_text.startswith("```json"): orch_text = orch_text[7:-3]
                orch_data = json.loads(orch_text)
            except:
                orch_data = {"transcription": "", "query": "", "intent": "search"}
                
            transcription = orch_data.get("transcription", "")
            query = orch_data.get("query", "")
            intent = orch_data.get("intent", "search")
            
            print(f"   Transcription: {transcription}")
            print(f"   Intent: {intent}")
            print(f"   Query: {query}")

        final_result = AnalysisResult(
            found=False,
            message="",
            transcribed_text=transcription,
            search_query=query,
            all_objects=[]
        )

        # --- 2. Execute based on Intent ---
        
        if intent == "move":
            print(f" [Orchestrator] Routing to PhysicalExplorer")
            # Call Physical Explorer
            agent_res = await explorer.process({"action": transcription})
            final_result.message = agent_res.message
            
        else: # Default to search
            print(f" [Orchestrator] Routing to RealtimeObserver")
            # A. Realtime Observer (Check NOW)
            obs_res = await observer.process({
                "image_content": image_content,
                "image_mime": image_mime,
                "query": query
            })
            
            # Save to History (only if found or first run? Let's save all for now)
            historian.add_record(obs_res.all_objects, datetime.datetime.now().strftime("%H:%M:%S"))
            
            final_result.all_objects = obs_res.all_objects
            
            if obs_res.found:
                # Found immediately!
                print(f" [Orchestrator] Object found by Observer")
                final_result.found = True
                final_result.box_2d = obs_res.box_2d
                final_result.label = obs_res.data.get("label")
                final_result.message = f"ありました！{obs_res.data.get('label')}です。"
            else:
                # Not found immediately.
                found_in_history = False
                
                # B. Context Historian (Check PAST) - Skip if subsequent run
                if not is_subsequent_run:
                    print(f" [Orchestrator] Object not found. Routing to ContextHistorian")
                    hist_res = await historian.process({"query": query})
                    if hist_res.found:
                         print(f" [Orchestrator] Object found in History")
                         final_result.message = f"今は見えませんが、{hist_res.message} (記憶)"
                         found_in_history = True
                
                if not found_in_history:
                    print(f" [Orchestrator] Not in history. Routing to CausalDetective")
                    # C. Causal Detective (Infer)
                    det_res = await detective.process({
                        "image_content": image_content,
                        "image_mime": image_mime,
                        "query": query
                    })
                    final_result.message = f"見つかりません。{det_res.message}"
                    
                    # If Detective suggests a location, trigger wait_and_scan
                    # Simple heuristic: if message contains "見て" or "確認", assume suggestion
                    if "見て" in det_res.message or "確認" in det_res.message:
                        final_result.action = "wait_and_scan"
        
        print(f" [Orchestrator] Analysis Complete\n")
        return final_result

    except Exception as e:
        print(f"Error in analyze endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

import firebase_utils

@app.post("/monitor")
async def monitor_environment(
    image: UploadFile = File(...)
):
    try:
        print(f"\n [Monitor] Received monitoring request")
        # Read file
        image_content = await image.read()
        image_mime = image.content_type if image.content_type != "application/octet-stream" else "image/jpeg"
        print(f"   Image size: {len(image_content)} bytes")
        
        print(f" [Monitor] Start Periodic Analysis")
        
        # Use RealtimeObserver to detect objects
        obs_res = await observer.process({
            "image_content": image_content,
            "image_mime": image_mime,
            "query": "what is in this image?"
        })
        print(f"   Observer found: {obs_res.found}, Label: {obs_res.data.get('label')}")
        
        # Save to Firestore
        metadata = {
            "found": obs_res.found,
            "label": obs_res.data.get("label"),
            "box_2d": obs_res.box_2d,
            "message": obs_res.message,
            "all_objects": obs_res.all_objects
        }
        
        try:
            firebase_utils.save_monitoring_data(image_content, metadata)
            print(f"   Saved to Firebase")
        except Exception as fb_err:
            print(f"   Firebase Error: {fb_err}")
        
        print(f" [Monitor] Analysis Complete. Found: {len(obs_res.all_objects)} objects.")
        
        return {"status": "success", "objects_count": len(obs_res.all_objects)}

    except Exception as e:
        print(f" [Monitor] Error: {e}")
        return {"status": "error", "detail": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
