# clean base image containing only comfyui, comfy-cli and comfyui-manager
FROM runpod/worker-comfyui:5.5.0-base

USER root

# 1. Install System Dependencies (THE NUCLEAR FIX)
# "|| true" prevents the build from crashing if a random repo is 404/offline.
# Swapped "libgl1-mesa-glx" -> "libgl1" (Modern equivalent)
RUN apt-get update || true && \
    apt-get install -y --no-install-recommends \
    curl \
    git \
    aria2 \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Custom Nodes (Combined for speed)
RUN comfy node install --exit-on-fail comfyui_essentials && \
    comfy node install --exit-on-fail comfyui-gimm-vfi && \
    comfy node install --exit-on-fail ComfyUI-mxToolkit && \
    comfy node install --exit-on-fail ComfyUI_TensorRT && \
    git clone https://github.com/orssorbit/ComfyUI-wanBlockswap custom_nodes/ComfyUI-wanBlockswap && \
    comfy node install --exit-on-fail was-node-suite-comfyui && \
    comfy node install --exit-on-fail ComfyUI-KJNodes && \
    comfy node install --exit-on-fail ComfyUI-Easy-Use && \
    comfy node install --exit-on-fail rgthree-comfy && \
    comfy node install --exit-on-fail ComfyUI-Frame-Interpolation && \
    comfy node install --exit-on-fail ComfyUI-Florence2 && \
    comfy node install --exit-on-fail comfyui-videohelpersuite

# 3. Download Models using ARIA2 (16x Faster)
# T5 Encoder & VAE
RUN aria2c -x 16 -s 16 -k 1M -d models/clip -o umt5_xxl_fp8_e4m3fn_scaled.safetensors "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors" && \
    aria2c -x 16 -s 16 -k 1M -d models/vae -o wan_2.1_vae.safetensors "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors"

# Wan 2.1 Models (CivitAI)
RUN aria2c -x 16 -s 16 -k 1M -d models/unet -o smoothMixWan22I2VT2V_i2vHigh.safetensors "https://civitai.com/api/download/models/2260110?token=fe236ecdc4737a4ab46bdbf26228fb14" && \
    aria2c -x 16 -s 16 -k 1M -d models/unet -o smoothMixWan22I2VT2V_i2vLow.safetensors "https://civitai.com/api/download/models/2259006?token=fe236ecdc4737a4ab46bdbf26228fb14"

# Interpolation Models
RUN aria2c -x 16 -s 16 -k 1M -d models/interpolation/gimm-vfi -o gimmvfi_f_arb_lpips_fp32.safetensors "https://huggingface.co/Kijai/GIMM-VFI_safetensors/resolve/f06ecc593e175188d71d8c31c86bce83696430e5/gimmvfi_f_arb_lpips_fp32.safetensors" && \
    aria2c -x 16 -s 16 -k 1M -d custom_nodes/ComfyUI-Frame-Interpolation/ckpts/rife -o rife47.pth "https://huggingface.co/jasonot/mycomfyui/resolve/main/rife47.pth"

# 4. Copy Handler
COPY rp_handler.py /rp_handler.py

CMD ["/start.sh"]
