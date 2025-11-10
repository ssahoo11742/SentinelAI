from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import paramiko
import logging
import os
import sys
import time
from typing import List
import tempfile
from dotenv import load_dotenv

load_dotenv()

# ---------------------------
# CONFIG
# ---------------------------
SUPABASE_URL = "https://uxrdywchpcwljsteomtn.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "your-default-supabase-key")
print(SUPABASE_KEY)
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
STORAGE_BUCKET = "sentinel_reports"

# SSH Configuration
SSH_HOST = "129.213.118.220"
SSH_USER = "ubuntu"
SSH_KEY_PATH = r"./ssh-key-watchtower.key"
REMOTE_PIPELINE_PATH = "~/SentinelAI/server/api/pipeline/pipeline.py"
REMOTE_OUTPUT_DIR = "~/SentinelAI/server/api/output"

os.makedirs(OUTPUT_DIR, exist_ok=True)

from supabase import create_client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sentinel-api")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://sentinel-ai-web.netlify.app", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# MODELS
# ---------------------------

class CustomRun(BaseModel):
    platforms: List[str] = ["manifold", "polymarket"]
    min_liquidity: float = 500
    max_hours: int = 720
    extra_args: List[str] = []

# ---------------------------
# HELPER FUNCTIONS
# ---------------------------

def upload_csv_to_supabase(job_id: str, filepath: str) -> str:
    """Upload a CSV file to Supabase storage"""
    storage_filename = f"{job_id}_{os.path.basename(filepath)}"
    with open(filepath, "rb") as f:
        supabase.storage.from_(STORAGE_BUCKET).upload(
            storage_filename, 
            f, 
            file_options={"content-type": "text/csv"}
        )
    return f"{STORAGE_BUCKET}/{storage_filename}"

def mark_job_status(job_id: str, status: str, storage_path: str = None, error: str = None):
    """Update job status in Supabase"""
    update_data = {"status": status}
    if storage_path:
        update_data["storage_path"] = storage_path
    if error:
        update_data["error"] = error
    supabase.table("pipeline_jobs").update(update_data).eq("id", job_id).execute()

