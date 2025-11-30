import os
import subprocess
import time

# --- RUNTIME DOWNLOADER ---
def download_file(url, path, filename):
    full_path = os.path.join(path, filename)
    if not os.path.exists(full_path):
        print(f"Downloading {filename}...")
        # Ensure directory exists
        os.makedirs(path, exist_ok=True)
        # Run aria2c
        subprocess.run([
            "aria2c", "-x", "16", "-s", "16", "-k", "1M",
            "-d", path, "-o", filename, url
        ], check=True)
        print(f"Finished downloading {filename}")
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
    # Wan 2.1 High
    {
        "url": "https://civitai.com/api/download/models/2260110?token=fe236ecdc4737a4ab46bdbf26228fb14",
        "path": "models/unet",
        "filename": "smoothMixWan22I2VT2V_i2vHigh.safetensors"
    },
    # Wan 2.1 Low (Now you can have BOTH because download time doesn't kill the build!)
    {
        "url": "https://civitai.com/api/download/models/2259006?token=fe236ecdc4737a4ab46bdbf26228fb14",
        "path": "models/unet",
        "filename": "smoothMixWan22I2VT2V_i2vLow.safetensors"
    }
]

print("--- Checking Model Files ---")
for model in models_to_download:
    try:
        download_file(model["url"], model["path"], model["filename"])
    except Exception as e:
        print(f"Failed to download {model['filename']}: {e}")
print("--- Model Check Complete ---")

# --- END DOWNLOADER ---

# ... The rest of your rp_handler code goes here ...
def handler(job):
    # ...
