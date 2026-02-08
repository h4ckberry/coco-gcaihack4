
import logging
import sys
import os

# Fake Env for testing
os.environ["PROJECT_ID"] = "ai-coco"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "1"

print("--- Starting Verify Logs ---")

try:
    from app.agent_orchestrator import agent_engine
    print("Imported agent_engine")

    # We need to manually call set_up because it is normally called by the Runner
    print("Calling set_up()...")
    agent_engine.set_up()
    print("set_up() finished.")

    # Check logger levels
    print(f"Root logger level: {logging.getLogger().level} (Should be 20/INFO)")
    print(f"App logger level: {logging.getLogger('app').level} (Should be 20/INFO)")
    print(f"Google logger level: {logging.getLogger('google').level} (Should be 30/WARNING)")
    print(f"OpenTelemetry logger level: {logging.getLogger('opentelemetry').level} (Should be 30/WARNING)")

except Exception as e:
    print(f"Error: {e}")

print("--- Verify Logs Finished ---")
