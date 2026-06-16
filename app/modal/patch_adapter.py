import pathlib

target = """                prompt_ids = tokenizer_manager.tokenizer.apply_chat_template(
                    openai_compatible_messages,
                    tokenize=True,
                    add_generation_prompt=True,
                )"""

replacement = """                prompt_ids = tokenizer_manager.tokenizer.apply_chat_template(
                    openai_compatible_messages,
                    tokenize=True,
                    add_generation_prompt=True,
                )
                if hasattr(prompt_ids, "input_ids"):
                    prompt_ids = prompt_ids.input_ids
                elif isinstance(prompt_ids, dict) and "input_ids" in prompt_ids:
                    prompt_ids = prompt_ids["input_ids"]"""

target_normalized = target.replace("\r\n", "\n")

def run_patch(adapter_path: pathlib.Path):
    if not adapter_path.exists():
        raise FileNotFoundError(f"Could not find adapter.py at {adapter_path}")

    content = adapter_path.read_text("utf-8")
    content_normalized = content.replace("\r\n", "\n")

    if target_normalized not in content_normalized:
        raise RuntimeError(f"Target string not found in {adapter_path}")

    patched_content = content_normalized.replace(target_normalized, replacement)
    adapter_path.write_text(patched_content, "utf-8")
    print(f"Successfully patched SGLang adapter.py at {adapter_path}!")

if __name__ == "__main__":
    import sglang
    sglang_dir = pathlib.Path(sglang.__file__).parent
    run_patch(sglang_dir / "srt/openai_api/adapter.py")
