"""Create missing tables on startup so existing MySQL installs pick up Phase 4 schema."""
from db.connection import get_connection

_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS feedback (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        model_key VARCHAR(50) NOT NULL,
        task_type VARCHAR(50) NOT NULL,
        rating TINYINT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS conversations (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        title VARCHAR(255) NOT NULL,
        task_type VARCHAR(50),
        messages_json LONGTEXT NOT NULL,
        plan_json LONGTEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        INDEX idx_conv_user (user_id, updated_at)
    )
    """,
]


def ensure_schema() -> None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        for sql in _STATEMENTS:
            cur.execute(sql)
        conn.commit()
    finally:
        conn.close()
