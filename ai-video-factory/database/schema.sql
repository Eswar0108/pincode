-- AI Video Factory Database Schema
-- SQLite database for job management, topics, and video renders

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- Topics discovered from trend sources
CREATE TABLE IF NOT EXISTS topics (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'unknown',
    score REAL NOT NULL DEFAULT 0,
    rank INTEGER NOT NULL DEFAULT 0,
    url TEXT,
    fetched_at TEXT NOT NULL DEFAULT (datetime('now')),
    status TEXT NOT NULL DEFAULT 'pending' -- pending, selected, rejected, rendered
);

-- Research results for each topic
CREATE TABLE IF NOT EXISTS research (
    id TEXT PRIMARY KEY,
    topic_id TEXT NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    summary TEXT,
    sources TEXT, -- JSON array of source URLs
    facts TEXT, -- JSON array of fact strings
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (topic_id) REFERENCES topics(id)
);

-- Generated scripts for each topic
CREATE TABLE IF NOT EXISTS scripts (
    id TEXT PRIMARY KEY,
    topic_id TEXT NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    hook TEXT NOT NULL,
    body TEXT NOT NULL,
    cta TEXT NOT NULL,
    word_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending', -- pending, approved, rejected
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (topic_id) REFERENCES topics(id)
);

-- Voice/narration assets
CREATE TABLE IF NOT EXISTS narration (
    id TEXT PRIMARY KEY,
    script_id TEXT NOT NULL REFERENCES scripts(id) ON DELETE CASCADE,
    audio_path TEXT NOT NULL,
    duration_seconds REAL NOT NULL DEFAULT 0,
    voice_id TEXT NOT NULL DEFAULT 'default',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (script_id) REFERENCES scripts(id)
);

-- Subtitle files
CREATE TABLE IF NOT EXISTS subtitles (
    id TEXT PRIMARY KEY,
    narration_id TEXT NOT NULL REFERENCES narration(id) ON DELETE CASCADE,
    ass_path TEXT NOT NULL,
    srt_path TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (narration_id) REFERENCES narration(id)
);

-- Video render jobs
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    topic_id TEXT NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'queued', -- queued, rendering, completed, failed
    output_path TEXT,
    duration_seconds REAL,
    file_size_bytes INTEGER,
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT,
    FOREIGN KEY (topic_id) REFERENCES topics(id)
);

-- Project folders (one per video)
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    topic_id TEXT REFERENCES topics(id),
    project_path TEXT NOT NULL,
    final_mp4 TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    approved INTEGER NOT NULL DEFAULT 0,
    published INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (topic_id) REFERENCES topics(id)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_topics_status ON topics(status);
CREATE INDEX IF NOT EXISTS idx_topics_score ON topics(score DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_topic ON jobs(topic_id);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);