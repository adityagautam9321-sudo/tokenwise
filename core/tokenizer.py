"""Token analysis using Hugging Face tokenizers (cached after first load)."""
from functools import lru_cache

TOKENIZER_MODELS = {
    "BERT": "bert-base-uncased",
    "DistilBERT": "distilbert-base-uncased",
    "RoBERTa": "roberta-base",
    "T5": "t5-small",
}


@lru_cache(maxsize=4)
def _load(model_id: str):
    from transformers import AutoTokenizer  # imported lazily: heavy import
    return AutoTokenizer.from_pretrained(model_id)


def tokenize_text(text: str, model_name: str = "BERT") -> dict:
    if not text.strip():
        return {"tokens": [], "token_count": 0, "words": 0, "characters": 0}

    tok = _load(TOKENIZER_MODELS.get(model_name, "bert-base-uncased"))
    ids = tok(text, add_special_tokens=True)["input_ids"]
    tokens = tok.convert_ids_to_tokens(ids)
    return {
        "tokens": tokens,
        "token_count": len(tokens),
        "words": len(text.split()),
        "characters": len(text),
    }
