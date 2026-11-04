"""MySQL connection pool (settings come from .env)."""
import os

from dotenv import load_dotenv
from mysql.connector import pooling

load_dotenv()

_pool = None


def _get_pool():
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="tokenwise_pool",
            pool_size=5,
            host=os.getenv("MYSQL_HOST", "localhost"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            user=os.getenv("MYSQL_USER", "root"),
            password=os.getenv("MYSQL_PASSWORD", ""),
            database=os.getenv("MYSQL_DATABASE", "tokenwise"),
        )
    return _pool


def get_connection():
    """Borrow a connection from the pool. Call .close() to return it."""
    return _get_pool().get_connection()
