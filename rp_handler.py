import runpod
import json
import os
import time
import requests
import base64
import boto3
from botocore.exceptions import NoCredentialsError

# --- CONFIGURATION ---
COMFY_URL = "http://127.0.0.1:8188"
WORKFLOW_FILE = "WAN2.2_LOOP.json" # Ensure this file is in your repo
OUTPUT_DIR = "/comfyui/output"      # Standard ComfyUI output path in container

# AWS / S3 / R2 Configuration (Set these as ENV Variables in RunPod Dashboard)
AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
BUCKET_NAME = os.environ.get("BUCKET_NAME")
ENDPOINT_URL = os.environ.get("ENDPOINT_URL") # e.g. https://<account>.r2.cloudflarestorage.com

def upload_to_s3(file_path, object_name):
    """Uploads the generated video to S3/R2 and returns the URL"""
    s3 = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        endpoint_url=ENDPOINT_URL
    )
    try:
        s3.upload_file(file_path, BUCKET_NAME, object_name)
        # Construct public URL (Adjust based on your storage provider)
        # For R2/S3 usually: https://bucket.endpoint/object
        # You might need a public custom domain here if your bucket isn't public
        url = f"{ENDPOINT_URL}/{BUCKET_NAME}/{object_name}"
        return url.replace(f"{BUCKET_NAME}/", "") if "r2" in ENDPOINT_URL else url 
    except FileNotFoundError:
        return None
    except NoCredentialsError:
        return "Credentials not available"

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
    # Serverless containers usually have Comfy at /comfyui or /workspace/ComfyUI
    # We upload via API to be safe
    image_data = base64.b64decode(image_base64.split(",")[-1])
    
    upload_response = requests.post(
        f"{COMFY_URL}/upload/image",
        files={"image": ("input_image.png", image_data)}
    )
    filename = upload_response.json().get("name")

    # 4. Load and Modify Workflow
    with open(WORKFLOW_FILE, "r") as f:
        workflow = json.load(f)

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

    # 5. Clear previous outputs (Optional but good for serverless hygiene)
    # (Skipping for brevity, container usually clean)

    # 6. Queue Prompt
    p = {"prompt": workflow}
    response = requests.post(f"{COMFY_URL}/prompt", json=p)
    prompt_id = response.json()["prompt_id"]

    # 7. Wait for Execution
    # We poll the history endpoint until the prompt_id appears
    while True:
        history_res = requests.get(f"{COMFY_URL}/history/{prompt_id}")
        history = history_res.json()
        if prompt_id in history:
            break
        time.sleep(1)

    # 8. Retrieve Output Filename
    # WAN2.2_LOOP usually outputs to VHS_VideoCombine (Node 398 or 551)
    outputs = history[prompt_id]["outputs"]
    
    # Find the video output. We look for 'gifs' or 'videos' in the output node
    video_filename = None
    for node_id in outputs:
        node_output = outputs[node_id]
        if "gifs" in node_output:
            video_filename = node_output["gifs"][0]["filename"]
        elif "videos" in node_output:
            video_filename = node_output["videos"][0]["filename"]
            
    if not video_filename:
        return {"error": "No output video found"}

    # 9. Upload Result to Cloud Storage
    # The file is physically located at /comfyui/output/{video_filename}
    local_path = f"{OUTPUT_DIR}/{video_filename}"
    cloud_url = upload_to_s3(local_path, f"rooper_{prompt_id}.mp4")

    if not cloud_url:
        return {"error": "Failed to upload to storage"}

    return {"status": "success", "video_url": cloud_url}

runpod.serverless.start({"handler": handler})