def create_ssh_client():
    """Create and return an SSH client connected to the VM"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(
            hostname=SSH_HOST,
            username=SSH_USER,
            key_filename=SSH_KEY_PATH,
            timeout=30
        )
        return client
    except Exception as e:
        logger.error(f"SSH connection failed: {e}")
        raise

def execute_remote_pipeline(ssh_client, config: CustomRun) -> str:
    """Execute the pipeline on the remote VM and return the output CSV filename"""
    
    # Build the command to run the pipeline
    platforms_str = ",".join(config.platforms)
    command = (
  f"cd ~/SentinelAI/server/api && "
        f"python3 -m pipeline.pipeline "
        f"--platforms {platforms_str} "
        f"--min-liquidity {config.min_liquidity} "
        f"--max-hours {config.max_hours}"
    )
    
    # Add extra arguments if provided
    if config.extra_args:
        command += " " + " ".join(config.extra_args)
    
    logger.info(f"Executing remote command: {command}")
    
    # Execute the command
    stdin, stdout, stderr = ssh_client.exec_command(command)
    
    # Wait for command to complete and get output
    exit_status = stdout.channel.recv_exit_status()
    output = stdout.read().decode('utf-8')
    error = stderr.read().decode('utf-8')
    
    if exit_status != 0:
        logger.error(f"Remote pipeline failed with exit code {exit_status}")
        logger.error(f"Error output: {error}")
        raise RuntimeError(f"Pipeline execution failed: {error}")
    
    logger.info(f"Pipeline output: {output}")
    
    # Find the latest CSV file in the remote output directory
    list_cmd = f"ls -t {REMOTE_OUTPUT_DIR}/*.csv | head -1"
    stdin, stdout, stderr = ssh_client.exec_command(list_cmd)
    latest_csv = stdout.read().decode('utf-8').strip()
    
    if not latest_csv:
        raise RuntimeError("No CSV output found on remote server")
    
    return latest_csv

def download_file_from_vm(ssh_client, remote_path: str, local_path: str):
    """Download a file from the VM using SFTP"""
    sftp = ssh_client.open_sftp()
    try:
        sftp.get(remote_path, local_path)
        logger.info(f"Downloaded {remote_path} to {local_path}")
    finally:
        sftp.close()

# ---------------------------
# PIPELINE RUNNER
# ---------------------------

def run_tracked_pipeline(job_id: str, config: CustomRun):
    """Run the pipeline on the remote VM via SSH"""
    logger.info(f"[JOB:{job_id}] Starting remote pipeline for platforms: {config.platforms}")
    mark_job_status(job_id, "running")
    
    ssh_client = None
    try:
        # Connect to VM
        logger.info(f"[JOB:{job_id}] Connecting to VM at {SSH_HOST}")
        ssh_client = create_ssh_client()
        
        # Execute pipeline on remote VM
        logger.info(f"[JOB:{job_id}] Executing pipeline on remote VM")
        remote_csv_path = execute_remote_pipeline(ssh_client, config)
        
        # Download the CSV file
        local_csv_path = os.path.join(OUTPUT_DIR, f"job_{job_id}_{os.path.basename(remote_csv_path)}")
        logger.info(f"[JOB:{job_id}] Downloading result from {remote_csv_path}")
        download_file_from_vm(ssh_client, remote_csv_path, local_csv_path)
        
        # Upload to Supabase storage
        logger.info(f"[JOB:{job_id}] Uploading to Supabase storage")
        storage_path = upload_csv_to_supabase(job_id, local_csv_path)
        
        mark_job_status(job_id, "completed", storage_path=storage_path)
        logger.info(f"[JOB:{job_id}] Completed successfully. Stored at: {storage_path}")
        
        # Clean up local file
        try:
            os.remove(local_csv_path)
        except Exception as e:
            logger.warning(f"Failed to clean up local file: {e}")
        
    except Exception as e:
        logger.error(f"[JOB:{job_id}] Failed: {e}")
        mark_job_status(job_id, "failed", error=str(e))
    finally:
        if ssh_client:
            ssh_client.close()
            logger.info(f"[JOB:{job_id}] SSH connection closed")

# ---------------------------
# ROUTES
# ---------------------------

@app.post("/custom")
async def run_custom(config: CustomRun, background_tasks: BackgroundTasks):
    """Run a custom pipeline job with specified parameters"""
    if not config.platforms:
        raise HTTPException(status_code=400, detail="Platforms list cannot be empty")
    
    job = supabase.table("pipeline_jobs").insert({
        "status": "pending", 
        "command": str(config)
    }).execute()
    job_id = job.data[0]["id"]
    
    background_tasks.add_task(run_tracked_pipeline, job_id, config)
    return {"job_id": job_id, "status": "started", "platforms": config.platforms}

@app.get("/jobs")
async def get_jobs():
    """Get all pipeline jobs"""
    result = supabase.table("pipeline_jobs").select("*").order("created_at", desc=True).execute()
    return result.data

@app.get("/health")
def health():
    """Health check endpoint"""
    return {"status": "ok"}

@app.post("/update")
async def run_default_update(background_tasks: BackgroundTasks):
    """Run the default update job"""
    config = CustomRun(
        platforms=["manifold", "polymarket"],
        min_liquidity=1155,
        max_hours=30000,
        extra_args=[]
    )
    
    job = supabase.table("pipeline_jobs").insert({
        "status": "pending", 
        "command": str(config)
    }).execute()
    job_id = job.data[0]["id"]
    
    background_tasks.add_task(run_tracked_pipeline, job_id, config)
    return {"job_id": job_id, "status": "started", "platforms": config.platforms}

@app.get("/test-ssh")
async def test_ssh():
    """Test SSH connection to the VM"""
    try:
        ssh_client = create_ssh_client()
        stdin, stdout, stderr = ssh_client.exec_command("echo 'SSH connection successful'")
        output = stdout.read().decode('utf-8').strip()
        ssh_client.close()
        return {"status": "success", "message": output}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ---------------------------
# RUN SERVER
# ---------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
