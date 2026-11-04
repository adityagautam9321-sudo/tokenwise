import time
from concurrent.futures import ThreadPoolExecutor

import streamlit as st

import web_search as search
from core import pdf_builder, runner
from core.media import attachments_context, image_data_urls, render_result_image
from core.model_registry import MODELS
from core.scoring import savings_vs_baseline
from db.user import log_request, save_feedback
from ui.theme import hero

ss = st.session_state
plan, model_id = ss.get("plan"), ss.get("selected_model")

hero("Run Task", "Execute the recommended model, race both, and rate the result.", pill="Execution")

# Allow landing here with a pre-computed vision result (no run_pending needed)
_has_precomputed = ss.get("result") and not ss.get("run_pending") and not ss.get("race_ids")

if not plan or (model_id not in MODELS and not ss.get("race_ids") and not _has_precomputed):
    st.info("Pick a model on the Assistant page first.")
    if st.button("Go to Assistant"):
        st.switch_page("pages/assistant.py")
    st.stop()


def _media_bundle():
    """Combine web search + attachment text, plus image data-URLs for vision models."""
    parts = []
    if plan.get("needs_web") and plan.get("search_query"):
        try:
            web = search.search_web(plan["search_query"])
            if web:
                parts.append(web)
        except Exception as e:
            st.warning(f"Web search failed, continuing without it: {e}")
    att_ctx = attachments_context(ss.get("attachments") or [])
    if att_ctx:
        parts.append(att_ctx)
    context = "\n\n".join(parts)
    urls = image_data_urls(ss.get("attachments") or [])
    return context, urls


def _run_one(model, context="", image_urls=None):
    try:
        return runner.run(model, plan, context, image_urls=image_urls)
    except Exception as e:
        return {"error": str(e)}


def _auto_pdf(text: str) -> bytes:
    title = (plan.get("task_type") or "TokenWise").replace("_", " ").title()
    return pdf_builder.build_pdf(text, default_title=title)


def _auto_image(text: str) -> bytes:
    title = (plan.get("task_type") or "TokenWise result").replace("_", " ").title()
    return render_result_image(title, text)


