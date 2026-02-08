from typing import Any, AsyncGenerator, Dict, Optional, Sequence
import uuid
import time
from google.cloud import firestore
from google.adk.sessions import Session, SessionService
from google.adk.types import Event

class FirestoreSessionService(SessionService):
    """A SessionService implementation backed by Google Cloud Firestore."""

    def __init__(self, project_id: str, location: str, database: str = "(default)"):
        """Initializes the FirestoreSessionService.

        Args:
            project_id: The Google Cloud project ID.
            location: The location of the Firestore database (not used by client).
            database: The Firestore database ID.
        """
        self._client = firestore.AsyncClient(project=project_id, database=database)

    async def create_session(
        self,
        session_id: str | None = None,
        user_id: str | None = None,
        app_name: str | None = None,
        parent_session_id: str | None = None,
        session_state: dict[str, Any] | None = None,
    ) -> Session:
        """Creates a new session and persists it to Firestore.

        Path: users/{user_id}/apps/{app_name}/sessions/{session_id}
        """
        if not session_id:
            session_id = str(uuid.uuid4())

        # Default user_id and app_name if not provided (though they should be)
        if not user_id:
            user_id = "default-user"
        if not app_name:
            app_name = "default-app"

        session = Session(
            id=session_id,
            user_id=user_id,
            app_name=app_name,
            parent_session_id=parent_session_id,
            state=session_state or {},
            created_at=time.time(),
            updated_at=time.time(),
        )

        doc_ref = self._client.collection("users").document(user_id) \
                      .collection("apps").document(app_name) \
                      .collection("sessions").document(session_id)

        # Convert session to dict for storage
        # We store only serializable fields
        data = {
            "id": session.id,
            "user_id": session.user_id,
            "app_name": session.app_name,
            "parent_session_id": session.parent_session_id,
            "state": session.state,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
        }

        await doc_ref.set(data)
        return session

    async def get_session(
        self,
        session_id: str,
        user_id: str | None = None,
        app_name: str | None = None
    ) -> Session | None:
        """Retrieves a session from Firestore."""
        # We need user_id and app_name to construct the path.
        # If not provided, we might have to search (inefficient) or rely on provided args.
        # For simplicity and performance, we require user_id and app_name or default them.
        # But wait, original interface only has session_id?
        # No, I updated backend to pass user_id and app_name.

        if not user_id:
            user_id = "default-user" # Should match create time default
        if not app_name:
            app_name = "default-app"

        doc_ref = self._client.collection("users").document(user_id) \
                      .collection("apps").document(app_name) \
                      .collection("sessions").document(session_id)

        doc = await doc_ref.get()
        if not doc.exists:
            return None

        data = doc.to_dict()
        return Session(
            id=data.get("id"),
            user_id=data.get("user_id"),
            app_name=data.get("app_name"),
            parent_session_id=data.get("parent_session_id"),
            state=data.get("state", {}),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    async def list_sessions(
        self,
        user_id: str,
        app_name: str
    ) -> Sequence[Session]:
        """Lists sessions for a user and app."""
        sessions_ref = self._client.collection("users").document(user_id) \
                           .collection("apps").document(app_name) \
                           .collection("sessions")

        docs = sessions_ref.stream()
        sessions = []
        async for doc in docs:
            data = doc.to_dict()
            sessions.append(Session(
                id=data.get("id"),
                user_id=data.get("user_id"),
                app_name=data.get("app_name"),
                parent_session_id=data.get("parent_session_id"),
                state=data.get("state", {}),
                created_at=data.get("created_at"),
                updated_at=data.get("updated_at"),
            ))
        return sessions

    async def delete_session(self, session_id: str, user_id: str, app_name: str) -> None:
        """Deletes a session."""
        doc_ref = self._client.collection("users").document(user_id) \
                      .collection("apps").document(app_name) \
                      .collection("sessions").document(session_id)
        await doc_ref.delete()

    async def update_session(self, session: Session) -> None:
        """Updates session state in Firestore."""
        doc_ref = self._client.collection("users").document(session.user_id) \
                      .collection("apps").document(session.app_name) \
                      .collection("sessions").document(session.id)

        data = {
            "state": session.state,
            "updated_at": time.time()
        }
        await doc_ref.update(data)
