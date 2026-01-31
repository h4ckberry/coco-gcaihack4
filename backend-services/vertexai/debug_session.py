
import asyncio
from google.adk.sessions.in_memory_session_service import InMemorySessionService

async def main():
    try:
        svc = InMemorySessionService()
        session = await svc.create_session(session_id="test", user_id="user", app_name="app")
        print(f"Session dir: {dir(session)}")
        print(f"Session dict: {session.__dict__}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
