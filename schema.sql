CREATE TABLE lists (
    id SERIAL PRIMARY KEY,
    title VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE todos (
    id SERIAL PRIMARY KEY,
    title VARCHAR(100) NOT NULL,
    completed BOOLEAN NOT NULL DEFAULT FALSE,
    list_id INTEGER NOT NULL REFERENCES lists(id) ON DELETE CASCADE,
    position_idx INTEGER NOT NULL,
    unique(list_id, position_idx)
);