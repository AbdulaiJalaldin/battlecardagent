CREATE TABLE IF NOT EXISTS battlecards (
    competitor_name TEXT PRIMARY KEY,
    strengths TEXT,           -- JSON array
    weaknesses TEXT,          -- JSON array
    objection_handling TEXT,  -- JSON array
    last_updated TIMESTAMP
);