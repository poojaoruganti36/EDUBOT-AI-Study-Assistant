from datetime import datetime
from pathlib import Path
import json
import uuid


def _normalize_store(data) -> dict:
    if isinstance(data, dict) and "sessions" in data:
        return data

    if isinstance(data, list):
        session_id = str(uuid.uuid4())
        title = infer_session_title(data) or "New chat"
        return {
            "current_session_id": session_id,
            "sessions": [
                {
                    "id": session_id,
                    "title": title,
                    "messages": data,
                    "updated_at": datetime.now().isoformat(),
                }
            ],
        }

    return {"current_session_id": None, "sessions": []}


def load_store(path: Path) -> dict:
    if not path.exists():
        return {"current_session_id": None, "sessions": []}
    try:
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            return {"current_session_id": None, "sessions": []}
        return _normalize_store(json.loads(content))
    except (json.JSONDecodeError, OSError):
        return {"current_session_id": None, "sessions": []}


def save_store(path: Path, store: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store, indent=2, ensure_ascii=False), encoding="utf-8")


def infer_session_title(messages: list[dict]) -> str:
    for message in messages:
        if message.get("role") == "user":
            content = " ".join(message.get("content", "").split())
            if content:
                return content[:48]
    return "New chat"


def is_empty_session(session: dict) -> bool:
    title = (session.get("title") or "").strip()
    messages = session.get("messages", [])
    return not messages and title in {"", "New chat"}


def create_session(title: str = "New chat") -> dict:
    return {
        "id": str(uuid.uuid4()),
        "title": title,
        "messages": [],
        "updated_at": datetime.now().isoformat(),
    }


def upsert_session(store: dict, session_id: str, messages: list[dict]) -> dict:
    sessions = store.get("sessions", [])
    title = infer_session_title(messages)
    updated_at = datetime.now().isoformat()

    for session in sessions:
        if session["id"] == session_id:
            session["messages"] = messages
            session["updated_at"] = updated_at
            if messages:
                session["title"] = title
            break
    else:
        session = create_session(title or "New chat")
        session["id"] = session_id
        session["messages"] = messages
        session["updated_at"] = updated_at
        sessions.insert(0, session)

    sessions = [session for session in sessions if not (session["id"] != session_id and is_empty_session(session))]
    sessions.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
    store["sessions"] = sessions
    store["current_session_id"] = session_id
    return store


def remove_session(store: dict, session_id: str) -> dict:
    sessions = [session for session in store.get("sessions", []) if session["id"] != session_id]
    store["sessions"] = sessions
    if store.get("current_session_id") == session_id:
        store["current_session_id"] = sessions[0]["id"] if sessions else None
    return store


def get_current_session(store: dict) -> dict:
    current_id = store.get("current_session_id")
    for session in store.get("sessions", []):
        if session["id"] == current_id:
            return session

    if store.get("sessions"):
        store["current_session_id"] = store["sessions"][0]["id"]
        return store["sessions"][0]

    session = create_session()
    store["sessions"] = [session]
    store["current_session_id"] = session["id"]
    return session


def load_memory(path: Path) -> list[dict]:
    store = load_store(path)
    return get_current_session(store).get("messages", [])


def save_memory(path: Path, messages: list[dict]) -> None:
    store = load_store(path)
    session = get_current_session(store)
    updated_store = upsert_session(store, session["id"], messages)
    save_store(path, updated_store)


def clear_memory(path: Path) -> None:
    save_store(path, {"current_session_id": None, "sessions": []})


def export_chat_markdown(messages: list[dict], title: str = "EDUBOT Chat History") -> str:
    lines = [f"# {title}", ""]
    for message in messages:
        role = message.get("role", "assistant").title()
        content = message.get("content", "")
        lines.append(f"## {role}")
        lines.append(content)
        lines.append("")
    return "\n".join(lines)
