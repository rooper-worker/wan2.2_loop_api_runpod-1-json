import runpod
import json
import os
import shutil
import time
import requests
import base64
import boto3
import torch
import gc
from botocore.exceptions import NoCredentialsError

COMFY_URL = "http://127.0.0.1:8188"
WORKFLOW_FILE = "WAN2.2_LOOP.json" 
OUTPUT_DIR = "/comfyui/output"

AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
BUCKET_NAME = os.environ.get("BUCKET_NAME")
ENDPOINT_URL = os.environ.get("ENDPOINT_URL") 
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "https://pub-7d6e5b999fdf478c9d8bb0283bf1bf0e.r2.dev")

def setup_paths():
    # *** VOLUME IS MOUNTED HERE ***
    VOLUME_ROOT = "/workspace/models"
    COMFY_ROOT = "/comfyui"

    mappings = [
        ("unet", "models/unet"),
        ("vae", "models/vae"),
        ("clip", "models/clip"),
        ("interpolation/gimm-vfi", "models/interpolation/gimm-vfi"),
        ("LLM", "models/LLM"),
        ("upscale_models", "models/upscale_models"),
        ("tensorrt", "models/tensorrt"),
    ]

    print("--- Setting up Network Volume Symlinks ---")
    
    for vol_folder, comfy_folder in mappings:
        src = os.path.join(VOLUME_ROOT, vol_folder)
        dst = os.path.join(COMFY_ROOT, comfy_folder)
        
        os.makedirs(os.path.dirname(dst), exist_ok=True)

        if os.path.exists(src):
            if os.path.exists(dst):
                if os.path.islink(dst):
                    os.unlink(dst)
                elif os.path.isdir(dst):
                    shutil.rmtree(dst)
            
            try:
                os.symlink(src, dst)
                print(f"✅ Linked {src} -> {dst}")
            except Exception as e:
                print(f"❌ Failed to link {src}: {e}")
        else:
            print(f"⚠️ Warning: Volume path {src} does not exist.")

    rife_vol = os.path.join(VOLUME_ROOT, "interpolation/rife")
    rife_container = os.path.join(COMFY_ROOT, "custom_nodes/ComfyUI-Frame-Interpolation/ckpts/rife")
    
    if os.path.exists(rife_vol):
        os.makedirs(os.path.dirname(rife_container), exist_ok=True)
        if os.path.exists(rife_container):
            shutil.rmtree(rife_container)
        os.symlink(rife_vol, rife_container)
        print(f"✅ Linked RIFE: {rife_vol} -> {rife_container}")
    else:
        print(f"⚠️ Warning: RIFE volume path {rife_vol} not found")

    print("--- Symlinks Complete ---")

setup_paths()

def upload_to_s3(file_path, object_name):
    s3 = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        endpoint_url=ENDPOINT_URL
    )
    try:
        s3.upload_file(file_path, BUCKET_NAME, object_name)
        return f"{PUBLIC_BASE_URL}/{object_name}"
    except Exception as e:
        print(f"Upload failed: {str(e)}")
        return None

def check_server(url):
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
    job_input = job["input"]
    
    image_base64 = job_input.get("image")
    duration = float(job_input.get("duration", 4.0))

    if not image_base64:
        return {"error": "No image provided"}

    if not check_server(COMFY_URL):
        return {"error": "ComfyUI server did not start"}

    try:
        image_data = base64.b64decode(image_base64.split(",")[-1])
        upload_response = requests.post(
            f"{COMFY_URL}/upload/image",
            files={"image": ("input_image.png", image_data)}
        )
        filename = upload_response.json().get("name")
    except Exception as e:
        return {"error": f"Failed to upload image to ComfyUI: {e}"}

    with open(WORKFLOW_FILE, "r") as f:
        workflow = json.load(f)

    workflow["426"]["inputs"]["Xi"] = duration
    workflow["426"]["inputs"]["Xf"] = duration
    workflow["516"]["inputs"]["image"] = filename
    
    workflow["82"]["inputs"]["Xi"] = 12
    workflow["82"]["inputs"]["Xf"] = 12
    workflow["85"]["inputs"]["Xi"] = 1.0
    workflow["85"]["inputs"]["Xf"] = 1.0
    workflow["490"]["inputs"]["Xi"] = 16
    workflow["490"]["inputs"]["Xf"] = 16
    workflow["556"]["inputs"]["Xi"] = 512
    workflow["556"]["inputs"]["Xf"] = 512

    p = {"prompt": workflow}
    response = requests.post(f"{COMFY_URL}/prompt", json=p)
    prompt_id = response.json()["prompt_id"]

    while True:
        try:
            history_res = requests.get(f"{COMFY_URL}/history/{prompt_id}")
            history = history_res.json()
            if prompt_id in history:
                break
            time.sleep(1)
        except Exception:
            time.sleep(1)

    outputs = history[prompt_id]["outputs"]
    video_filename = None
    for node_id in outputs:
        node_output = outputs[node_id]
        if "gifs" in node_output:
            video_filename = node_output["gifs"][0]["filename"]
        elif "videos" in node_output:
            video_filename = node_output["videos"][0]["filename"]
            
    if not video_filename:
        return {"error": "No output video found"}

    local_path = f"{OUTPUT_DIR}/{video_filename}"
    cloud_url = upload_to_s3(local_path, f"rooper_{prompt_id}.mp4")

    gc.collect()
    torch.cuda.empty_cache()
    torch.cuda.ipc_collect()

    return {"status": "success", "video_url": cloud_url}

runpod.serverless.start({"handler": handler})
