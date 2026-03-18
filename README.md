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

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Update `config/settings.yaml`:
- `openai.api_key`: your key
- `openai.model`: any supported model you want
- optional: temperature, output tokens, chapter rules, prompt template

## Run

```bash
streamlit run app.py
```

## Notes

- The app processes the uploaded PDF one chapter/segment at a time.
- Chapter detection first parses the Contents page (TOC) and maps chapter page ranges.
- If TOC parsing fails, it falls back to regex heading split and then segment split.
- Output can be downloaded as JSON and Markdown.
