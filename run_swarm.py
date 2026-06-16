import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.box import ROUNDED
from rich.live import Live

from app.context.context_manager import ContextManager
from app.inference.client import InferenceClient
from app.orchestration.orchestrator import SwarmOrchestrator

console = Console()

async def main():
    console.clear()
    console.print(Panel(
        Text("QwenSwarm: RepoPilot CLI", style="bold cyan", justify="center"),
        subtitle="Zero-Copy Multi-Agent Software Engineering System",
        box=ROUNDED,
        border_style="cyan"
    ))
    
    # Check configurations
    from app.config import settings
    console.print(f"[bold cyan]Configuration Loaded:[/bold cyan]")
    console.print(f"  • Backend Type: [bold green]{settings.BACKEND_TYPE}[/bold green]")
    console.print(f"  • Model Name: [bold green]{settings.MODEL_NAME}[/bold green]")
    console.print(f"  • Endpoint URL: [bold green]{settings.MODAL_ENDPOINT_URL}[/bold green]\n")
    
    if settings.BACKEND_TYPE == "sglang" and settings.MODAL_ENDPOINT_URL == "http://localhost:30000":
        console.print("[yellow]Note: MODAL_ENDPOINT_URL is pointing to localhost:30000. If you are deploying to Modal, make sure to update this endpoint in your .env file.[/yellow]\n")

    # Step 1: Parse repository context
    with console.status("[bold yellow]Building Repository Context Graph...[/bold yellow]") as status:
        try:
            cm = ContextManager(".")
            cm.build()
            payload = cm.retrieve_context()
            console.print("[bold green]✔[/bold green] Repository Context Graph built successfully!")
            console.print(f"  • Total files indexed: [bold]{len(cm.graph.files)}[/bold]")
            console.print(f"  • Total symbols extracted: [bold]{len(cm.graph.symbols)}[/bold]")
        except Exception as e:
            console.print(f"[bold red]❌ Failed to build repository context:[/bold red] {e}")
            sys.exit(1)
            
    # Step 2: Choose inference backend
    console.print("\n[bold cyan]Step 2: Select Inference Backend[/bold cyan]")
    console.print("  [1] Qwen Cloud Services (DashScope) [Recommended]")
    console.print("  [2] Modal + SGLang")
    console.print("  [3] Local / Custom vLLM")
    
    default_opt = "1"
    if settings.BACKEND_TYPE == "sglang":
        default_opt = "2"
    elif settings.BACKEND_TYPE == "vllm":
        default_opt = "3"
        
    choice = input(f"Choose backend (1-3, default {default_opt}): ").strip()
    if not choice:
        choice = default_opt
        
    if choice == "1":
        settings.BACKEND_TYPE = "dashscope"
    elif choice == "2":
        settings.BACKEND_TYPE = "sglang"
    elif choice == "3":
        settings.BACKEND_TYPE = "vllm"
    else:
        console.print(f"[yellow]Invalid choice, using configuration default: {settings.BACKEND_TYPE}[/yellow]")

    console.print(f"Selected Backend: [bold green]{settings.BACKEND_TYPE}[/bold green]\n")

    # Step 3: Get user request
    console.print("[bold cyan]Step 3: What engineering task should the Swarm of Agents execute?[/bold cyan]")
    user_request = input("> ").strip()
    if not user_request:
        console.print("[bold red]Task cannot be empty.[/bold red]")
        sys.exit(1)
        
    console.print()
    
    # Initialize client and orchestrator
    client = InferenceClient()
    orchestrator = SwarmOrchestrator(context_payload=payload, inference_client=client)
    
    # Subscribe to events to show progress beautifully
    thought_content = ""
    live_instance = None
    
    def make_event_logger(event_name, style, emoji):
        async def handler(data=None):
            nonlocal thought_content
            thought_content = ""
            if live_instance:
                live_instance.update(Panel(Text("Thinking...", style="dim"), title="💭 Agent Thought Process", border_style="cyan", box=ROUNDED))
                
            if data is None:
                console.print(f"[{style}]{emoji} {event_name}[/{style}]")
            else:
                if event_name == "WORKFLOW_STARTED":
                    console.print(Panel(f"[bold]Request:[/bold] {data}", title=f"🚀 {event_name}", border_style=style, box=ROUNDED))
                elif event_name == "PLAN_CREATED":
                    table = Table(title="Generated Swarm Execution Plan", box=ROUNDED, border_style="yellow")
                    table.add_column("Task ID", style="cyan", width=10)
                    table.add_column("Title", style="bold white")
                    table.add_column("Priority", style="magenta")
                    table.add_column("Target Files", style="green")
                    
                    for task in data.tasks:
                        table.add_row(
                            task.id,
                            task.title,
                            task.priority.value if hasattr(task.priority, "value") else str(task.priority),
                            ", ".join(task.target_files)
                        )
                    console.print(table)
                elif event_name == "TASK_STARTED":
                    console.print(f"[{style}]{emoji} {event_name}: Assigning tasks to executors...[/{style}]")
                    for executor, task in data:
                        console.print(f"  • Assigned [bold cyan]{task.id}[/bold cyan] -> [italic]ExecutorAgent[/italic] ([bold]{task.title}[/bold])")
                elif event_name == "TASK_COMPLETED":
                    console.print(f"[{style}]{emoji} {event_name}: Tasks finished. Results:[/{style}]")
                    for result in data:
                        console.print(f"  • Task [bold cyan]{result.task_id}[/bold cyan]: {result.summary}")
                        if result.files_modified:
                            console.print(f"    Modified files: [green]{', '.join(result.files_modified)}[/green]")
                elif event_name == "EXECUTION_STARTED":
                    console.print(f"[{style}]{emoji} {event_name}: Workspace path: [italic]{data}[/italic]")
                elif event_name == "TESTS_COMPLETED":
                    console.print(f"[{style}]{emoji} {event_name}:")
                    console.print(f"  • Tests run: {data.tests_run} (Passed: [green]{data.tests_passed}[/green], Failed: [red]{data.tests_failed}[/red])")
                    console.print(f"  • Mypy validation: {'[green]PASSED[/green]' if data.mypy_passed else '[red]FAILED[/red]'}")
                    console.print(f"  • Ruff linting: {'[green]PASSED[/green]' if data.ruff_passed else '[red]FAILED[/red]'}")
                elif event_name == "REPAIR_STARTED":
                    console.print(f"[{style}]{emoji} {event_name}: Repair agent triggered by [bold red]{data.tool} {data.error_type}[/bold red]")
                elif event_name == "REPAIR_COMPLETED":
                    console.print(f"[{style}]{emoji} {event_name}: Fix generated (Confidence: [bold]{data.confidence:.2%}[/bold])")
                    console.print(Panel(data.proposed_fix, title="Proposed Patch", border_style="yellow", box=ROUNDED))
                elif event_name == "REVIEW_COMPLETED":
                    status_str = "[green]APPROVED[/green]" if data.approved else "[red]REJECTED[/red]"
                    console.print(Panel(
                        f"Status: {status_str}\n\n[bold]Reason:[/bold]\n{data.reason}\n\n[bold]Issues:[/bold]\n" + 
                        ("\n".join(f"- {i}" for i in data.issues) if data.issues else "None") + 
                        "\n\n[bold]Recommendations:[/bold]\n" + 
                        ("\n".join(f"- {r}" for r in data.recommendations) if data.recommendations else "None"),
                        title=f"📋 {event_name}",
                        border_style="green" if data.approved else "red",
                        box=ROUNDED
                    ))
                else:
                    console.print(f"[{style}]{emoji} {event_name}: {data}[/{style}]")
        return handler

    orchestrator.event_bus.subscribe("WORKFLOW_STARTED", make_event_logger("WORKFLOW_STARTED", "cyan", "🚀"))
    orchestrator.event_bus.subscribe("PLAN_CREATED", make_event_logger("PLAN_CREATED", "yellow", "📋"))
    orchestrator.event_bus.subscribe("TASK_STARTED", make_event_logger("TASK_STARTED", "blue", "⚙"))
    orchestrator.event_bus.subscribe("TASK_COMPLETED", make_event_logger("TASK_COMPLETED", "green", "✔"))
    orchestrator.event_bus.subscribe("EXECUTION_STARTED", make_event_logger("EXECUTION_STARTED", "magenta", "📦"))
    orchestrator.event_bus.subscribe("TESTS_STARTED", make_event_logger("TESTS_STARTED", "yellow", "🔍"))
    orchestrator.event_bus.subscribe("TESTS_COMPLETED", make_event_logger("TESTS_COMPLETED", "green", "📊"))
    orchestrator.event_bus.subscribe("REPAIR_STARTED", make_event_logger("REPAIR_STARTED", "red", "🩹"))
    orchestrator.event_bus.subscribe("REPAIR_COMPLETED", make_event_logger("REPAIR_COMPLETED", "yellow", "🔧"))
    orchestrator.event_bus.subscribe("REVIEW_STARTED", make_event_logger("REVIEW_STARTED", "cyan", "👀"))
    orchestrator.event_bus.subscribe("REVIEW_COMPLETED", make_event_logger("REVIEW_COMPLETED", "green", "📝"))
    
    async def thought_handler(data: str):
        nonlocal thought_content
        thought_content += data
        if live_instance:
            live_instance.update(Panel(Text(thought_content, style="cyan"), title="💭 Agent Thought Process", border_style="cyan", box=ROUNDED))
            
    orchestrator.event_bus.subscribe("MODEL_THINKING", thought_handler)
    
    console.print("[bold yellow]Executing multi-agent swarm workflow...[/bold yellow]")
    try:
        initial_panel = Panel(Text("Waiting for agents...", style="dim"), title="💭 Agent Thought Process", border_style="cyan", box=ROUNDED)
        with Live(initial_panel, console=console, refresh_per_second=15) as live:
            live_instance = live
            result = await orchestrator.receive_request(user_request)
            live_instance = None
            
        console.print("\n[bold green]✔ Workflow completed successfully![/bold green]")
    except Exception as e:
        console.print(f"\n[bold red]❌ Swarm execution failed:[/bold red] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Aborted by user.[/bold yellow]")
        sys.exit(0)
