
# 🤖 EDUBOT - AI Study Assistant

**Intelligent Chatbot for Education and Tutoring**

EDUBOT is a Generative AI-powered study assistant built with **Python**, **Streamlit**, **LLMs**, and **RAG-based document retrieval**. It helps students ask doubts, upload study materials, generate summaries, practice quizzes, create flashcards, and revise faster through an interactive learning interface.

This project is designed as an academic AI tutoring system that supports both general learning queries and document-based question answering.

## ✨ Why EDUBOT?

Students often depend on textbooks, PDFs, recorded lectures, and search engines for learning. These methods can be slow, scattered, and not personalized. EDUBOT brings everything into one simple learning workspace where students can upload notes, ask questions, and instantly create revision tools.

## 🎯 Key Features

- AI chatbot for academic doubt solving
- Document-based question answering using uploaded files
- Retrieval-Augmented Generation with embeddings and FAISS
- Upload support for PDF, DOCX, PPTX, TXT, MD, CSV, JSON, and images
- Automatic study material summarization
- Interactive multiple-choice quizzes with score and correct answers
- Flashcards for quick revision
- Mind map generation for topic understanding
- Learning goal input for personalized responses
- Local chat history and downloadable markdown export
- Optional voice input support
- Clean Streamlit interface inspired by modern AI tutor apps

## 🏗️ Project Architecture

```text
Student Query / Uploaded Study Material
                  |
                  v
Input Processing and Text Extraction
                  |
                  v
Text Chunking and Preprocessing
                  |
                  v
Embedding Generation
                  |
                  v
FAISS Vector Search
                  |
                  v
Relevant Context Retrieval
                  |
                  v
LLM Response Generation
                  |
                  v
Answer, Summary, Quiz, Flashcards, or Mind Map
```

## ⚙️ Tech Stack

- **Frontend/UI:** Streamlit
- **Backend:** Python
- **AI/LLM:** API-based Large Language Model integration
- **RAG:** FAISS and Sentence Transformers
- **Document Processing:** PyPDF2, python-docx, python-pptx
- **Image OCR:** Pillow and pytesseract
- **Voice Support:** SpeechRecognition and pyttsx3
- **Environment Management:** python-dotenv

## 📁 Folder Structure

```text
EDUBOT/
  app.py                  # Compatibility entry point
  edututor_app.py         # Main Streamlit application
  config.py               # App and model configuration
  requirements.txt        # Required Python packages
  README.md               # Project documentation
  .env.example            # API key template
  .gitignore              # Files excluded from GitHub
  run_edututor.bat        # Windows quick-start launcher
  assets/
    style.css             # Custom UI styling
  data/
    .gitkeep              # Keeps data folder in repository
  modules/
    file_utils.py         # File upload and text extraction
    image_utils.py        # OCR helper
    llm.py                # LLM client and response handling
    memory_utils.py       # Chat history utilities
    pdf_utils.py          # PDF extraction helper
    rag.py                # Chunking, embeddings, and FAISS retrieval
    study_tools.py        # Quiz, summary, flashcard, and mind map logic
    voice_utils.py        # Voice input helper
```

## 🚀 Installation

1. Download or clone this repository, then open the project folder.

```bash
cd EDUBOT-AI-Study-Assistant
```

2. Create a virtual environment.

```bash
python -m venv .venv
```

3. Activate the virtual environment.

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

4. Install dependencies.

```bash
pip install -r requirements.txt
```

5. Create the environment file.

Windows:

```bash
copy .env.example .env
```

macOS/Linux:

```bash
cp .env.example .env
```

6. Add your API key inside `.env`.

```env
AI_API_KEY=your_api_key_here
```

7. Run EDUBOT.

```bash
streamlit run edututor_app.py
```

The app will open in your browser at:

```text
http://localhost:8501
```

## 💡 How To Use

Try these prompts:

- `Explain photosynthesis in simple terms`
- `Create a quiz about cricket`
- `Create flashcards about Python loops`
- `Summarize this chapter into 5 key points`
- `Create a mind map about World War 2`
- `Analyze the uploaded file and explain it simply`

You can also upload study materials from the sidebar and ask questions based on them.

## 🧠 Quiz Feature

EDUBOT includes an interactive quiz system:

- Generates multiple-choice questions from any topic or uploaded material
- Lets the student choose answers
- Requires all questions to be answered before submission
- Shows score after submission
- Displays the correct answer for every question

## 📌 Documentation Alignment

This project follows the academic documentation requirement:

**"Intelligent Chatbot for Education and Tutoring"**

Implemented modules include:

- Streamlit-based chatbot interface
- General query mode
- Document upload and processing
- Document-based question answering
- RAG using FAISS
- LLM-generated answers
- Summary generation
- Quiz generation
- Flashcard generation
- Mind map generation

# 🔍 Retrieval-Augmented Generation (RAG)

EDUBOT uses Retrieval-Augmented Generation (RAG) to improve response accuracy by retrieving relevant information from uploaded documents before generating answers with the language model.

This enables:

- Context-aware responses
- Better accuracy
- Reduced hallucinations
- Personalized document-based tutoring

---

# 🖼 OCR Support

Image uploads are processed using **Tesseract OCR** through `pytesseract`.

Install Tesseract OCR if you plan to analyze images containing text.

Windows default installation path:

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

---

# 🔮 Future Enhancements

- 🌍 Multilingual tutoring
- 📱 Mobile application
- 🎙 AI-generated audio explanations
- 📈 Student learning analytics
- ☁ Cloud-based document storage
- 🎓 Learning Management System (LMS) integration
- 📊 Personalized study recommendations

---

# 📌 GitHub Notes

The following files should **not** be uploaded:

- `.env`
- `.venv/`
- `__pycache__/`
- Local cache files
- Temporary logs
- Generated memory/history files (if any)

Before pushing the project:

```bash
streamlit run app.py
```

Verify that the application launches successfully.

---

# ⚠️ Disclaimer

EDUBOT generates responses using Large Language Models (LLMs). While it is designed to assist learning, users should verify important academic information using trusted educational resources.

---

# 👨‍💻 Author

**Your Name**

Bachelor of Engineering (Computer Science)

Final Year Project

GitHub: https://github.com/poojaoruganti36 

---

# 📄 License

This project is licensed under the **MIT License**.

See the **LICENSE** file for more information.

---

## ⭐ If you found this project useful, consider giving it a star on GitHub!



