# clean base image containing only comfyui, comfy-cli and comfyui-manager
FROM runpod/worker-comfyui:5.5.0-base

# install custom nodes into comfyui
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

# Install curl
RUN apt-get update && apt-get install -y curl

# download models into comfyui
RUN comfy model download --url https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors --relative-path models/clip --filename umt5_xxl_fp8_e4m3fn_scaled.safetensors
RUN comfy model download --url https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors --relative-path models/vae --filename wan_2.1_vae.safetensors

# --- FIX START: Added --create-dirs flag ---
RUN curl -L --retry 5 --retry-delay 5 --create-dirs -A "Mozilla/5.0" \
  "https://civitai.com/api/download/models/2260110?token=fe236ecdc4737a4ab46bdbf26228fb14" \
  -o models/unet/smoothMixWan22I2VT2V_i2vHigh.safetensors

RUN curl -L --retry 5 --retry-delay 5 --create-dirs -A "Mozilla/5.0" \
  "https://civitai.com/api/download/models/2259006?token=fe236ecdc4737a4ab46bdbf26228fb14" \
  -o models/unet/smoothMixWan22I2VT2V_i2vLow.safetensors
# --- FIX END ---

RUN comfy model download --url https://huggingface.co/Kijai/GIMM-VFI_safetensors/resolve/f06ecc593e175188d71d8c31c86bce83696430e5/gimmvfi_f_arb_lpips_fp32.safetensors --relative-path models/interpolation/gimm-vfi --filename gimmvfi_f_arb_lpips_fp32.safetensors
RUN comfy model download --url https://huggingface.co/jasonot/mycomfyui/resolve/main/rife47.pth --relative-path custom_nodes/ComfyUI-Frame-Interpolation/ckpts/rife --filename rife47.pth
