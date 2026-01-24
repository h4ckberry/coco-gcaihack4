from google.adk.agents import BaseAgent, LlmAgent
import google.generativeai as genai
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, PrivateAttr
import json
import datetime

# --- Data Models ---
class BoundingBox(BaseModel):
    ymin: int
    xmin: int
    ymax: int
    xmax: int
    label: str

class ObjectDetail(BaseModel):
    box_2d: List[int]
    label: str

class AgentResponse(BaseModel):
    agent_name: str
    message: str
    found: bool = False
    box_2d: Optional[List[int]] = None
    all_objects: List[ObjectDetail] = []
    data: Optional[Dict[str, Any]] = None

class AnalysisResult(BaseModel):
    found: bool
    box_2d: Optional[List[int]] = None
    label: Optional[str] = None
    message: str
    all_objects: List[ObjectDetail] = []
    transcribed_text: Optional[str] = None
    search_query: Optional[str] = None
    action: Optional[str] = None

# --- Custom Agents using ADK BaseAgent ---

class RealtimeObserver(BaseAgent):
    _model: Any = PrivateAttr()

    def __init__(self, model_name: str = "gemini-3-flash-preview"):
        super().__init__(name="RealtimeObserver")
        self._model = genai.GenerativeModel(model_name)

    # Custom process method (ADK usually uses run/process, we'll keep a consistent interface)
    async def process(self, input_data: Dict[str, Any]) -> AgentResponse:
        print(f"\n [RealtimeObserver] Start")
        query = input_data.get("query", "detect everything")
        print(f"   Input Query: {query}")

        image_content = input_data.get("image_content")
        image_mime = input_data.get("image_mime", "image/jpeg")
        
        # Check for generic query
        is_generic = query.lower() in ["detect everything", "what is in this image?", "describe the main objects in this scene briefly."]
        
        if is_generic:
            prompt = """
            Analyze the image and detect ALL visible objects.
            List every distinct object you see with its bounding box.
            
            Output JSON:
            {
                "found": true,
                "box_2d": null,
                "label": "Multiple Objects",
                "all_objects": [ 
                    { "box_2d": [ymin, xmin, ymax, xmax], "label": "object name" },
                    ...
                ]
            }
            """
        else:
            prompt = f"""
            Analyze the image and find the object: "{query}".
            Also detect ALL other visible objects in the scene.
            
            Output JSON:
            {{
                "found": boolean,
                "box_2d": [ymin, xmin, ymax, xmax] or null (for the target object "{query}"),
                "label": "target object name" or null,
                "all_objects": [ 
                    {{ "box_2d": [ymin, xmin, ymax, xmax], "label": "object name" }},
                    ...
                ]
            }}
            """
        
        try:
            response = self._model.generate_content([
                prompt,
                {"mime_type": image_mime, "data": image_content}
            ])
            
            text = response.text.strip()
            if text.startswith("```json"): text = text[7:-3]
            data = json.loads(text)
            
            result = AgentResponse(
                agent_name=self.name,
                message=f"Found {data.get('label')}" if data.get("found") else "Not found in current view.",
                found=data.get("found", False),
                box_2d=data.get("box_2d"),
                all_objects=[ObjectDetail(**o) for o in data.get("all_objects", [])],
                data=data
            )
            print(f"   Output Found: {result.found}")
            print(f"   Output Message: {result.message}")
            print(f" [RealtimeObserver] End\n")
            return result
        except Exception as e:
            print(f"Observer Error: {e}")
            return AgentResponse(agent_name=self.name, message="Error observing scene.", found=False)

class ContextHistorian(BaseAgent):
    history: List[Dict[str, Any]] = []

    def __init__(self):
        super().__init__(name="ContextHistorian")
        # self.history is already initialized by Pydantic default

    def add_record(self, objects: List[ObjectDetail], timestamp: str):
        print(f" [ContextHistorian] Recording {len(objects)} objects at {timestamp}")
        self.history.append({
            "timestamp": timestamp,
            "objects": [o.label for o in objects]
        })
        if len(self.history) > 50:
            self.history.pop(0)

    async def process(self, input_data: Dict[str, Any]) -> AgentResponse:
        print(f"\n [ContextHistorian] Start")
        query = input_data.get("query", "")
        print(f"   Input Query: {query}")
        
        found_records = []
        for record in reversed(self.history):
            for obj_label in record["objects"]:
                if query in obj_label:
                    found_records.append(record)
        
        if found_records:
            recent = found_records[0]
            result = AgentResponse(
                agent_name=self.name,
                message=f"I remember seeing {query} at {recent['timestamp']}.",
                found=True,
                data={"records": found_records}
            )
        else:
            result = AgentResponse(agent_name=self.name, message=f"No memory of {query}.", found=False)
            
        print(f"   Output Found: {result.found}")
        print(f"   Output Message: {result.message}")
        print(f" [ContextHistorian] End\n")
        return result

class CausalDetective(BaseAgent):
    _model: Any = PrivateAttr()

    def __init__(self, model_name: str = "gemini-flash-latest"):
        super().__init__(name="CausalDetective")
        self._model = genai.GenerativeModel(model_name)

    async def process(self, input_data: Dict[str, Any]) -> AgentResponse:
        print(f"\n [CausalDetective] Start")
        query = input_data.get("query", "")
        print(f"   Input Query: {query}")

        image_content = input_data.get("image_content")
        image_mime = input_data.get("image_mime", "image/jpeg")
        
        prompt = f"""
        User is looking for: "{query}", but it is NOT visible in the image.
        Analyze the scene and infer where it might be hidden or stored.
        Consider containers (drawers, boxes), furniture, or logical locations.
        
        Output JSON:
        {{
            "suggestion": "Detailed suggestion in Japanese on where to look.",
            "reasoning": "Why you think so."
        }}
        """

        try:
            response = self._model.generate_content([
                prompt,
                {"mime_type": image_mime, "data": image_content}
            ])
            
            text = response.text.strip()
            if text.startswith("```json"): text = text[7:-3]
            data = json.loads(text)
            
            result = AgentResponse(
                agent_name=self.name,
                message=data.get("suggestion", "I have no clue."),
                found=False,
                data=data
            )
            print(f"   Output Suggestion: {result.message}")
            print(f" [CausalDetective] End\n")
            return result
        except Exception as e:
            print(f"Detective Error: {e}")
            return AgentResponse(agent_name=self.name, message="Could not reason about the scene.", found=False)

class PhysicalExplorer(BaseAgent):
    def __init__(self):
        super().__init__(name="PhysicalExplorer")

    async def process(self, input_data: Dict[str, Any]) -> AgentResponse:
        print(f"\n [PhysicalExplorer] Start")
        action = input_data.get("action", "")
        print(f"   Input Action: {action}")
        print(f"   [Mock] Executing physical movement...")
        
        result = AgentResponse(
            agent_name=self.name,
            message=f"Moving camera: {action}",
            found=False
        )
        print(f"   Output Message: {result.message}")
        print(f" [PhysicalExplorer] End\n")
        return result
