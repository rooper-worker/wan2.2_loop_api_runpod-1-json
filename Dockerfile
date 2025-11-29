# clean base image containing only comfyui, comfy-cli and comfyui-manager
FROM runpod/worker-comfyui:5.5.0-base

# 1. Install System Dependencies (Fixes the "command not found" error)
RUN apt-get update && apt-get install -y curl git libgl1-mesa-glx libglib2.0-0

# 2. Install Custom Nodes
RUN comfy node install --exit-on-fail comfyui_essentials
RUN comfy node install --exit-on-fail comfyui-gimm-vfi
RUN comfy node install --exit-on-fail ComfyUI-mxToolkit
RUN comfy node install --exit-on-fail ComfyUI_TensorRT
RUN git clone https://github.com/orssorbit/ComfyUI-wanBlockswap custom_nodes/ComfyUI-wanBlockswap
RUN comfy node install --exit-on-fail was-node-suite-comfyui
RUN comfy node install --exit-on-fail ComfyUI-KJNodes
RUN comfy node install --exit-on-fail ComfyUI-Easy-Use
RUN comfy node install --exit-on-fail rgthree-comfy
RUN comfy node install --exit-on-fail ComfyUI-Frame-Interpolation
RUN comfy node install --exit-on-fail ComfyUI-Florence2
RUN comfy node install --exit-on-fail comfyui-videohelpersuite

# 3. Download Models (Fixes the "exit code 23" error)
RUN comfy model download --url https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors --relative-path models/clip --filename umt5_xxl_fp8_e4m3fn_scaled.safetensors
RUN comfy model download --url https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors --relative-path models/vae --filename wan_2.1_vae.safetensors

RUN curl -L --retry 5 --retry-delay 5 --create-dirs -A "Mozilla/5.0" \
  "https://civitai.com/api/download/models/2260110?token=fe236ecdc4737a4ab46bdbf26228fb14" \
  -o models/unet/smoothMixWan22I2VT2V_i2vHigh.safetensors

RUN curl -L --retry 5 --retry-delay 5 --create-dirs -A "Mozilla/5.0" \
  "https://civitai.com/api/download/models/2259006?token=fe236ecdc4737a4ab46bdbf26228fb14" \
  -o models/unet/smoothMixWan22I2VT2V_i2vLow.safetensors

RUN comfy model download --url https://huggingface.co/Kijai/GIMM-VFI_safetensors/resolve/f06ecc593e175188d71d8c31c86bce83696430e5/gimmvfi_f_arb_lpips_fp32.safetensors --relative-path models/interpolation/gimm-vfi --filename gimmvfi_f_arb_lpips_fp32.safetensors
RUN comfy model download --url https://huggingface.co/jasonot/mycomfyui/resolve/main/rife47.pth --relative-path custom_nodes/ComfyUI-Frame-Interpolation/ckpts/rife --filename rife47.pth

# 4. COPY YOUR HANDLER (Crucial step the Professor missed)
# This assumes rp_handler.py is in the same folder as your Dockerfile on your PC
COPY rp_handler.py /rp_handler.py

# 5. Set the entrypoint (The base image usually handles this, but explicit is safer)
# If your rp_handler.py expects to control the start, ensure the CMD points to the base image's start script
# which usually looks for the handler.
CMD ["/start.sh"]
