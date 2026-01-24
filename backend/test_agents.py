import sys
import os

# Add current directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from agents import RealtimeObserver, ContextHistorian, CausalDetective, PhysicalExplorer, AnalysisResult
    print("Successfully imported agents and AnalysisResult.")

    print("Initializing RealtimeObserver...")
    obs = RealtimeObserver()
    print("RealtimeObserver initialized.")

    print("Initializing ContextHistorian...")
    hist = ContextHistorian()
    print("ContextHistorian initialized.")

    print("Initializing CausalDetective...")
    det = CausalDetective()
    print("CausalDetective initialized.")

    print("Initializing PhysicalExplorer...")
    exp = PhysicalExplorer()
    print("PhysicalExplorer initialized.")

    print("ALL AGENTS INITIALIZED SUCCESSFULLY.")

except Exception as e:
    print(f"CRITICAL ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