def _log_savings(model_key: str, model: dict, res: dict):
    sv = savings_vs_baseline(model, res["input_tokens"], res["output_tokens"])
    entry = {
        "model": model["label"],
        "model_key": model_key,
        "task": plan.get("task_type"),
        "in_tok": res["input_tokens"],
        "out_tok": res["output_tokens"],
        "cost": sv["cost"],
        "baseline": sv["baseline"],
        "baseline_cost": sv["baseline_cost"],
        "saved": sv["saved"],
        "percent": sv["percent"],
        "when": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    bag = ss.setdefault("savings_log", [])
    bag.insert(0, entry)
    ss.savings_log = bag[:50]


# ---------- Race mode ----------
if ss.get("race_ids"):
    st.markdown(
        f"**Race:** {' vs '.join(MODELS[i]['label'] for i in ss.race_ids)} · "
        f"**Task:** {plan['task_type'].replace('_', ' ').title()}"
    )
    with st.expander("Task sent to the models"):
        st.write(plan["task_prompt"])

    if ss.get("run_pending") or not ss.get("race_results"):
        ss.run_pending = False
        with st.spinner("Preparing media + racing models..."):
            context, urls = _media_bundle()
            models = [MODELS[i] for i in ss.race_ids]
            t0 = time.time()
            with ThreadPoolExecutor(max_workers=2) as ex:
                ss.race_results = list(
                    ex.map(lambda m: _run_one(m, context, urls), models)
                )
            ss.race_elapsed = round(time.time() - t0, 2)

        for mid, res in zip(ss.race_ids, ss.race_results):
            if "error" in res:
                continue
            try:
                log_request(
                    ss.user["id"],
                    plan["task_prompt"][:5000],
                    plan["task_type"],
                    MODELS[mid]["api_id"],
                    res["input_tokens"],
                    res["output_tokens"],
                )
            except Exception:
                pass
            _log_savings(mid, MODELS[mid], res)

    st.subheader("⚔️ Race results")
    st.caption(f"Wall time: {ss.get('race_elapsed', '?')} s (parallel)")
    st.info("Cost savings are tracked under **History → Savings**.")
    cols = st.columns(2)
    for col, mid, res in zip(cols, ss.race_ids, ss.race_results):
        m = MODELS[mid]
        with col, st.container(border=True):
            st.markdown(f"### {m['label']}")
            if "error" in res:
                st.error(res["error"])
                continue
            st.caption(
                f"{res['input_tokens'] + res['output_tokens']:,} tokens · {res['seconds']}s"
            )
            st.markdown(res["text"])
            pdf_bytes = _auto_pdf(res["text"])
            img_bytes = _auto_image(res["text"])
            st.download_button(
                "📄 PDF",
                data=pdf_bytes,
                file_name=f"tokenwise_{mid}.pdf",
                mime="application/pdf",
                key=f"pdf_{mid}",
                type="primary",
            )
            st.download_button(
                "🖼️ Image card",
                data=img_bytes,
                file_name=f"tokenwise_{mid}.png",
                mime="image/png",
                key=f"img_{mid}",
            )
            rating = st.feedback("stars", key=f"race_fb_{mid}")
            if rating is not None and not ss.get(f"fb_race_{mid}"):
                try:
                    save_feedback(ss.user["id"], mid, plan["task_type"], rating + 1)
                    ss[f"fb_race_{mid}"] = True
                    st.toast(f"Thanks — TokenWise will learn from your rating of {m['label']}.")
                except Exception as e:
                    st.warning(f"Could not save feedback: {e}")

    if st.button("← Back to Assistant"):
        ss.pop("race_ids", None)
        ss.pop("race_results", None)
        st.switch_page("pages/assistant.py")
    st.stop()


# ---------- Single model ----------
# For pre-computed vision results model_id may still be valid; guard either way
model = MODELS.get(model_id) if model_id else None

if _has_precomputed and not model:
    # Vision result arrived without a registry model — show result directly
    result = ss.get("result")
    task_label = (plan.get("task_type") or "analysis").replace("_", " ").title()
    st.markdown(f"**Task:** {task_label}  ·  *answered by vision model*")
else:
    if not model:
        st.info("Pick a model on the Assistant page first.")
        if st.button("Go to Assistant"):
            st.switch_page("pages/assistant.py")
        st.stop()
    st.markdown(
        f"**Model:** {model['label']}  ·  **Task:** {plan['task_type'].replace('_', ' ').title()}"
    )
    if ss.get("attachments"):
        st.caption(f"{len(ss.attachments)} attachment(s) will be included in this run.")
    with st.expander("Task sent to the model"):
        st.write(plan["task_prompt"])

    if ss.get("run_pending"):
        ss.run_pending = False
        with st.spinner(f"Running on Groq · {model['label']}..."):
            try:
                context, urls = _media_bundle()
                ss.sources_text = context if plan.get("needs_web") else ""
                ss.result = runner.run(model, plan, context, image_urls=urls)
                ss.result_pdf = _auto_pdf(ss.result["text"])
                ss.result_image = _auto_image(ss.result["text"])
            except Exception as e:
                ss.result = None
                ss.result_pdf = None
                ss.result_image = None
                st.error(f"Model error: {e}")
                st.info("Go back to Assistant and pick the other recommended model.")

        if ss.result:
            try:
                log_request(
                    ss.user["id"],
                    plan["task_prompt"][:5000],
                    plan["task_type"],
                    model["api_id"],
                    ss.result["input_tokens"],
                    ss.result["output_tokens"],
                )
            except Exception as e:
                st.warning(f"Could not save run history: {e}")
            _log_savings(model_id, model, ss.result)

result = ss.get("result")
if result:
    st.subheader("✅ Result")
    st.markdown(result["text"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Input tokens", f"{result['input_tokens']:,}")
    c2.metric("Output tokens", f"{result['output_tokens']:,}")
    c3.metric("Total tokens", f"{result['input_tokens'] + result['output_tokens']:,}")
    c4.metric("Time", f"{result['seconds']} s")

    st.info("Cost savings for this run are listed under **History → Savings**.")

    if ss.get("sources_text"):
        with st.expander("🌐 / 📎 Context used"):
            st.markdown(ss.sources_text[:4000])

    if not ss.get("result_pdf"):
        ss.result_pdf = _auto_pdf(result["text"])
    if not ss.get("result_image"):
        ss.result_image = _auto_image(result["text"])

    st.subheader("Downloads")
    d1, d2, d3 = st.columns(3)
    with d1:
        st.download_button(
            "📄 PDF (auto-generated)",
            data=ss.result_pdf,
            file_name="tokenwise_output.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True,
        )
    with d2:
        st.download_button(
            "🖼️ Image card (PNG)",
            data=ss.result_image,
            file_name="tokenwise_card.png",
            mime="image/png",
            use_container_width=True,
        )
    with d3:
        st.download_button(
            "📝 Text",
            result["text"],
            file_name="tokenwise_output.txt",
            use_container_width=True,
        )

    st.write("Was this result good?")
    rating = st.feedback("stars", key="single_fb")
    if rating is not None and not ss.get("feedback_given"):
        try:
            save_feedback(ss.user["id"], model_id, plan["task_type"], rating + 1)
            ss.feedback_given = True
            st.toast("Thanks — TokenWise will learn from this.")
        except Exception as e:
            st.warning(f"Could not save feedback: {e}")

    st.divider()
    if st.button("← Back to Assistant", use_container_width=True):
        st.switch_page("pages/assistant.py")
