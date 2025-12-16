# FinPro Robo-Advisor (FastAPI + Streamlit)

A simple robo-advisor prototype:
- **Backend (FastAPI)** serves recommendations via `/recommend`
- **Model**: SVD (warm-start for existing users)
- **Cold-start**: rule-based recommendations based on risk profile
- **Frontend (Streamlit)** collects user input, calls the API, and displays recommended assets (cards + table)

---

## Prerequisites

- Python **3.10 / 3.11** recommended  
  (If you use Python 3.12 and hit binary/architecture errors, use 3.11.)
- macOS users: avoid Rosetta if you’re on Apple Silicon.
- Activate venv
- Install dependencies 
---

## 1) Setup (Virtual Environment)

From the project directory:

```bash
python3 -m venv .venv
source .venv/bin/activate

pip install fastapi uvicorn pandas pydantic streamlit requests scikit-surprise
```

Open Terminal A and run:
```uvicorn main:app --reload```

Open Terminal B and run:
```streamlit run streamlit_app.py --server.port 8502```
