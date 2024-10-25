CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    telegram_id INTEGER UNIQUE
);

CREATE TABLE processed_videos (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    video_path VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);