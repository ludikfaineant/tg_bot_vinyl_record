CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    telegram_id INTEGER UNIQUE
);

CREATE TABLE album_videos (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    video_path VARCHAR NOT NULL,
    title VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
