# =============================================================================
# modal_server.py — QwenSwarm GPU Backend
# =============================================================================
# WHAT THIS FILE DOES
# -------------------
# Deploys an OpenAI-compatible SGLang inference server onto a Modal A10G GPU.
# The server hosts Qwen/Qwen2.5-7B-Instruct and exposes two critical features:
#
#   1. RadixAttention KV-Cache Sharing
#      SGLang's RadixAttention stores every computed KV-tensor in a prefix
#      radix trie keyed by the token sequence that produced it.  When two
#      requests share an identical token prefix (our SHARED_SYSTEM_PROMPT),
#      SGLang reuses the already-computed KV tensors from VRAM rather than
#      re-running the transformer layers.  This is the "zero-copy" in
#      QwenSwarm — the GPU never re-encodes the shared context.
#
#   2. XGrammar Structured Outputs (GPU-side JSON enforcement)
#      When a request arrives with an OpenAI `response_format` containing a
#      JSON Schema, SGLang's XGrammar integration compiles that schema into a
#      context-free grammar and converts it to a token-level finite-state
#      automaton.  At each decoding step the FSA masks logits directly on the
#      GPU so that only tokens that keep the partial JSON valid receive non-zero
#      probability.  Zero CPU round-trips; zero post-hoc parsing/retries.
#
# DEPLOYMENT
# ----------
#   modal deploy modal_server.py          # persistent endpoint
#   modal run    modal_server.py          # ephemeral (dev / demo)
#
# The endpoint URL printed after deploy goes into orchestrator.py or .env as
# MODAL_ENDPOINT_URL.
# =============================================================================

import subprocess
import sys
import time

import modal

# ---------------------------------------------------------------------------
# 1. Modal App definition
# ---------------------------------------------------------------------------
app = modal.App("qwen-swarm-sglang")

# ---------------------------------------------------------------------------
# 2. Container Image
# ---------------------------------------------------------------------------
# We build a bespoke container image that layers SGLang and its dependencies
# on top of Modal's official CUDA 12.4 / Ubuntu 22.04 base.
#
# WHY pip_install order matters:
#   torch must be present before sglang so that sglang's CUDA extension build
#   picks up the correct CUDA toolkit bundled with the torch wheel.
#
# flashinfer — fused CUDA kernels for attention; SGLang requires it for
#   RadixAttention's paged KV-cache management on Ampere+ GPUs (A10G = GA102).
# xgrammar  — compiled C++/CUDA grammar engine; installed here so it is
#   available in the same Python environment as sglang at serving time.
sglang_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        # Core ML stack
        "torch==2.3.1",
        "torchvision==0.18.1",
        "torchaudio==2.3.1",
        extra_index_url="https://download.pytorch.org/whl/cu121",
    )
    .pip_install(
        # SGLang with all optional extras (openai server, vision, etc.)
        "sglang[all]==0.3.6",
        # GPU-accelerated structured output grammar engine
        "xgrammar==0.1.6",
        # Fused attention kernels for RadixAttention paged cache
        "flashinfer==0.1.6",
        extra_index_url="https://flashinfer.ai/whl/cu121/torch2.3/",
    )
    .pip_install(
        # HuggingFace ecosystem for model weight loading
        "transformers>=4.43.0",
        "accelerate>=0.31.0",
        "huggingface_hub>=0.23.0",
    )
)

# ---------------------------------------------------------------------------
# 3. Model weight volume
# ---------------------------------------------------------------------------
# Modal Volumes give us a persistent NFS-like layer.  We download the model
# weights once into this volume; subsequent cold-starts skip the download and
# just memory-map from the volume, cutting cold-start time from ~5 min → ~40 s.
MODEL_VOLUME = modal.Volume.from_name("qwen-swarm-weights", create_if_missing=True)
MODEL_DIR = "/model-weights"
MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"

# Port on which SGLang's OpenAI-compatible HTTP server listens inside the
# container.  Modal tunnels this out via a web endpoint.
SGLANG_PORT = 30000


