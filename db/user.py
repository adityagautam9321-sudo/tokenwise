"""User registration, login, request history, conversations, feedback."""
import json
import re

import bcrypt
from mysql.connector import Error, IntegrityError

from db.connection import get_connection

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def register_user(name: str, email: str, password: str):
    """Returns (ok: bool, message: str)."""
    name, email = name.strip(), email.strip().lower()

    if len(name) < 2:
        return False, "Please enter your name."
    if not EMAIL_RE.match(email):
        return False, "Please enter a valid email address."
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    if len(password.encode("utf-8")) > 72:
        return False, "Password is too long (max 72 bytes)."

    pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode()

    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s)",
            (name, email, pw_hash),
        )
        conn.commit()
        return True, "Account created. You can log in now."
    except IntegrityError:
        return False, "This email is already registered."
    except Error as e:
        return False, f"Database error: {e}"
    finally:
        if conn:
            conn.close()


def authenticate(email: str, password: str):
    """Returns {'id','name','email'} on success, otherwise None."""
    email = email.strip().lower()
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id, name, email, password_hash FROM users WHERE email = %s",
            (email,),
        )
        row = cur.fetchone()
    finally:
        if conn:
            conn.close()

    if not row:
        return None
    if bcrypt.checkpw(password.encode("utf-8"), row["password_hash"].encode()):
        return {"id": row["id"], "name": row["name"], "email": row["email"]}
    return None


def log_request(user_id, prompt, task, model, input_tokens, output_tokens):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO requests "
            "(user_id, prompt, task, chosen_model, input_tokens, output_tokens) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (user_id, prompt, task, model, input_tokens, output_tokens),
        )
        conn.commit()
    finally:
        if conn:
            conn.close()


def get_history(user_id, limit=20):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id, created_at, task, chosen_model, input_tokens, output_tokens, "
            "LEFT(prompt, 120) AS prompt_preview "
            "FROM requests WHERE user_id = %s ORDER BY id DESC LIMIT %s",
            (user_id, limit),
        )
        return cur.fetchall()
    finally:
        if conn:
            conn.close()


def delete_request(user_id, request_id) -> bool:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM requests WHERE id = %s AND user_id = %s",
            (request_id, user_id),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def save_feedback(user_id, model_key, task_type, rating):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO feedback (user_id, model_key, task_type, rating) "
            "VALUES (%s, %s, %s, %s)",
            (user_id, model_key, task_type, rating),
        )
        conn.commit()
    finally:
        conn.close()


def get_fit_adjustments(min_votes=3):
    """{(model_key, task_type): delta} where delta is between -2 and +2."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT model_key, task_type, AVG(rating), COUNT(*) "
            "FROM feedback GROUP BY model_key, task_type"
        )
        return {
            (m, t): round(max(-2, min(2, (float(avg) - 3) * 1.0)), 1)
            for m, t, avg, n in cur.fetchall()
            if n >= min_votes
        }
    finally:
        conn.close()


def _title_from_messages(messages: list) -> str:
    for m in messages:
        if m.get("role") == "user" and (m.get("content") or "").strip():
            text = m["content"].strip().replace("\n", " ")
            return (text[:72] + "…") if len(text) > 72 else text
    return "Untitled chat"


def save_conversation(user_id, messages, plan=None, conversation_id=None):
    """Insert or update a conversation. Returns conversation id."""
    title = _title_from_messages(messages)
    task_type = (plan or {}).get("task_type")
    messages_json = json.dumps(messages, ensure_ascii=False)
    plan_json = json.dumps(plan, ensure_ascii=False) if plan else None

    conn = get_connection()
    try:
        cur = conn.cursor()
        if conversation_id:
            cur.execute(
                "UPDATE conversations SET title=%s, task_type=%s, messages_json=%s, "
                "plan_json=%s WHERE id=%s AND user_id=%s",
                (title, task_type, messages_json, plan_json, conversation_id, user_id),
            )
            if cur.rowcount == 0:
                conversation_id = None
        if not conversation_id:
            cur.execute(
                "INSERT INTO conversations (user_id, title, task_type, messages_json, plan_json) "
                "VALUES (%s, %s, %s, %s, %s)",
                (user_id, title, task_type, messages_json, plan_json),
            )
            conversation_id = cur.lastrowid
        conn.commit()
        return conversation_id
    finally:
        conn.close()


def list_conversations(user_id, limit=50):
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id, title, task_type, created_at, updated_at "
            "FROM conversations WHERE user_id = %s "
            "ORDER BY updated_at DESC LIMIT %s",
            (user_id, limit),
        )
        return cur.fetchall()
    finally:
        conn.close()


def get_conversation(user_id, conversation_id):
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id, title, task_type, messages_json, plan_json, created_at, updated_at "
            "FROM conversations WHERE id = %s AND user_id = %s",
            (conversation_id, user_id),
        )
        row = cur.fetchone()
        if not row:
            return None
        row["messages"] = json.loads(row.pop("messages_json") or "[]")
        plan_raw = row.pop("plan_json")
        row["plan"] = json.loads(plan_raw) if plan_raw else None
        return row
    finally:
        conn.close()


def delete_conversation(user_id, conversation_id) -> bool:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM conversations WHERE id = %s AND user_id = %s",
            (conversation_id, user_id),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def dashboard_stats(user_id):
    """Aggregate usage for the Dashboard page."""
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)

        cur.execute(
            "SELECT COUNT(*) AS runs, "
            "COALESCE(SUM(input_tokens), 0) AS in_tok, "
            "COALESCE(SUM(output_tokens), 0) AS out_tok "
            "FROM requests WHERE user_id = %s",
            (user_id,),
        )
        totals = cur.fetchone() or {"runs": 0, "in_tok": 0, "out_tok": 0}

        cur.execute(
            "SELECT chosen_model AS model, COUNT(*) AS n, "
            "SUM(input_tokens + output_tokens) AS tokens "
            "FROM requests WHERE user_id = %s "
            "GROUP BY chosen_model ORDER BY n DESC",
            (user_id,),
        )
        by_model = cur.fetchall()

        cur.execute(
            "SELECT task, COUNT(*) AS n FROM requests "
            "WHERE user_id = %s AND task IS NOT NULL "
            "GROUP BY task ORDER BY n DESC",
            (user_id,),
        )
        by_task = cur.fetchall()

        cur.execute(
            "SELECT COUNT(*) AS chats FROM conversations WHERE user_id = %s",
            (user_id,),
        )
        chats = cur.fetchone()["chats"]

        cur.execute(
            "SELECT AVG(rating) AS avg_rating, COUNT(*) AS n "
            "FROM feedback WHERE user_id = %s",
            (user_id,),
        )
        fb = cur.fetchone() or {"avg_rating": None, "n": 0}

        cur.execute(
            "SELECT created_at, task, chosen_model, input_tokens, output_tokens "
            "FROM requests WHERE user_id = %s ORDER BY id DESC LIMIT 8",
            (user_id,),
        )
        recent = cur.fetchall()

        return {
            "runs": int(totals["runs"] or 0),
            "in_tok": int(totals["in_tok"] or 0),
            "out_tok": int(totals["out_tok"] or 0),
            "chats": int(chats or 0),
            "by_model": by_model,
            "by_task": by_task,
            "feedback_count": int(fb["n"] or 0),
            "avg_rating": float(fb["avg_rating"]) if fb["avg_rating"] is not None else None,
            "recent": recent,
        }
    finally:
        conn.close()
