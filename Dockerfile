FROM runpod/worker-comfyui:5.5.0-base

USER root

RUN apt-get update || true && \
    apt-get install -y --no-install-recommends curl git aria2 libgl1 libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

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

COPY rp_handler.py /rp_handler.py
COPY WAN2.2_LOOP.json /WAN2.2_LOOP.json

CMD ["/start.sh"]
