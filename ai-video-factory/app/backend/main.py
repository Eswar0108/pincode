"""AI Video Factory — FastAPI backend.

Provides REST API for topic discovery, job management, and video rendering.
Wraps the existing Node/Remotion renderer as the video composer.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.backend.db import dict_from_row, get_connection, init_db
from app.topic_collector.collector import collect_topics, get_topics, select_topics

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

FACTORY_ROOT = Path(__file__).resolve().parent.parent.parent
REMOITION_DIR = FACTORY_ROOT.parent / "Ai_Video_Creator"
PROJECTS_DIR = FACTORY_ROOT / "projects"
PROJECTS_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="AI Video Factory", version="0.1.0")


@app.on_event("startup")
def _startup() -> None:
    init_db()
    print("[backend] Database initialized")


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class CollectRequest(BaseModel):
    limit: int = 100


class SelectRequest(BaseModel):
    topic_ids: list[str]


class JobResponse(BaseModel):
    id: str
    topic_id: str
    status: str
    output_path: str | None = None
    created_at: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "AI Video Factory", "version": "0.1.0", "status": "running"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.post("/collect")
async def collect(req: CollectRequest) -> dict[str, Any]:
    """Step 1-4: Discover, score, and select trending topics."""
    result = await collect_topics(limit=req.limit)
    return result


@app.get("/topics")
async def list_topics(limit: int = 50, status: str | None = None) -> dict[str, Any]:
    """List topics, optionally filtered by status."""
    topics = get_topics(limit=limit, status=status)
    return {"count": len(topics), "topics": topics}


@app.post("/topics/select")
async def select_topics_endpoint(req: SelectRequest) -> dict[str, Any]:
    """Mark topics as selected for rendering."""
    changed = select_topics(req.topic_ids)
    return {"selected": changed, "topic_ids": req.topic_ids}


@app.post("/jobs", response_model=JobResponse)
async def create_job(topic_id: str) -> dict[str, Any]:
    """Create a video render job for a selected topic."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM topics WHERE id = ?", (topic_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Topic not found")
        topic = dict_from_row(row)
    finally:
        conn.close()

    job_id = f"job_{uuid.uuid4().hex[:12]}"
    project_dir = PROJECTS_DIR / f"video_{job_id[-6:]}"
    project_dir.mkdir(parents=True, exist_ok=True)

    # Save topic context for this job
    (project_dir / "topic.json").write_text(json.dumps(topic, indent=2))

    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO jobs (id, topic_id, status, output_path, created_at)
            VALUES (?, ?, 'queued', ?, ?)
            """,
            (
                job_id,
                topic_id,
                str(project_dir / "final.mp4"),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    # Trigger rendering asynchronously
    asyncio.create_task(_render_job(job_id, topic, project_dir))

    return {
        "id": job_id,
        "topic_id": topic_id,
        "status": "queued",
        "output_path": str(project_dir / "final.mp4"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str) -> dict[str, Any]:
    """Get job status and details."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")
        return dict_from_row(row)
    finally:
        conn.close()


