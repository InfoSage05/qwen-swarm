import getpass
from pathlib import Path
from rich.console import Console
from app.auth.keystore import save_key

console = Console()

def setup_command():
    """Interactive wizard to configure RepoPilot backends and keys."""
    console.print("[bold cyan]RepoPilot Setup Wizard[/bold cyan]")
    console.print("Let's configure your default AI backend.\n")
    
    backends = {
        "1": ("dashscope", "Qwen Cloud (DashScope)"),
        "2": ("sglang", "Modal + SGLang"),
        "3": ("vllm", "Local/Custom vLLM"),
        "4": ("glm", "Zhipu AI (GLM)"),
        "5": ("ollama", "Ollama (Local, No API Key needed)")
    }
    
    for k, v in backends.items():
        console.print(f"  [{k}] {v[1]}")
        
    choice = input("\nSelect a backend (1-5): ").strip()
    if choice not in backends:
        console.print("[bold red]Invalid choice.[/bold red]")
        return
        
    backend_id = backends[choice][0]
    
    if backend_id == "dashscope":
        key = getpass.getpass("Enter your DashScope API Key: ").strip()
        if key:
            save_key("DASHSCOPE_API_KEY", key)
            console.print("[green]Saved DashScope API Key securely.[/green]")
    elif backend_id == "glm":
        key = getpass.getpass("Enter your GLM API Key: ").strip()
        if key:
            save_key("GLM_API_KEY", key)
            console.print("[green]Saved GLM API Key securely.[/green]")
    elif backend_id == "vllm":
        key = getpass.getpass("Enter your OpenAI-compatible API Key: ").strip()
        if key:
            save_key("OPENAI_API_KEY", key)
            console.print("[green]Saved OPENAI API Key securely.[/green]")
            
    # Write preference to config
    config_dir = Path.home() / ".config" / "repopilot"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "config.toml"
    
    # Simple TOML writing
    config_content = f'BACKEND_TYPE = "{backend_id}"\n'
    if backend_id == "ollama":
        config_content += 'MODEL_NAME = "qwen2.5-coder:7b"\n'
        
    with open(config_file, "w") as f:
        f.write(config_content)
        
    console.print(f"\n[bold green]Setup Complete![/bold green] Your default backend is now [bold]{backend_id}[/bold].")
    console.print("You can run [bold cyan]repopilot[/bold cyan] to start the shell.")
