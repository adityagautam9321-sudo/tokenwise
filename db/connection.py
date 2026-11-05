"""MySQL connection pool. Settings come from .env locally or Streamlit secrets in the cloud."""
import os

from dotenv import load_dotenv
from mysql.connector import pooling

load_dotenv()

_pool = None


def _cfg(name: str, default: str = "") -> str:
    """Read a setting from the environment, then from Streamlit secrets."""
    value = os.getenv(name)
    if value:
        return value
    try:
        import streamlit as st
        return str(st.secrets.get(name, default))
    except Exception:
        return default


def _get_pool():
    global _pool
    if _pool is None:
        kwargs = dict(
            pool_name="tokenwise_pool",
            pool_size=5,
            host=_cfg("MYSQL_HOST", "localhost"),
            port=int(_cfg("MYSQL_PORT", "3306")),
            user=_cfg("MYSQL_USER", "root"),
            password=_cfg("MYSQL_PASSWORD", ""),
            database=_cfg("MYSQL_DATABASE", "tokenwise"),
        )
        if _cfg("MYSQL_SSL", "").lower() in ("1", "true", "yes"):
            import certifi
            kwargs.update(ssl_ca=certifi.where(), ssl_verify_cert=True)
        _pool = pooling.MySQLConnectionPool(**kwargs)
    return _pool


def get_connection():
    """Borrow a connection from the pool. Call .close() to return it."""
    return _get_pool().get_connection()