@app.get("/jobs")
async def list_jobs(limit: int = 50) -> dict[str, Any]:
    """List all render jobs."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return {"count": len(rows), "jobs": [dict_from_row(r) for r in rows]}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Rendering — wraps existing Node/Remotion pipeline
# ---------------------------------------------------------------------------


async def _render_job(job_id: str, topic: dict[str, Any], project_dir: Path) -> None:
    """Background task: render a video using the existing Remotion pipeline."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE jobs SET status = 'rendering' WHERE id = ?", (job_id,)
        )
        conn.commit()
    finally:
        conn.close()

    try:
        # Build content JSON for Remotion from topic
        content = {
            "name": "listicle",
            "source": "ai-video-factory",
            "hook": f"Trending: {topic['title']}",
            "hookSubtitle": f"Source: {topic.get('source', 'unknown')} · Score: {topic.get('score', 0)}",
            "items": [
                {
                    "title": topic["title"],
                    "meta": topic.get("approx_traffic"),
                    "level": 4,
                }
            ],
            "cta": "Follow for more trending topics",
            "durationInFrames": 450,
            "fps": 30,
            "width": 1080,
            "height": 1920,
        }

        content_path = project_dir / "content.json"
        content_path.write_text(json.dumps(content, indent=2))

        # Call the existing Remotion renderer
        env = os.environ.copy()
        env["CONTENT_FILE"] = str(content_path)

        result = subprocess.run(
            [
                "npx",
                "remotion",
                "render",
                str(REMOITION_DIR / "src" / "index.ts"),
                "Contributions",
                str(project_dir / "final.mp4"),
                "--width=1080",
                "--height=1920",
                "--pixel-format=yuv420p",
                "--browser-executable=/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            ],
            cwd=str(REMOITION_DIR),
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Remotion render failed: {result.stderr}")

        # Update job as completed
        file_size = (project_dir / "final.mp4").stat().st_size if (project_dir / "final.mp4").exists() else 0
        conn = get_connection()
        try:
            conn.execute(
                """
                UPDATE jobs
                SET status = 'completed', output_path = ?, file_size_bytes = ?, completed_at = ?
                WHERE id = ?
                """,
                (
                    str(project_dir / "final.mp4"),
                    file_size,
                    datetime.now(timezone.utc).isoformat(),
                    job_id,
                ),
            )
            conn.commit()
        finally:
            conn.close()

        print(f"[backend] Job {job_id} completed: {project_dir / 'final.mp4'}")

    except Exception as exc:  # noqa: BLE001
        print(f"[backend] Job {job_id} failed: {exc}")
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE jobs SET status = 'failed', error_message = ? WHERE id = ?",
                (str(exc), job_id),
            )
            conn.commit()
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# Simple HTML dashboard
# ---------------------------------------------------------------------------


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard() -> str:
    """Simple HTML dashboard for reviewing jobs and topics."""
    return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>AI Video Factory — Dashboard</title>
    <style>
        body { font-family: system-ui, -apple-system, sans-serif; margin: 0; padding: 20px; background: #0b0d12; color: #f0f6fc; }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { font-size: 24px; margin-bottom: 20px; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; margin-bottom: 16px; }
        .card h2 { font-size: 16px; margin-top: 0; color: #58a6ff; }
        .btn { background: #2ea043; color: #fff; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-size: 14px; }
        .btn:hover { background: #2d8a3b; }
        .btn.secondary { background: #30363d; }
        table { width: 100%; bord        table { width: 100%; bord        table { width: 100%; bord        table { width: 100%; bord   om: 1px solid #30363d; }
        .status-queued { color: #d2a8ff; }
        .status-rendering { color: #58a6ff; }
        .status-completed { color: #39d353; }
        .status-failed { color: #f85149; }
        .status-pending { color: #8b949e; }
        .status-selected { color: #58a6ff; }
        .topic-score { font-family: monospace; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎬 AI Video Factory — Dashboard</h1>

        <div class="grid">
            <div class="card">
                <h2>Topic Discovery</h2>
                <button class="btn" onclick="collectTopics()">Collect Topics</button>
                <button class="btn secondary" onclick="loadTopics()">Refresh Topics</button>
                <div id="topics-list" style="margin-top: 16px;"></div>
            </div>

            <div class="card">
                <h2>Render Jobs</h2>
                <button class="btn secondary" onclick="loadJobs()">Refresh Jobs</button>
                <div id="jobs-list" style="margin-top: 16px;"></div>
            </div>
        </div>

        <script>
            async function collectTopics() {
                const res = await fetch('/collect', { method: 'POST', body: JSON.stringify({ limit: 100 }) });
                const data = await res.json();
                alert(`Collected ${data.count} topics (source: ${data.source})`);
                loadTopics();
            }

            async function loadTopics() {
                const res = await fetch('/topics?limit=20&status=pending');
                const data = await res.json();
                const el = document.getElementById('topics-list');
                el.innerHTML = '<table><thead><tr><th>Score</th><th>Title</th><th>Source</th><th>Action</th></tr></thead><tbody>' +
                    data.topics.map(t => `
                        <tr>
                            <td class="topic-score">${t.score}</td>
                            <td>${t.title}</td>
                            <td>${t.source}</td>
                            <td><button class="btn" onclick="selectAndRender('${t.id}')">Select + Render</button></td>
                        </tr>
                    `).join('') +
                    '</tbody></table>';
            }

            async function selectAndRender(topicId) {
                await fetch('/topics/select', { method: 'POST', body: JSON.stringify({ topic_ids: [topicId] }) });
                const res = await fetch('/jobs', { method: 'POST', body: JSON.stringify({ topic_id: topicId }) });
                const job = await res.json();
                alert(`Job created: ${job.id}`);
                loadJobs();
            }

            async function loadJobs() {
                const res = await fetch('/jobs?limit=20');
                const data = await res.json();
                const el = document.getElementById('jobs-list');
                el.innerHTML = '<table><thead><tr><th>Job ID</th><th>Topic</th><th>Status</th><th>Created</th></tr></thead><tbody>' +
                    data.jobs.map(j => `
                        <tr>
                            <td>${j.id}</td>
                            <td>${j.topic_id}</td>
                            <td class="status-${j.status}">${j.status}</td>
                            <td>${j.created_at}</td>
                        </tr>
                    `).join('') +
                    '</tbody></table>';
            }

            loadTopics();
            loadJobs();
        </script>
    </div>
</body>
</html>

"""
