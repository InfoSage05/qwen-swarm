import modal

sglang_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch==2.3.1",
        "torchvision==0.18.1",
        "torchaudio==2.3.1",
        extra_index_url="https://download.pytorch.org/whl/cu121",
    )
    .pip_install(
        "sglang[all]==0.3.6",
        "xgrammar==0.1.6",
        "flashinfer==0.1.6",
        extra_index_url="https://flashinfer.ai/whl/cu121/torch2.3/",
    )
    .pip_install(
        "transformers>=4.43.0",
        "accelerate>=0.31.0",
        "huggingface_hub>=0.23.0",
    )
)
