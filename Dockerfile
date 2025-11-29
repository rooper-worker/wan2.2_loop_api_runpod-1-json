# clean base image containing only comfyui, comfy-cli and comfyui-manager
FROM runpod/worker-comfyui:5.5.0-base

# install custom nodes into comfyui
RUN comfy node install --exit-on-fail comfyui_essentials

# download models into comfyui
RUN comfy model download --url https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors --relative-path models/clip --filename umt5_xxl_fp8_e4m3fn_scaled.safetensors
RUN comfy model download --url https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors --relative-path models/vae --filename wan_2.1_vae.safetensors
RUN comfy model download --url https://civitai.com/api/download/models/2260110?token=fe236ecdc4737a4ab46bdbf26228fb14 --relative-path models/unet --filename smoothMixWan22I2VT2V_i2vHigh.safetensors
RUN comfy model download --url https://civitai.com/api/download/models/2259006?token=fe236ecdc4737a4ab46bdbf26228fb14 --relative-path models/unet --filename smoothMixWan22I2VT2V_i2vLow.safetensors
RUN comfy model download --url https://huggingface.co/Kijai/GIMM-VFI_safetensors/blob/f06ecc593e175188d71d8c31c86bce83696430e5/gimmvfi_f_arb_lpips_fp32.safetensors --relative-path models/interpolation/gimm-vfi --filename gimmvfi_f_arb_lpips_fp32.safetensors

# copy all input data (like images or videos) into comfyui (uncomment and adjust if needed)
# COPY input/ /comfyui/input/
