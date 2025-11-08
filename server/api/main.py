from fastapi import FastAPI, BackgroundTasks, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client
import uvicorn
import logging
import subprocess
import uuid
import os
import time
import pandas as pd

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

SUPABASE_URL = "https://uxrdywchpcwljsteomtn.supabase.co"
SUPABASE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InV4cmR5d2NocGN3bGpzdGVvbXRuIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MjEyMDUzMywiZXhwIjoyMDc3Njk2NTMzfQ.jaQvrFqm4wTOyS_XxaUzCM1REtEyh-9Sj1EDFNjKJ8g"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

OUTPUT_DIR = "."        # where pipeline writes results
STORAGE_BUCKET = "sentinel_reports"  # Supabase bucket

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sentinel-api")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# MODELS
# --------------------------------------------------

class CustomRun(BaseModel):
    platforms: list[str] = ["manifold", "polymarket"]
    min_liquidity: float = 500
    max_hours: int = 720
    extra_args: list[str] = []


# --------------------------------------------------
# TRACKED PIPELINE RUNNER
# --------------------------------------------------

def run_tracked_pipeline(job_id: str, cmd: str):
    logger.info(f"[JOB:{job_id}] Marking job running...")
    supabase.table("pipeline_jobs").update({"status": "running"}).eq("id", job_id).execute()

    try:
        logger.info(f"[JOB:{job_id}] Executing: {cmd}")
        subprocess.run(cmd, shell=True, check=False)

        # wait a moment for output to appear
        time.sleep(2)

        # find latest result file
        latest_file = None
        if os.path.exists(OUTPUT_DIR):
            files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith(".csv")]
            if files:
                files.sort(key=lambda x: os.path.getctime(os.path.join(OUTPUT_DIR, x)), reverse=True)
                latest_file = os.path.join(OUTPUT_DIR, files[0])

        storage_path = None
        if latest_file:
            storage_filename = f"{job_id}_{os.path.basename(latest_file)}"

            # Upload file to supabase storage bucket
            supabase.storage.from_(STORAGE_BUCKET).upload(
                storage_filename,
                file=open(latest_file, "rb"),
                file_options={"content-type": "text/csv"}
            )

            # This is the public or retrievable bucket path
            storage_path = f"{STORAGE_BUCKET}/{storage_filename}"


        supabase.table("pipeline_jobs").update({
            "status": "completed",
            "storage_path": storage_path
        }).eq("id", job_id).execute()

        logger.info(f"[JOB:{job_id}] Completed ✅ Stored: {storage_path}")

    except Exception as e:
        logger.error(f"[JOB:{job_id}] Failed ❌ {e}")
        supabase.table("pipeline_jobs").update({
            "status": "failed",
            "error": str(e)
        }).eq("id", job_id).execute()


# --------------------------------------------------
# ROUTES
# --------------------------------------------------

@app.post("/update")
async def run_default_update(background_tasks: BackgroundTasks):

    cmd = (
        "python -m pipeline.pipeline "
        "--platforms manifold polymarket "
        "--min-liquidity 1155 "
        "--max-hours 30000"
    )

    job = supabase.table("pipeline_jobs").insert({
        "command": cmd,
        "status": "pending"
    }).execute()

    job_id = job.data[0]["id"]

    background_tasks.add_task(run_tracked_pipeline, job_id, cmd)

    return {"job_id": job_id, "status": "started", "command": cmd}


@app.post("/custom")
async def run_custom(config: CustomRun, background_tasks: BackgroundTasks):

    if not config.platforms:
        raise HTTPException(status_code=400, detail="Platforms list cannot be empty")

    platforms_str = " ".join(config.platforms)
    extra = " ".join(config.extra_args)

    cmd = (
        f"python -m pipeline.pipeline "
        f"--platforms {platforms_str} "
        f"--min-liquidity {config.min_liquidity} "
        f"--max-hours {config.max_hours} {extra}"
    )

    job = supabase.table("pipeline_jobs").insert({
        "command": cmd,
        "status": "pending"
    }).execute()

    job_id = job.data[0]["id"]

    background_tasks.add_task(run_tracked_pipeline, job_id, cmd)

    return {"job_id": job_id, "status": "started", "command": cmd}


@app.get("/jobs")
async def get_jobs():
    result = supabase.table("pipeline_jobs").select("*").order("created_at", desc=True).execute()
    return result.data


@app.get("/health")
def health():
    return {"status": "ok"}


# --------------------------------------------------
# RUN SERVER
# --------------------------------------------------

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
