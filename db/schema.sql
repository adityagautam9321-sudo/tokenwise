CREATE DATABASE IF NOT EXISTS tokenwise
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE tokenwise;

-- Only a bcrypt HASH is stored. The real password is never saved.
CREATE TABLE IF NOT EXISTS users (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    email         VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS requests (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id       INT NOT NULL,
    prompt        TEXT NOT NULL,
    task          VARCHAR(50),
    chosen_model  VARCHAR(80),
    input_tokens  INT DEFAULT 0,
    output_tokens INT DEFAULT 0,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS feedback (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    user_id    INT NOT NULL,
    model_key  VARCHAR(50) NOT NULL,
    task_type  VARCHAR(50) NOT NULL,
    rating     TINYINT NOT NULL,           -- 1 to 5
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Full advisor chat sessions (save / reopen / delete)
CREATE TABLE IF NOT EXISTS conversations (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NOT NULL,
    title       VARCHAR(255) NOT NULL,
    task_type   VARCHAR(50),
    messages_json LONGTEXT NOT NULL,
    plan_json   LONGTEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_conv_user (user_id, updated_at)
);
