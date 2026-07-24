from datetime import datetime
from difflib import SequenceMatcher
from typing import Optional

from modules.llm import ask_llm, extract_json_from_text


def _fallback_quiz(topic: str) -> list[dict]:
    topic_label = topic.strip() or "the selected topic"
    if "cricket" in topic_label.lower():
        return [
            {
                "question": "How many players are there in one cricket team on the field?",
                "options": ["7", "9", "11", "15"],
                "answer": "11",
                "explanation": "A cricket team has 11 players.",
            },
            {
                "question": "What is the main object a batter tries to protect in cricket?",
                "options": ["The boundary rope", "The stumps", "The pitch roller", "The scoreboard"],
                "answer": "The stumps",
                "explanation": "The batter protects the stumps while trying to score runs.",
            },
            {
                "question": "What is a six in cricket?",
                "options": [
                    "Six balls bowled by one bowler",
                    "A hit that crosses the boundary without bouncing",
                    "Six wickets taken in a match",
                    "A tie between two teams",
                ],
                "answer": "A hit that crosses the boundary without bouncing",
                "explanation": "A ball hit over the boundary on the full scores six runs.",
            },
            {
                "question": "What is an over in cricket?",
                "options": ["3 legal balls", "4 legal balls", "6 legal balls", "10 legal balls"],
                "answer": "6 legal balls",
                "explanation": "One over normally contains six legal deliveries.",
            },
            {
                "question": "Which format is usually the shortest official cricket format?",
                "options": ["Test", "ODI", "T20", "First-class"],
                "answer": "T20",
                "explanation": "T20 matches have 20 overs per side, making them shorter than ODIs and Tests.",
            },
        ]

    return [
        {
            "question": f"What is the best first step when learning about {topic_label}?",
            "options": [
                "Understand the basic meaning and key terms",
                "Memorize random facts without context",
                "Avoid examples completely",
                "Start with the hardest advanced problem",
            ],
            "answer": "Understand the basic meaning and key terms",
            "explanation": "A strong foundation makes the rest of the topic easier to understand.",
        },
        {
            "question": f"Why are examples useful when studying {topic_label}?",
            "options": [
                "They connect ideas to real situations",
                "They replace all explanations",
                "They make practice unnecessary",
                "They remove the need to revise",
            ],
            "answer": "They connect ideas to real situations",
            "explanation": "Examples help turn abstract information into something easier to remember.",
        },
        {
            "question": f"Which method is most helpful for checking understanding of {topic_label}?",
            "options": [
                "Answering practice questions",
                "Only rereading the title",
                "Ignoring difficult points",
                "Skipping revision",
            ],
            "answer": "Answering practice questions",
            "explanation": "Practice questions reveal what you understand and what needs more review.",
        },
        {
            "question": f"What should you do if a concept in {topic_label} feels confusing?",
            "options": [
                "Break it into smaller parts",
                "Stop studying the topic forever",
                "Guess without reviewing",
                "Only copy definitions",
            ],
            "answer": "Break it into smaller parts",
            "explanation": "Breaking a hard idea into smaller steps makes it easier to learn.",
        },
        {
            "question": f"What is a good revision strategy for {topic_label}?",
            "options": [
                "Summarize key points and test yourself",
                "Read once and never return",
                "Avoid notes and examples",
                "Focus only on unrelated topics",
            ],
            "answer": "Summarize key points and test yourself",
            "explanation": "Active revision improves memory better than passive reading.",
        },
    ]


def _normalize_text(value: str) -> str:
    return " ".join(str(value).strip().lower().split())


def _best_matching_option(answer: str, options: list[str]) -> str:
    if not options:
        return ""

    answer_text = _normalize_text(answer)
    if not answer_text:
        return options[0]

    for option in options:
        if _normalize_text(option) == answer_text:
            return option

    if answer_text in {"a", "b", "c", "d"}:
        index = ord(answer_text) - ord("a")
        if index < len(options):
            return options[index]

    if answer_text.isdigit():
        index = int(answer_text) - 1
        if 0 <= index < len(options):
            return options[index]

    return max(options, key=lambda option: SequenceMatcher(None, answer_text, _normalize_text(option)).ratio())


def _normalize_quiz_items(raw_items: list[dict], fallback_topic: str) -> list[dict]:
    normalized_items: list[dict] = []
    for item in raw_items[:5]:
        if not isinstance(item, dict):
            continue

        options = item.get("options", [])
        if not isinstance(options, list):
            options = [str(options)]
        cleaned_options = []
        for option in options:
            option_text = str(option).strip()
            if option_text and option_text not in cleaned_options:
                cleaned_options.append(option_text)

        answer = (
            item.get("answer")
            or item.get("correct_answer")
            or item.get("correctAnswer")
            or item.get("correct")
            or item.get("solution")
            or ""
        )
        answer = str(answer).strip()
        if answer and answer not in cleaned_options:
            cleaned_options.append(answer)

        if len(cleaned_options) < 2:
            continue

        cleaned_options = cleaned_options[:4]
        correct_answer = _best_matching_option(answer, cleaned_options)
        if not correct_answer:
            continue

        normalized_items.append(
            {
                "question": str(item.get("question", "Question")).strip() or "Question",
                "options": cleaned_options,
                "answer": correct_answer,
                "explanation": str(item.get("explanation", "")).strip(),
            }
        )

    return normalized_items or _fallback_quiz(fallback_topic)


