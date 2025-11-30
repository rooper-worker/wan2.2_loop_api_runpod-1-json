import runpod
import json
import os
import subprocess
import time
import requests
import base64
import boto3
import torch
import gc
from botocore.exceptions import NoCredentialsError

# --- CONFIGURATION ---
COMFY_URL = "http://127.0.0.1:8188"
WORKFLOW_FILE = "WAN2.2_LOOP.json" # Ensure this file is in the root of your container/repo
OUTPUT_DIR = "/comfyui/output"     # Standard output path in the runpod base image

# AWS / S3 / R2 Configuration
AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
BUCKET_NAME = os.environ.get("BUCKET_NAME")
ENDPOINT_URL = os.environ.get("ENDPOINT_URL") # e.g. https://<account>.r2.cloudflarestorage.com
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "https://pub-7d6e5b999fdf478c9d8bb0283bf1bf0e.r2.dev")

# ==============================================================================
# 1. RUNTIME DOWNLOADER (Runs once when the worker starts)
# ==============================================================================

def download_file(url, path, filename):
    full_path = os.path.join(path, filename)
    if not os.path.exists(full_path):
        print(f"Downloading {filename}...")
        os.makedirs(path, exist_ok=True)
        try:
            subprocess.run([
                "aria2c", "-x", "16", "-s", "16", "-k", "1M",
                "-d", path, "-o", filename, url
            ], check=True)
            print(f"Finished downloading {filename}")
        except subprocess.CalledProcessError as e:
            print(f"Failed to download {filename}: {e}")
    else:
        print(f"Found {filename}, skipping download.")

# Define your models here
models_to_download = [
    # T5 Encoder
    {
        "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors",
        "path": "models/clip",
        "filename": "umt5_xxl_fp8_e4m3fn_scaled.safetensors"
    },
    # VAE
    {
        "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors",
        "path": "models/vae",
        "filename": "wan_2.1_vae.safetensors"
    },
    # Wan 2.1 High (14GB)
    {
        "url": "https://civitai.com/api/download/models/2260110?token=fe236ecdc4737a4ab46bdbf26228fb14",
        "path": "models/unet",
        "filename": "smoothMixWan22I2VT2V_i2vHigh.safetensors"
    },
    # Wan 2.1 Low (8GB) - Optional, but good to have since download is fast now
    {
        "url": "https://civitai.com/api/download/models/2259006?token=fe236ecdc4737a4ab46bdbf26228fb14",
        "path": "models/unet",
        "filename": "smoothMixWan22I2VT2V_i2vLow.safetensors"
    }
]

print("--- Checking Model Files (Runtime) ---")
for model in models_to_download:
    download_file(model["url"], model["path"], model["filename"])
print("--- Model Check Complete ---")


# ==============================================================================
# 2. HELPER FUNCTIONS
# ==============================================================================

def upload_to_s3(file_path, object_name):
    """Uploads to R2/S3 and returns the PUBLIC playable URL"""
    s3 = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        endpoint_url=ENDPOINT_URL
    )
    try:
        s3.upload_file(file_path, BUCKET_NAME, object_name)
        # Return the public URL
        return f"{PUBLIC_BASE_URL}/{object_name}"
        
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return None
    except NoCredentialsError:
        print("Credentials not available")
        return None
    except Exception as e:
        print(f"Upload failed: {str(e)}")
        return None

def check_server(url):
    """Waits for ComfyUI to start up"""
    retries = 0
    while retries < 30:
        try:
            requests.get(url)
            return True
        except requests.exceptions.ConnectionError:
            time.sleep(1)
            retries += 1
    return False

# ==============================================================================
# 3. MAIN HANDLER
# ==============================================================================

def handler(job):
    """The main function called by RunPod"""
    job_input = job["input"]
    
    # 1. Inputs from your Next.js Frontend
    image_base64 = job_input.get("image")
    duration = float(job_input.get("duration", 4.0))

    if not image_base64:
        return {"error": "No image provided"}

    # 2. Wait for ComfyUI to be ready
    if not check_server(COMFY_URL):
        return {"error": "ComfyUI server did not start"}

    # 3. Save Input Image to ComfyUI Input Directory
    # We decode the base64 image and upload it to ComfyUI via API
    try:
        image_data = base64.b64decode(image_base64.split(",")[-1])
        upload_response = requests.post(
            f"{COMFY_URL}/upload/image",
            files={"image": ("input_image.png", image_data)}
        )
        filename = upload_response.json().get("name")
    except Exception as e:
        return {"error": f"Failed to upload image to ComfyUI: {e}"}

    # 4. Load and Modify Workflow
    try:
        with open(WORKFLOW_FILE, "r") as f:
            workflow = json.load(f)
    except FileNotFoundError:
        return {"error": f"Workflow file {WORKFLOW_FILE} not found"}

    # --- MAPPING YOUR JSON ---
    # Duration (Node 426)
    workflow["426"]["inputs"]["Xi"] = duration
    workflow["426"]["inputs"]["Xf"] = duration
    
    # Start Image (Node 516)
    workflow["516"]["inputs"]["image"] = filename
    
    # Locked Settings (Hardcoded for Consistency)
    workflow["82"]["inputs"]["Xi"] = 12   # Steps
    workflow["82"]["inputs"]["Xf"] = 12
    workflow["85"]["inputs"]["Xi"] = 1.0  # CFG
    workflow["85"]["inputs"]["Xf"] = 1.0
    workflow["490"]["inputs"]["Xi"] = 16  # FPS
    workflow["490"]["inputs"]["Xf"] = 16
    workflow["556"]["inputs"]["Xi"] = 512 # Height
    workflow["556"]["inputs"]["Xf"] = 512
    # --------------------------------------------------

    # 5. Queue Prompt
    try:
        p = {"prompt": workflow}
        response = requests.post(f"{COMFY_URL}/prompt", json=p)
        prompt_id = response.json()["prompt_id"]
    except Exception as e:
        return {"error": f"Failed to queue prompt: {e}"}

    # 6. Wait for Execution
    # Poll the history endpoint until the prompt_id appears
    while True:
        try:
            history_res = requests.get(f"{COMFY_URL}/history/{prompt_id}")
            history = history_res.json()
            if prompt_id in history:
                break
            time.sleep(1)
        except Exception:
            time.sleep(1)

    # 7. Retrieve Output Filename
    # WAN2.2_LOOP usually outputs to VHS_VideoCombine (Node 398 or 551)
    outputs = history[prompt_id]["outputs"]
    
    video_filename = None
    for node_id in outputs:
        node_output = outputs[node_id]
        if "gifs" in node_output:
            video_filename = node_output["gifs"][0]["filename"]
        elif "videos" in node_output:
            video_filename = node_output["videos"][0]["filename"]
            
    if not video_filename:
        return {"error": "No output video found in ComfyUI history"}

    # 8. Upload Result to Cloud Storage
    local_path = f"{OUTPUT_DIR}/{video_filename}"
    cloud_url = upload_to_s3(local_path, f"rooper_{prompt_id}.mp4")

    if not cloud_url:
        return {"error": "Failed to upload to storage"}
    
    # 9. HARDENING: Cleanup Memory
    # This prevents the worker from crashing after multiple runs
    gc.collect()
    torch.cuda.empty_cache()
    torch.cuda.ipc_collect()

    return {"status": "success", "video_url": cloud_url}

runpod.serverless.start({"handler": handler})
