# Simple in-memory session store

sessions = {}

def create_session(user):
    import uuid
    session_id = str(uuid.uuid4())
    sessions[session_id] = user
    return session_id

def get_user(session_id):
    return sessions.get(session_id)