def _fallback_flashcards(message: str) -> list[dict]:
    return [{"front": "Flashcard generation unavailable", "back": message}]


def _fallback_mind_map(message: str) -> dict:
    return {
        "topic": "Mind Map Unavailable",
        "branches": [{"title": "Try Again", "points": [message, "Upload clearer text or add more detail."]}],
    }


def summarize_text(text: str, mode: str, api_key: Optional[str]) -> str:
    if not text.strip():
        return "Please provide text or upload a file first."

    task = "Create a concise summary with key points and revision tips." if mode == "summary" else (
        "Analyze this material. Explain the main idea, difficult concepts, strengths, gaps, and likely exam questions."
    )

    messages = [
        {
            "role": "system",
            "content": "You are an expert tutor. Respond in clean markdown with short sections and practical learning advice.",
        },
        {"role": "user", "content": f"{task}\n\nMaterial:\n{text[:12000]}"},
    ]
    return ask_llm(messages, api_key=api_key)


def create_quiz(text: str, api_key: Optional[str]) -> list[dict]:
    if not text.strip():
        return _fallback_quiz("No input provided.")

    messages = [
        {
            "role": "system",
            "content": (
                "Create exactly 5 multiple-choice questions from the given topic or material. "
                "If the user gives only a short topic, use accurate general knowledge about that topic. "
                "Each question must have exactly 4 options. "
                "The answer must exactly match one of the options. "
                "Return only valid JSON as an array of objects with keys: question, options, answer, explanation."
            ),
        },
        {"role": "user", "content": text[:12000]},
    ]
    try:
        response = ask_llm(messages, api_key=api_key, temperature=0.2)
        quiz_items = extract_json_from_text(response)
        if not isinstance(quiz_items, list) or not quiz_items:
            return _fallback_quiz(text)
        return _normalize_quiz_items(quiz_items, text)
    except Exception:
        return _fallback_quiz(text)


def create_flashcards(text: str, api_key: Optional[str]) -> list[dict]:
    if not text.strip():
        return _fallback_flashcards("Add text or upload material first.")

    messages = [
        {
            "role": "system",
            "content": (
                "Create exactly 8 concise flashcards from the material. "
                "Return only valid JSON as an array of objects with keys: front, back."
            ),
        },
        {"role": "user", "content": text[:12000]},
    ]
    response = ask_llm(messages, api_key=api_key, temperature=0.2)
    try:
        cards = extract_json_from_text(response)
        if not isinstance(cards, list) or not cards:
            return _fallback_flashcards("The model returned no flashcards.")

        normalized_cards: list[dict] = []
        for item in cards[:8]:
            if not isinstance(item, dict):
                continue
            normalized_cards.append(
                {
                    "front": str(item.get("front", "Flashcard")).strip() or "Flashcard",
                    "back": str(item.get("back", "No answer available.")).strip() or "No answer available.",
                }
            )

        return normalized_cards or _fallback_flashcards("The generated flashcard format was invalid.")
    except Exception:
        return _fallback_flashcards("The AI response could not be converted into flashcards.")


def create_mind_map(text: str, api_key: Optional[str]) -> dict:
    if not text.strip():
        return _fallback_mind_map("No input provided.")

    messages = [
        {
            "role": "system",
            "content": (
                "Create a concise study mind map from the material. "
                "Return only valid JSON with keys: topic, branches. "
                "Each branch must be an object with keys: title, points. "
                "points must be an array of short strings. Create 4 to 6 branches."
            ),
        },
        {"role": "user", "content": text[:12000]},
    ]
    response = ask_llm(messages, api_key=api_key, temperature=0.2)
    try:
        mind_map = extract_json_from_text(response)
        if not isinstance(mind_map, dict):
            return _fallback_mind_map("The model returned an invalid mind map format.")

        topic = str(mind_map.get("topic", "Study Topic")).strip() or "Study Topic"
        branches = []
        for branch in mind_map.get("branches", [])[:6]:
            if not isinstance(branch, dict):
                continue
            points = branch.get("points", [])
            if not isinstance(points, list):
                points = [str(points)]
            cleaned_points = [str(point).strip() for point in points if str(point).strip()]
            branches.append(
                {
                    "title": str(branch.get("title", "Branch")).strip() or "Branch",
                    "points": cleaned_points,
                }
            )

        return {"topic": topic, "branches": branches} if branches else _fallback_mind_map(
            "The generated mind map had no usable branches."
        )
    except Exception:
        return _fallback_mind_map("The AI response could not be converted into a mind map.")


def mind_map_to_markdown(mind_map: dict) -> str:
    topic = mind_map.get("topic", "Mind Map")
    lines = [f"# {topic}", ""]
    for branch in mind_map.get("branches", []):
        lines.append(f"## {branch.get('title', 'Branch')}")
        for point in branch.get("points", []):
            lines.append(f"- {point}")
        lines.append("")
    return "\n".join(lines)


def create_study_pack_markdown(source_text: str, result_text: str, sources: list[str]) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    source_label = ", ".join(sources) if sources else "Manual text input"
    return "\n".join(
        [
            "# EduTutor AI Study Pack",
            "",
            f"Generated: {timestamp}",
            f"Sources: {source_label}",
            "",
            "## Source Material",
            source_text[:8000] if source_text.strip() else "No source text provided.",
            "",
            "## Generated Output",
            result_text,
            "",
        ]
    )
