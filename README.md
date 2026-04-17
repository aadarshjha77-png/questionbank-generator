# Questionbank Generator (Streamlit + OpenAI)

This app lets a user:
1. Upload a PDF at runtime.
2. Enter a topic/focus prompt.
3. Detect chapters from the Contents page and select only desired chapters.
4. Generate chapter-wise questions using an OpenAI model from YAML config.

## Project Structure

- `app.py`: Streamlit UI and orchestration
- `config.py`: config loader + validation
- `config/settings.yaml`: hardcoded/default values (API key, model, prompts, limits)
- `utils/pdf_parser.py`: PDF text extraction + chapter splitting
- `utils/question_generator.py`: OpenAI API call and structured response parsing

## Notes

- The app processes the uploaded PDF one chapter/segment at a time.
- Chapter detection first parses the Contents page (TOC) and maps chapter page ranges.
- If TOC parsing fails, it falls back to regex heading split and then segment split.
- Output can be downloaded as JSON and Markdown.

# 🤖 AI Question Bank Generator

An intelligent web application that generates exam-ready questions from uploaded PDFs using AI. Built with Streamlit, this system supports user authentication, analytics dashboard, and export features.

# 🚀 Features

- 🔐 User Login & Signup System
- 👑 Admin Dashboard (Analytics)
- 📄 Upload PDF & Extract Chapters
- 🤖 AI-based Question Generation (Descriptive + MCQ)
- 💬 Chat-based UI (Ask & Answer questions)
- 📊 User Analytics Dashboard
- 📥 Download Questions as CSV
- 📈 Track Most Used Topics & Active Users

## 🧠 Tech Stack

- Python
- Streamlit
- OpenAI API
- SQLite Database
- Pandas
