"""Five work modes shown on the Dashboard hub."""

WORK_MODES = {
    "coding": {
        "title": "Coding & technical",
        "icon": "💻",
        "blurb": "Code, debugging, algorithms, and maths/logic problems.",
        "benefit": "Routes hard STEM work to capable models without overpaying for simple scripts.",
        "task_type": "coding",
        "needs_web": False,
        "prefer_pdf": False,
        "starter": (
            "I need coding / technical help. "
            "Ask me for the language, problem statement, or maths question."
        ),
        "welcome": (
            "Coding & technical mode is on. Share your code, bug, algorithm, "
            "or maths problem — I'll pick a strong value model for it."
        ),
    },
    "general": {
        "title": "General & current affairs",
        "icon": "🌐",
        "blurb": "News, explainers, Q&A, and everyday research.",
        "benefit": "Uses live web search when needed so answers stay current.",
        "task_type": "question_answering",
        "needs_web": True,
        "prefer_pdf": False,
        "starter": (
            "I want help with general knowledge or current affairs. "
            "Ask what topic I care about."
        ),
        "welcome": (
            "General / current-affairs mode is on. Ask about news, concepts, "
            "or multiple questions — I'll answer each one separately."
        ),
    },
    "documents": {
        "title": "PDFs, folders & summaries",
        "icon": "📄",
        "blurb": "Summarise text, draft reports, and produce downloadable PDFs.",
        "benefit": "Auto-builds a PDF of the result so you can share or archive it.",
        "task_type": "pdf_generation",
        "needs_web": False,
        "prefer_pdf": True,
        "starter": (
            "I need a PDF, folder-style outline, or summary. "
            "Ask me for the text or topic to process."
        ),
        "welcome": (
            "Document mode is on. Paste text to summarise, outline a folder of topics, "
            "or ask for a report — TokenWise will generate a PDF for you."
        ),
    },
    "vision": {
        "title": "Images & detection",
        "icon": "🖼️",
        "blurb": "Describe, analyse, or detect content in pictures; craft image prompts.",
        "benefit": "Upload an image to analyse, or get a clear prompt for AI image tools.",
        "task_type": "data_extraction",
        "needs_web": False,
        "prefer_pdf": True,
        "starter": (
            "I want image help: describe/detect objects in a picture I upload, "
            "or write a detailed prompt to generate an AI picture."
        ),
        "welcome": (
            "Image mode is on. Upload a picture for description/detection, "
            "or tell me what AI image you want and I'll write a strong generation prompt."
        ),
    },
    "recommend": {
        "title": "Recommendation system",
        "icon": "⭐",
        "blurb": "Product, study, career, or content recommendations with reasons.",
        "benefit": "Structured picks with clear why/why-not — not a single opaque answer.",
        "task_type": "question_answering",
        "needs_web": False,
        "prefer_pdf": True,
        "starter": (
            "I want personalised recommendations. "
            "Ask what I need recommendations for and my constraints (budget, level, tastes)."
        ),
        "welcome": (
            "Recommendation mode is on. Tell me what you need suggestions for "
            "(courses, tools, movies, products…) and any constraints."
        ),
    },
}
