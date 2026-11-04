# TokenWise

Chat about the job you want done. TokenWise estimates tokens and cost, recommends the
2 best-value Groq models (with a cost↔quality priority slider), runs or **races** them,
shows a **savings meter**, learns from star ratings, and keeps **chat history** you can
reopen or delete. A **Dashboard** summarises your usage.

Flow: Login → Advisor → top-2 models → run / race → rate → History / Dashboard.

## Setup

1. `pip install -r requirements.txt`
2. Run `db/schema.sql` in MySQL Workbench (or let the app auto-create new Phase 4 tables).
3. Copy `.env.example` to `.env` and fill in the keys.
4. `streamlit run app.py`

Passwords are stored only as bcrypt hashes.

## Phase 4 features

| Feature | Where |
|---------|--------|
| Chat history (save / open / delete) | History page + auto-save on Assistant |
| Priority slider | Assistant sidebar |
| Savings meter | Run Task (single + race) |
| Race mode | Assistant → “Race both models” |
| Feedback learning | Star ratings on Run Task → fit adjustments |
| Dashboard | Usage metrics + charts |
| Testing / demo pack | `tests/`, `docs/DEMO.md` |

## Tests

```bash
python -m pytest tests/ -q
```

## Demo screenshots & slides

See [docs/DEMO.md](docs/DEMO.md).
