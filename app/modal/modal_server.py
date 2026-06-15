import sys
import subprocess
import time
import modal
import os

from app.modal.deployment import app, MODEL_VOLUME, MODEL_DIR
from app.modal.image import sglang_image
from app.config import settings

@app.cls(
    gpu=settings.GPU_TYPE,
    image=sglang_image,
    volumes={MODEL_DIR: MODEL_VOLUME},
    timeout=3600,
    scaledown_window=600,
)
class QwenSGLangServer:
    @modal.enter()
    def start_sglang_server(self):
        self._download_weights_if_needed()
        cmd = [
            sys.executable, "-m", "sglang.launch_server",
            "--model-path", MODEL_DIR,
            "--host", settings.SGLANG_HOST,
            "--port", str(settings.SGLANG_PORT),
            "--dtype", "bfloat16",
            "--enable-radix-cache",
            "--mem-fraction-static", "0.88",
            "--chunked-prefill-size", "4096",
            "--enable-torch-compile",
            "--schedule-policy", "lpm",
            "--served-model-name", settings.MODEL_NAME,
            "--trust-remote-code",
        ]
        
        print(f"[modal_server] Launching SGLang: {' '.join(cmd)}")
        self._proc = subprocess.Popen(
            cmd, stdout=sys.stdout, stderr=sys.stderr
        )
        self._wait_for_server_ready()

    def _download_weights_if_needed(self):
        from huggingface_hub import snapshot_download
        marker = f"{MODEL_DIR}/.download_complete"
        if os.path.exists(marker):
            return
            
        print(f"[modal_server] Downloading {settings.MODEL_NAME} → {MODEL_DIR} …")
        snapshot_download(
            repo_id=settings.MODEL_NAME,
            local_dir=MODEL_DIR,
            ignore_patterns=["*.msgpack", "*.h5", "flax_model*"],
        )
        with open(marker, "w") as f:
            f.write("ok")
        MODEL_VOLUME.commit()

    def _wait_for_server_ready(self, timeout: int = 300):
        import urllib.request
        import urllib.error
        health_url = f"http://localhost:{settings.SGLANG_PORT}/health"
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(health_url, timeout=5) as r:
                    if r.status == 200:
                        return
            except Exception:
                pass
            time.sleep(3)
        raise RuntimeError("SGLang failed to start")

    @modal.exit()
    def shutdown(self):
        if hasattr(self, "_proc") and self._proc.poll() is None:
            self._proc.terminate()
            self._proc.wait(timeout=15)

    @modal.web_server(port=settings.SGLANG_PORT, startup_timeout=360)
    def serve(self):
        pass