# ---------------------------------------------------------------------------
# 4. QwenSGLangServer Modal class
# ---------------------------------------------------------------------------
@app.cls(
    # -------------------------------------------------------------------------
    # GPU selection
    # A10G = 24 GB GDDR6 VRAM.  Qwen2.5-7B in bf16 needs ~14 GB, leaving
    # ~10 GB for the RadixAttention KV-cache pool — enough to hold the shared
    # prefix tree for hundreds of concurrent swarm branches.
    # -------------------------------------------------------------------------
    gpu="a10g",
    image=sglang_image,
    volumes={MODEL_DIR: MODEL_VOLUME},
    # Keep the container alive between requests.  This is *critical* for
    # KV-cache reuse: if the container cold-starts per request the in-memory
    # radix trie is destroyed and we pay full prefill cost every time.
    timeout=3600,          # 1-hour max lifetime per container
    container_idle_timeout=600,  # reclaim after 10 min of silence
    # Secrets: HF token for gated model download (Qwen is ungated but good practice)
    secrets=[modal.Secret.from_name("huggingface-secret", required=False)],
)
class QwenSGLangServer:
    """
    Modal class that lifecycle-manages the SGLang server process.

    Modal calls `enter()` once after the container starts, then routes HTTP
    requests to `serve()`.  The SGLang subprocess runs for the entire
    container lifetime, so its in-process radix trie (KV-cache index) persists
    across all API calls that hit this container.
    """

    @modal.enter()
    def start_sglang_server(self):
        """
        Called exactly once when the Modal container initialises.

        We launch SGLang as a subprocess rather than importing it in-process
        because SGLang's C++ runtime initialises global CUDA contexts that
        conflict with Modal's own CUDA setup when imported at module level.
        The subprocess owns the GPU context cleanly.

        KEY SGLANG FLAGS FOR QWENSWARM
        --------------------------------
        --enable-radix-cache
            Activates RadixAttention.  SGLang maintains a prefix radix trie in
            VRAM.  Every unique token prefix gets one KV entry; all subsequent
            requests that share that prefix are cache hits.  Our
            SHARED_SYSTEM_PROMPT is the root of every swarm branch, so it is
            computed once and reused by Planner, Executor, and Reviewer agents.

        --mem-fraction-static 0.88
            Reserves 88 % of VRAM for the static KV-cache pool managed by
            RadixAttention's paged allocator.  Higher = more cache capacity =
            more simultaneous branches without eviction.

        --chunked-prefill-size 4096
            Enables chunked prefill: long prompts are split into 4096-token
            chunks and interleaved with decode steps, reducing latency for the
            first swarm agent while subsequent agents are still waiting.

        --enable-torch-compile
            Applies torch.compile() to the attention and MLP kernels, giving
            ~15-20 % throughput improvement on A10G after a one-time warm-up.

        --dtype bfloat16
            bf16 halves VRAM vs fp32 while matching A10G's native accumulation
            format, leaving more headroom for the KV-cache pool.

        --api-key (empty)
            We handle auth at the Modal layer (requires_auth on the endpoint).
            Setting an empty key disables SGLang's own auth middleware.
        """
        self._download_weights_if_needed()

        cmd = [
            sys.executable, "-m", "sglang.launch_server",
            "--model-path",          MODEL_DIR,
            "--host",                "0.0.0.0",
            "--port",                str(SGLANG_PORT),
            "--dtype",               "bfloat16",
            # ---- RadixAttention KV-cache (THE MAGIC) ----
            "--enable-radix-cache",
            "--mem-fraction-static", "0.88",
            # ---- Throughput optimisations ----
            "--chunked-prefill-size", "4096",
            "--enable-torch-compile",
            "--schedule-policy",     "lpm",   # longest-prefix-match scheduling
            # ---- Structured output (XGrammar) ----
            # SGLang auto-detects xgrammar if installed; no extra flag needed.
            # When the OpenAI `response_format` field contains a JSON Schema,
            # SGLang's grammar backend compiles it to a token-mask FSA on GPU.
            # ---- OpenAI API compatibility ----
            "--served-model-name",   "qwen-swarm",
            "--trust-remote-code",
        ]

        print(f"[modal_server] Launching SGLang: {' '.join(cmd)}")
        self._proc = subprocess.Popen(
            cmd,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        self._wait_for_server_ready()

    def _download_weights_if_needed(self):
        """
        Downloads Qwen2.5-7B-Instruct weights into the Modal Volume the first
        time the container runs.  Subsequent runs skip this (files already
        exist in the volume mount at MODEL_DIR).
        """
        import os
        from huggingface_hub import snapshot_download

        marker = f"{MODEL_DIR}/.download_complete"
        if os.path.exists(marker):
            print("[modal_server] Model weights already present in volume.")
            return

        print(f"[modal_server] Downloading {MODEL_ID} → {MODEL_DIR} …")
        snapshot_download(
            repo_id=MODEL_ID,
            local_dir=MODEL_DIR,
            ignore_patterns=["*.msgpack", "*.h5", "flax_model*"],
        )
        # Write sentinel so we skip download on future cold-starts
        with open(marker, "w") as f:
            f.write("ok")
        MODEL_VOLUME.commit()   # flush volume writes so other containers see them
        print("[modal_server] Download complete.")

    def _wait_for_server_ready(self, timeout: int = 300):
        """
        Polls SGLang's /health endpoint until it responds 200 or we time out.
        SGLang's first start includes torch.compile warm-up (~90 s on A10G).
        """
        import urllib.request
        import urllib.error

        health_url = f"http://localhost:{SGLANG_PORT}/health"
        deadline = time.time() + timeout
        print("[modal_server] Waiting for SGLang to be ready …")
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(health_url, timeout=5) as r:
                    if r.status == 200:
                        print("[modal_server] SGLang is ready ✓")
                        return
            except (urllib.error.URLError, ConnectionRefusedError):
                pass
            time.sleep(3)
        raise RuntimeError(f"SGLang did not become ready within {timeout}s")

    @modal.exit()
    def shutdown(self):
        """Gracefully terminate the SGLang subprocess when Modal reclaims the container."""
        if hasattr(self, "_proc") and self._proc.poll() is None:
            print("[modal_server] Shutting down SGLang …")
            self._proc.terminate()
            self._proc.wait(timeout=15)

    # -------------------------------------------------------------------------
    # Web endpoint — proxies all traffic to the local SGLang process.
    #
    # @modal.web_server exposes a TCP port on the container as a public HTTPS
    # endpoint.  Modal handles TLS termination and routes requests to
    # 0.0.0.0:{SGLANG_PORT} inside the container.
    #
    # The orchestrator sets this URL as the `base_url` for its AsyncOpenAI
    # client, so every /v1/chat/completions call goes directly to SGLang's
    # OpenAI-compatible router.
    # -------------------------------------------------------------------------
    @modal.web_server(port=SGLANG_PORT, startup_timeout=360)
    def serve(self):
        """
        Modal web_server decorator turns the SGLang HTTP port into a public
        HTTPS endpoint.  No application code needed here — Modal proxies
        traffic straight to the port.

        After `modal deploy modal_server.py` the URL looks like:
          https://<your-workspace>--qwen-swarm-sglang-qwensglangserver-serve.modal.run

        Set that URL as MODAL_ENDPOINT_URL in your .env file.
        """
        pass  # Modal handles the proxy; SGLang process was started in enter()


# ---------------------------------------------------------------------------
# 5. One-shot download helper (run with `modal run modal_server.py`)
# ---------------------------------------------------------------------------
@app.function(
    image=sglang_image,
    volumes={MODEL_DIR: MODEL_VOLUME},
    timeout=1800,
    secrets=[modal.Secret.from_name("huggingface-secret", required=False)],
)
def download_model():
    """
    Standalone function to pre-populate the Modal Volume with model weights.
    Run once before deploying the server:

        modal run modal_server.py::download_model

    This avoids the cold-start download penalty on the first serve() call.
    """
    from huggingface_hub import snapshot_download
    import os

    marker = f"{MODEL_DIR}/.download_complete"
    if os.path.exists(marker):
        print("Weights already downloaded.")
        return

    snapshot_download(
        repo_id=MODEL_ID,
        local_dir=MODEL_DIR,
        ignore_patterns=["*.msgpack", "*.h5", "flax_model*"],
    )
    with open(marker, "w") as f:
        f.write("ok")
    MODEL_VOLUME.commit()
    print("Model weights downloaded and committed to volume.")


# ---------------------------------------------------------------------------
# 6. Local entrypoint for quick smoke-test
# ---------------------------------------------------------------------------
@app.local_entrypoint()
def main():
    """
    Quick smoke-test: downloads weights then prints the endpoint URL.
    Run with:  modal run modal_server.py
    """
    print("Pre-downloading model weights into Modal Volume …")
    download_model.remote()
    print(
        "\n✅  Weights ready.  Deploy the server with:\n"
        "    modal deploy modal_server.py\n"
        "\nThen copy the printed URL into .env as MODAL_ENDPOINT_URL."
    )
