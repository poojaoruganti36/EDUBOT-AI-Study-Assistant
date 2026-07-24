import json
import os
from pathlib import Path
import warnings

from groq import AuthenticationError
import streamlit as st
from dotenv import load_dotenv

import config
from modules.file_utils import build_knowledge_base, extract_text_from_uploads
from modules.llm import ask_llm
from modules.memory_utils import (
    create_session,
    export_chat_markdown,
    get_current_session,
    is_empty_session,
    load_store,
    remove_session,
    save_store,
    upsert_session,
)
from modules.study_tools import (
    create_flashcards,
    create_mind_map,
    create_quiz,
    create_study_pack_markdown,
    mind_map_to_markdown,
    summarize_text,
)
from modules.voice_utils import get_voice_input

warnings.filterwarnings("ignore", category=FutureWarning, module=r"google\..*")

load_dotenv(override=True)

BASE_DIR = Path(__file__).parent
MEMORY_FILE = BASE_DIR / "data" / "memory.json"
STYLE_FILE = BASE_DIR / "assets" / "style.css"


def inject_styles() -> None:
    if STYLE_FILE.exists():
        st.markdown(f"<style>{STYLE_FILE.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def initialize_state() -> None:
    if "memory_store" not in st.session_state:
        st.session_state.memory_store = load_store(MEMORY_FILE)
    current_session = get_current_session(st.session_state.memory_store)
    if "current_session_id" not in st.session_state:
        st.session_state.current_session_id = current_session["id"]
    if "messages" not in st.session_state:
        st.session_state.messages = current_session.get("messages", [])
    if "knowledge_base" not in st.session_state:
        st.session_state.knowledge_base = None
    if "study_result" not in st.session_state:
        st.session_state.study_result = ""
    if "study_format" not in st.session_state:
        st.session_state.study_format = "markdown"
    if "uploaded_sources" not in st.session_state:
        st.session_state.uploaded_sources = []
    if "voice_status" not in st.session_state:
        st.session_state.voice_status = ""
    if "manual_topic" not in st.session_state:
        st.session_state.manual_topic = ""
    if "prompt_input" not in st.session_state:
        st.session_state.prompt_input = ""
    if "pending_prompt" not in st.session_state:
        st.session_state.pending_prompt = None
    if "quiz_items" not in st.session_state:
        st.session_state.quiz_items = []
    if "quiz_submitted" not in st.session_state:
        st.session_state.quiz_submitted = False
    if "quiz_index" not in st.session_state:
        st.session_state.quiz_index = 0
    if "quiz_answers" not in st.session_state:
        st.session_state.quiz_answers = []
    if "quiz_topic" not in st.session_state:
        st.session_state.quiz_topic = ""
    if "flashcard_items" not in st.session_state:
        st.session_state.flashcard_items = []
    if "flashcard_index" not in st.session_state:
        st.session_state.flashcard_index = 0
    if "flashcard_show_back" not in st.session_state:
        st.session_state.flashcard_show_back = False
    if "mind_map_data" not in st.session_state:
        st.session_state.mind_map_data = None
    if "sidebar_selected_session" not in st.session_state:
        st.session_state.sidebar_selected_session = False
    if "raw_text" not in st.session_state:
        st.session_state.raw_text = ""
    if "upload_signature" not in st.session_state:
        st.session_state.upload_signature = ()


def sync_current_session() -> None:
    st.session_state.memory_store = upsert_session(
        st.session_state.memory_store,
        st.session_state.current_session_id,
        st.session_state.messages,
    )
    save_store(MEMORY_FILE, st.session_state.memory_store)


def switch_session(session_id: str) -> None:
    st.session_state.current_session_id = session_id
    current_session = get_current_session(
        {
            "current_session_id": session_id,
            "sessions": st.session_state.memory_store.get("sessions", []),
        }
    )
    st.session_state.messages = current_session.get("messages", [])
    st.session_state.study_result = ""
    st.session_state.quiz_items = []
    st.session_state.quiz_submitted = False
    st.session_state.quiz_topic = ""
    st.session_state.prompt_input = ""
    st.session_state.pending_prompt = None
    st.session_state.voice_status = ""
    st.rerun()


def start_new_chat() -> None:
    session = create_session()
    st.session_state.memory_store["sessions"].insert(0, session)
    st.session_state.memory_store["current_session_id"] = session["id"]
    save_store(MEMORY_FILE, st.session_state.memory_store)
    st.session_state.current_session_id = session["id"]
    st.session_state.messages = []
    st.session_state.study_result = ""
    st.session_state.quiz_items = []
    st.session_state.quiz_submitted = False
    st.session_state.quiz_topic = ""
    st.session_state.prompt_input = ""
    st.session_state.pending_prompt = None
    st.session_state.voice_status = ""
    st.session_state.sidebar_selected_session = False
    st.rerun()


def build_chat_messages(user_prompt: str, context_text: str, learning_goal: str) -> list[dict]:
    system_prompt = f"""
You are {config.APP_NAME}, an intelligent tutoring assistant for students.

Rules:
- Explain clearly and accurately.
- When the user is learning, teach step by step.
- If uploaded context is provided, use it as the main source.
- If the answer is not fully supported by the uploaded context, say so briefly.
- End with a short "Key takeaway" line.

Learning goal from sidebar:
{learning_goal or "General tutoring support"}

Uploaded context:
{context_text or "No uploaded context supplied."}
"""
    recent_messages = st.session_state.messages[-4:]
    return [{"role": "system", "content": system_prompt}, *recent_messages, {"role": "user", "content": user_prompt}]


def _get_upload_signature(uploads: list) -> tuple:
    return tuple((uploaded_file.name, getattr(uploaded_file, "size", 0)) for uploaded_file in uploads or [])


def refresh_uploaded_material(uploads: list) -> None:
    signature = _get_upload_signature(uploads)
    if not uploads:
        st.session_state.upload_signature = ()
        st.session_state.raw_text = ""
        st.session_state.uploaded_sources = []
        st.session_state.knowledge_base = None
        return

    if signature == st.session_state.upload_signature:
        return

    raw_text, sources = extract_text_from_uploads(uploads)
    st.session_state.upload_signature = signature
    st.session_state.raw_text = raw_text
    st.session_state.uploaded_sources = sources
    st.session_state.knowledge_base = build_knowledge_base(raw_text) if sources else None


def render_sidebar() -> tuple[str, list, str]:
    with st.sidebar:
        st.markdown("### 💬 Chats")
        if st.button("✨ New chat", key="new_chat", use_container_width=True, type="primary"):
            start_new_chat()

        sessions = st.session_state.memory_store.get("sessions", [])
        st.caption("Recent")
        for session in sessions[:12]:
            if is_empty_session(session) and session["id"] != st.session_state.current_session_id:
                continue
            label = session.get("title") or "New chat"
            if st.button(
                label,
                key=f"session_{session['id']}",
                use_container_width=True,
                type="secondary" if session["id"] != st.session_state.current_session_id else "primary",
            ):
                st.session_state.sidebar_selected_session = True
                switch_session(session["id"])

        st.markdown("---")
        st.markdown("### 📚 Study Workspace")
        st.caption("Upload notes and set your learning goal.")
        learning_goal = st.text_area(
            "🎯 Learning Goal",
            placeholder="Example: Help me revise biology for exams in simple language.",
        )
        uploads = st.file_uploader(
            "📎 Upload learning material",
            type=["pdf", "txt", "md", "csv", "json", "docx", "pptx", "png", "jpg", "jpeg"],
            accept_multiple_files=True,
            help="Use notes, PDFs, Word files, PowerPoint slides, screenshots, or text files as study context.",
        )

        if st.button("🧹 Clear Chat History", use_container_width=True):
            st.session_state.messages = []
            st.session_state.memory_store = remove_session(st.session_state.memory_store, st.session_state.current_session_id)
            if not st.session_state.memory_store.get("sessions"):
                session = create_session()
                st.session_state.memory_store = {"current_session_id": session["id"], "sessions": [session]}
            st.session_state.current_session_id = st.session_state.memory_store["current_session_id"]
            st.session_state.messages = get_current_session(st.session_state.memory_store).get("messages", [])
            save_store(MEMORY_FILE, st.session_state.memory_store)
            st.success("Chat history cleared.")
            st.rerun()

        if st.session_state.messages:
            current_title = next(
                (
                    session.get("title", "EDUBOT Chat History")
                    for session in sessions
                    if session["id"] == st.session_state.current_session_id
                ),
                "EDUBOT Chat History",
            )
            chat_export = export_chat_markdown(st.session_state.messages, current_title)
            st.download_button(
                "⬇️ Download Chat History",
                data=chat_export,
                file_name="edu_tutor_chat_history.md",
                mime="text/markdown",
                use_container_width=True,
            )

    return os.getenv("AI_API_KEY") or os.getenv("GROQ_API_KEY"), uploads or [], learning_goal


def render_chat() -> None:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    st.markdown('<div id="chat-bottom"></div>', unsafe_allow_html=True)


def scroll_to_bottom() -> None:
    st.markdown(
        """
<script>
    const bottom = window.parent.document.getElementById("chat-bottom");
    if (bottom) {
        bottom.scrollIntoView({ behavior: "smooth", block: "end" });
    }
</script>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state() -> None:
    st.markdown(
        """
<div class="hero-shell">
  <div class="hero-chip">🤖 EDUBOT</div>
  <h1>🤖 EDUBOT</h1>
  <p>Your intelligent study companion for learning, practice, and revision.</p>
  <div class="hero-sub">✨ How can I help you learn today?</div>
</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="quick-actions-title">⚡ Quick actions</div>', unsafe_allow_html=True)


def render_project_header() -> None:
    st.markdown(
        """
<div class="project-header">
  <div class="project-kicker">Intelligent Chatbot for Education and Tutoring</div>
  <h1>EDUBOT - AI Study Assistant</h1>
  <p>Ask questions, upload study material, generate summaries, practice quizzes, flashcards, and mind maps.</p>
</div>
        """,
        unsafe_allow_html=True,
    )


def build_manual_prompt(action: str) -> str:
    prompts = {
        "Explain": "Explain ",
        "Summarize": "Summarize ",
        "Analyze": "Analyze ",
        "Quiz": "Create a quiz about ",
        "Flashcards": "Create flashcards about ",
        "Revision": "Create a quiz and flashcards about ",
    }
    return prompts.get(action, "")


def should_persist_message(message: str) -> bool:
    blocked_prefixes = (
        "AI service authentication failed.",
        "Something went wrong:",
        "Error from LLM:",
    )
    return not message.startswith(blocked_prefixes)


def friendly_error_message(exc: Exception) -> str:
    message = str(exc) or exc.__class__.__name__
    if "AI service is not configured" in message or "API key is missing" in message:
        return "AI service is not configured. Add the API key in the `.env` file, then restart the app."
    if isinstance(exc, AuthenticationError):
        return "AI service authentication failed. Check the API key in the `.env` file, then restart the app."
    return f"Something went wrong: {message}"


def normalize_quiz_value(value: str) -> str:
    return " ".join(str(value).strip().lower().split())


def clear_quiz_response_state(*key_prefixes: str) -> None:
    st.session_state.quiz_answers = []
    st.session_state.quiz_submitted = False
    st.session_state.quiz_index = 0
    prefixes = key_prefixes or ("tools", "chat")
    for prefix in prefixes:
        for idx in range(1, 11):
            choice_key = f"{prefix}_quiz_choice_{idx}"
            if choice_key in st.session_state:
                del st.session_state[choice_key]


def get_answered_quiz_count(key_prefix: str, total: int) -> int:
    return sum(1 for idx in range(1, total + 1) if st.session_state.get(f"{key_prefix}_quiz_choice_{idx}"))


def set_quiz_topic(topic: str) -> None:
    clean_topic = " ".join(str(topic).strip().split())
    st.session_state.quiz_topic = clean_topic[:80] if clean_topic else "Selected study topic"


def handle_study_command(prompt: str, api_key) -> bool:
    normalized = prompt.strip().lower()

    if normalized.startswith("create flashcards"):
        topic = prompt.split("about", 1)[-1].strip() if "about" in normalized else prompt
        st.session_state.flashcard_items = create_flashcards(topic, api_key)
        st.session_state.flashcard_index = 0
        st.session_state.flashcard_show_back = False
        st.session_state.study_format = "flashcards"
        st.session_state.study_result = ""
        st.session_state.quiz_items = []
        clear_quiz_response_state()
        return True

    if normalized.startswith("create a quiz and flashcards"):
        topic = prompt.split("about", 1)[-1].strip() if "about" in normalized else prompt
        st.session_state.flashcard_items = create_flashcards(topic, api_key)
        st.session_state.flashcard_index = 0
        st.session_state.flashcard_show_back = False
        st.session_state.quiz_items = create_quiz(topic, api_key)
        set_quiz_topic(topic)
        clear_quiz_response_state()
        st.session_state.study_format = "quiz"
        st.session_state.study_result = ""
        return True

    if normalized.startswith("create a quiz"):
        topic = prompt.split("about", 1)[-1].strip() if "about" in normalized else prompt
        st.session_state.quiz_items = create_quiz(topic, api_key)
        set_quiz_topic(topic)
        clear_quiz_response_state()
        st.session_state.study_format = "quiz"
        st.session_state.study_result = ""
        st.session_state.flashcard_items = []
        return True

    return False


def process_prompt(prompt: str, learning_goal: str, knowledge_base, api_key) -> None:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        if handle_study_command(prompt, api_key):
            sync_current_session()
            return
    except AuthenticationError as exc:
        reply = friendly_error_message(exc)
        st.session_state.messages.append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"):
            st.error(reply)
        sync_current_session()
        return
    except Exception as exc:
        reply = friendly_error_message(exc)
        st.session_state.messages.append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"):
            st.warning(reply)
        sync_current_session()
        return

    context_text = ""
    if knowledge_base:
        context_text = knowledge_base["retriever"](prompt)

    reply = None
    with st.chat_message("assistant"):
        with st.spinner("Thinking through the answer..."):
            try:
                reply = ask_llm(build_chat_messages(prompt, context_text, learning_goal), api_key=api_key)
            except AuthenticationError as exc:
                reply = friendly_error_message(exc)
                st.error(reply)
            except Exception as exc:
                reply = friendly_error_message(exc)
                st.warning(reply)

        if reply:
            st.markdown(reply)

    if reply and should_persist_message(reply):
        st.session_state.messages.append({"role": "assistant", "content": reply})
    sync_current_session()


def set_prepared_prompt(action: str) -> None:
    st.session_state.pending_prompt = build_manual_prompt(action)


def render_interactive_quiz(key_prefix: str = "tools") -> None:
    if not st.session_state.quiz_items:
        return

    total = len(st.session_state.quiz_items)
    topic = st.session_state.get("quiz_topic") or "Selected study topic"
    answered = get_answered_quiz_count(key_prefix, total)

    st.markdown("## Quiz Challenge")
    st.caption(f"Topic: {topic}")
    st.progress(answered / total if total else 0)
    st.caption(f"Progress: {answered}/{total} questions answered.")

    if not st.session_state.quiz_submitted:
        st.markdown(f"**Choose the correct answer for all {total} questions, then submit.**")
        for idx, item in enumerate(st.session_state.quiz_items, start=1):
            st.markdown(f"**Q{idx}. {item.get('question', 'Question')}**")
            options = item.get("options", [])
            if not options:
                st.warning("This question has no options. Please regenerate the quiz.")
                continue
            st.radio(
                f"Choose the correct answer for question {idx}",
                options,
                key=f"{key_prefix}_quiz_choice_{idx}",
                index=None,
                label_visibility="collapsed",
            )
            st.markdown("")

        if st.button("Submit Quiz", key=f"{key_prefix}_submit_quiz", use_container_width=True):
            answers = []
            missing = []
            for idx, item in enumerate(st.session_state.quiz_items, start=1):
                selected = st.session_state.get(f"{key_prefix}_quiz_choice_{idx}")
                if not selected:
                    missing.append(idx)
                answers.append(
                    {
                        "question": item.get("question", ""),
                        "selected": selected or "No answer selected",
                        "correct": item.get("answer", ""),
                        "explanation": item.get("explanation", ""),
                    }
                )

            if missing:
                st.warning(f"Please answer all questions before submitting. Missing: {', '.join(map(str, missing))}")
            else:
                st.session_state.quiz_answers = answers
                st.session_state.quiz_submitted = True
                st.rerun()

    if st.session_state.quiz_submitted:
        score = sum(
            1
            for answer in st.session_state.quiz_answers
            if normalize_quiz_value(answer["selected"]) == normalize_quiz_value(answer["correct"])
        )
        percent = (score / total) * 100 if total else 0
        st.markdown("### Quiz Performance")
        metric_col1, metric_col2, metric_col3 = st.columns(3)
        metric_col1.metric("Score", f"{score}/{total}")
        metric_col2.metric("Accuracy", f"{percent:.0f}%")
        if percent >= 80:
            feedback = "Excellent work. You understood this topic really well."
        elif percent >= 50:
            feedback = "Good effort. A quick revision pass will make this stronger."
        else:
            feedback = "Keep going. Review the answers below and try again."
        metric_col3.metric("Level", "Strong" if percent >= 80 else "Growing")
        st.info(feedback)

        for idx, answer in enumerate(st.session_state.quiz_answers, start=1):
            st.markdown(f"**Q{idx}. {answer['question']}**")
            is_correct = normalize_quiz_value(answer["selected"]) == normalize_quiz_value(answer["correct"])
            if is_correct:
                st.success(f"Correct answer: {answer['correct']}")
            else:
                st.error(f"Incorrect. Correct answer: {answer['correct']}")
            st.write(f"Your answer: {answer['selected']}")
            if answer["explanation"]:
                st.caption(answer["explanation"])

        if st.button("Play Again", key=f"{key_prefix}_quiz_restart", use_container_width=True):
            clear_quiz_response_state(key_prefix)
            st.rerun()


def render_flashcards(key_prefix: str = "tools") -> None:
    if not st.session_state.flashcard_items:
        return

    total = len(st.session_state.flashcard_items)
    idx = st.session_state.flashcard_index
    item = st.session_state.flashcard_items[idx]
    title = "Back" if st.session_state.flashcard_show_back else "Front"
    body = item.get("back", "") if st.session_state.flashcard_show_back else item.get("front", "")
    visual_emoji, visual_label = get_flashcard_visual(item.get("front", ""), item.get("back", ""))

    st.markdown("### Flashcards")
    progress_col1, progress_col2 = st.columns([3, 1])
    progress_col1.progress((idx + 1) / total)
    progress_col2.markdown(f"**{idx + 1}/{total}**")
    st.markdown(
        f"""
<div class="flashcard-shell">
  <div class="flashcard-top">
    <div class="flashcard-label">{title}</div>
    <div class="flashcard-visual">
      <div class="flashcard-emoji">{visual_emoji}</div>
      <div class="flashcard-visual-label">{visual_label}</div>
    </div>
  </div>
  <div class="flashcard-body">{body}</div>
</div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Previous", key=f"{key_prefix}_flash_prev", use_container_width=True, disabled=idx == 0):
            st.session_state.flashcard_index -= 1
            st.session_state.flashcard_show_back = False
            st.rerun()
    with col2:
        if st.button("Flip", key=f"{key_prefix}_flash_flip", use_container_width=True):
            st.session_state.flashcard_show_back = not st.session_state.flashcard_show_back
            st.rerun()
    with col3:
        if st.button("Next", key=f"{key_prefix}_flash_next", use_container_width=True, disabled=idx == total - 1):
            st.session_state.flashcard_index += 1
            st.session_state.flashcard_show_back = False
            st.rerun()


def render_mind_map() -> None:
    mind_map = st.session_state.mind_map_data
    if not mind_map:
        return

    st.markdown("### Mind Map")
    topic = mind_map.get("topic", "Mind Map")
    st.markdown(f"#### {topic}")

    columns = st.columns(2)
    branches = mind_map.get("branches", [])
    for idx, branch in enumerate(branches):
        with columns[idx % 2]:
            points = "".join(f"<li>{point}</li>" for point in branch.get("points", []))
            st.markdown(
                f"""
<div class="mindmap-card">
  <div class="mindmap-title">{branch.get('title', 'Branch')}</div>
  <ul>{points}</ul>
</div>
                """,
                unsafe_allow_html=True,
            )

    st.download_button(
        "⬇️ Download Mind Map",
        data=mind_map_to_markdown(mind_map),
        file_name="edubot_mind_map.md",
        mime="text/markdown",
    )


def get_flashcard_visual(front: str, back: str) -> tuple[str, str]:
    text = f"{front} {back}".lower()
    mapping = [
        (("plant", "photosynthesis", "leaf", "chlorophyll"), ("🌿", "Biology")),
        (("heart", "cell", "blood", "human body"), ("🫀", "Life Science")),
        (("graph", "algorithm", "data", "search", "tree"), ("🧠", "Computer Science")),
        (("planet", "star", "gravity", "black hole", "space"), ("🌌", "Space")),
        (("equation", "triangle", "algebra", "geometry", "math"), ("📐", "Mathematics")),
        (("war", "revolution", "history", "empire", "king"), ("🏛️", "History")),
        (("atom", "energy", "force", "motion", "physics"), ("⚛️", "Physics")),
        (("map", "country", "climate", "earth"), ("🗺️", "Geography")),
        (("poem", "novel", "story", "author", "literature"), ("📚", "Literature")),
        (("money", "market", "trade", "economics"), ("💹", "Economics")),
    ]
    for keywords, visual in mapping:
        if any(keyword in text for keyword in keywords):
            return visual
    return "🎓", "Study Card"


def render_quick_actions() -> None:
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button(
            "🧠 Explain a topic\nExplain black holes in simple terms",
            key="quick_explain",
            use_container_width=True,
            type="secondary",
        ):
            set_prepared_prompt("Explain")

    with col2:
        if st.button(
            "📝 Summarize notes\nSummarize this chapter into 5 key points",
            key="quick_summarize",
            use_container_width=True,
            type="secondary",
        ):
            set_prepared_prompt("Summarize")

    with col3:
        if st.button(
            "🎯 Build revision tools\nCreate a quiz and flashcards from your topic",
            key="quick_revision",
            use_container_width=True,
            type="secondary",
        ):
            set_prepared_prompt("Revision")


def main() -> None:
    st.set_page_config(page_title=config.APP_NAME, page_icon="📘", layout="wide")
    inject_styles()
    initialize_state()

    api_key, uploads, learning_goal = render_sidebar()
    refresh_uploaded_material(uploads)

    knowledge_base = st.session_state.knowledge_base
    raw_text = st.session_state.raw_text

    render_project_header()
    chat_tab, tools_tab, about_tab = st.tabs(["💬 Tutor Chat", "🧪 Study Tools", "ℹ️ Project Info"])

    with chat_tab:
        if not st.session_state.messages:
            render_empty_state()
            render_quick_actions()
        render_chat()
        if st.session_state.messages:
            scroll_to_bottom()

        if st.session_state.study_format == "quiz" and st.session_state.quiz_items:
            render_interactive_quiz("chat")
        elif st.session_state.study_format == "flashcards" and st.session_state.flashcard_items:
            st.info("Open the Study Tools tab to interact with the generated flashcards.")
        elif st.session_state.study_format == "mindmap" and st.session_state.mind_map_data:
            st.info("Open the Study Tools tab to interact with the generated mind map.")

        if st.session_state.uploaded_sources:
            st.caption(f"Loaded files: {', '.join(st.session_state.uploaded_sources)}")

        if st.session_state.voice_status:
            st.caption(st.session_state.voice_status)

        if st.session_state.pending_prompt is not None:
            st.session_state.prompt_input = st.session_state.pending_prompt
            st.session_state.pending_prompt = None

        composer_col1, composer_col2, composer_col3 = st.columns([1, 10, 1])
        with composer_col1:
            mic_clicked = st.button("🎤", key="voice_input", type="primary", use_container_width=True)
        with composer_col2:
            st.text_input(
                "Ask a question, request an explanation, or use your uploaded material...",
                key="prompt_input",
                label_visibility="collapsed",
                placeholder="Ask a question, request an explanation, or use your uploaded material...",
            )
        with composer_col3:
            send_clicked = st.button("➤", key="send_prompt", type="primary", use_container_width=True)

        if mic_clicked:
            try:
                spoken_prompt = get_voice_input()
                if spoken_prompt:
                    st.session_state.voice_status = f"Heard: {spoken_prompt}"
                    st.session_state.pending_prompt = spoken_prompt
                else:
                    st.session_state.voice_status = "Voice input not captured."
            except Exception:
                st.session_state.voice_status = "Voice input not available on this device."

        if send_clicked:
            prompt = st.session_state.prompt_input.strip()
            if prompt:
                process_prompt(prompt, learning_goal, knowledge_base, api_key)
                st.session_state.pending_prompt = ""
                st.rerun()

    with tools_tab:
        st.subheader("Generate Study Material")
        source_text = st.text_area(
            "Paste text to summarize or analyze",
            value=raw_text[:4000] if raw_text else "",
            height=240,
            placeholder="Paste notes, articles, textbook paragraphs, or upload files from the sidebar.",
        )

        col1, col2, col3, col4 = st.columns(4)
        if col1.button("Summarize", key="tools_summarize", use_container_width=True):
            try:
                st.session_state.study_result = summarize_text(source_text, "summary", api_key)
                st.session_state.quiz_items = []
                clear_quiz_response_state()
                st.session_state.flashcard_items = []
                st.session_state.mind_map_data = None
            except AuthenticationError:
                st.session_state.study_result = "AI service authentication failed. Check the `.env` file and try again."
            except Exception as exc:
                st.session_state.study_result = friendly_error_message(exc)
            st.session_state.study_format = "markdown"
        if col2.button("Analyze", key="tools_analyze", use_container_width=True):
            try:
                st.session_state.study_result = summarize_text(source_text, "analysis", api_key)
                st.session_state.quiz_items = []
                clear_quiz_response_state()
                st.session_state.flashcard_items = []
                st.session_state.mind_map_data = None
            except AuthenticationError:
                st.session_state.study_result = "AI service authentication failed. Check the `.env` file and try again."
            except Exception as exc:
                st.session_state.study_result = friendly_error_message(exc)
            st.session_state.study_format = "markdown"
        if col3.button("Make Quiz", key="tools_quiz", use_container_width=True):
            try:
                st.session_state.quiz_items = create_quiz(source_text, api_key)
                set_quiz_topic(source_text[:80] if source_text.strip() else "Selected study topic")
                clear_quiz_response_state()
                st.session_state.study_result = ""
                st.session_state.flashcard_items = []
                st.session_state.mind_map_data = None
            except AuthenticationError:
                st.session_state.study_result = "AI service authentication failed. Check the `.env` file and try again."
            except Exception as exc:
                st.session_state.study_result = friendly_error_message(exc)
            st.session_state.study_format = "quiz"
        if col4.button("Make Flashcards", key="tools_flashcards", use_container_width=True):
            try:
                st.session_state.flashcard_items = create_flashcards(source_text, api_key)
                st.session_state.flashcard_index = 0
                st.session_state.flashcard_show_back = False
                st.session_state.study_result = ""
                st.session_state.quiz_items = []
                clear_quiz_response_state()
                st.session_state.mind_map_data = None
            except AuthenticationError:
                st.session_state.study_result = "AI service authentication failed. Check the `.env` file and try again."
            except Exception as exc:
                st.session_state.study_result = friendly_error_message(exc)
            st.session_state.study_format = "flashcards"
        if st.button("🧭 Make Mind Map", key="tools_mindmap", use_container_width=True):
            try:
                st.session_state.mind_map_data = create_mind_map(source_text, api_key)
                st.session_state.study_result = ""
                st.session_state.flashcard_items = []
                st.session_state.quiz_items = []
                clear_quiz_response_state()
            except AuthenticationError:
                st.session_state.study_result = "AI service authentication failed. Check the `.env` file and try again."
                st.session_state.mind_map_data = None
            except Exception as exc:
                st.session_state.study_result = friendly_error_message(exc)
                st.session_state.mind_map_data = None
            st.session_state.study_format = "mindmap"

        if st.session_state.study_format == "quiz" and st.session_state.quiz_items:
            render_interactive_quiz("tools")
        elif st.session_state.study_format == "flashcards" and st.session_state.flashcard_items:
            render_flashcards("tools")
        elif st.session_state.study_format == "mindmap" and st.session_state.mind_map_data:
            render_mind_map()
        elif st.session_state.study_result:
            st.markdown("### Result")
            if st.session_state.study_format == "json":
                st.code(st.session_state.study_result, language="json")
            else:
                st.markdown(st.session_state.study_result)

            study_pack = create_study_pack_markdown(
                source_text=source_text,
                result_text=st.session_state.study_result,
                sources=st.session_state.uploaded_sources,
            )
            st.download_button(
                "Download Study Pack",
                data=study_pack,
                file_name="edu_tutor_study_pack.md",
                mime="text/markdown",
            )

    with about_tab:
        st.subheader("What This Project Includes")
        st.markdown(
            """
This mini project is designed for education and tutoring use cases:

- ChatGPT-style tutoring answers
- Summaries and deeper analysis for pasted text
- Uploaded file support for PDFs, notes, screenshots, and text files
- Quiz and flashcard generation
- Downloadable study packs and chat history
- Local conversation memory

Run it locally with:
```bash
streamlit run edututor_app.py
```
            """
        )


if __name__ == "__main__":
    main()
