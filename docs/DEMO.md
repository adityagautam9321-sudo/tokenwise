# TokenWise — Demo screenshots & slides

## Screenshot checklist

Run `streamlit run app.py`, then capture these (full browser window, light theme):

| # | Page | What to show |
|---|------|--------------|
| 1 | Login | TokenWise brand + Login / Register tabs |
| 2 | Assistant (empty) | Welcome message + chat input + priority slider in sidebar |
| 3 | Assistant (recs) | Chat thread + two model cards + **Race both models** |
| 4 | Priority | Same task, slider at Cost vs at Quality (two shots) |
| 5 | Run Task | Result text + token metrics + **savings meter** |
| 6 | Race mode | Side-by-side outputs with time / tokens / cost |
| 7 | Feedback | Star rating after a result |
| 8 | History | Chat sessions list with Open / Delete |
| 9 | Dashboard | Metrics row + model / task bar charts |

Save files under `docs/screenshots/` as `01-login.png` … `09-dashboard.png`.

## Suggested slide outline (8–10 slides)

1. **Title** — TokenWise: pick the cheapest model that still does the job
2. **Problem** — Teams overpay by defaulting to the biggest model
3. **Solution** — Advisor → scored top-2 → run / race → learn from ratings
4. **Architecture** — Streamlit UI · Gemini/Groq advisor · Groq runners · MySQL
5. **Priority slider** — Cost ↔ Quality re-ranks without another LLM call
6. **Savings meter & Race** — Prove the cheaper pick still works
7. **Feedback learning** — Stars adjust fit scores after enough votes
8. **History & Dashboard** — Persist chats, delete anytime, see usage
9. **Demo / live walkthrough**
10. **Next steps** — More providers, team budgets, auto-router

## Live demo script (~3 minutes)

1. Log in → open Assistant.
2. Ask: *“Write a short Python function that merges two sorted lists.”*
3. Move priority toward **Cost**, then toward **Quality** — watch ranking change.
4. Click **Race both models** → compare outputs and the savings meter.
5. Leave a star rating → mention it feeds future recommendations.
6. Open **History** → reopen or delete the chat.
7. Open **Dashboard** → show runs / tokens / model mix.
