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

from rich.layout import Layout
from app.context.context_manager import ContextManager
from app.inference.client import InferenceClient
from app.orchestration.orchestrator import SwarmOrchestrator
from app.orchestration.session_manager import SessionManager, SessionData

console = Console()

async def run_terminal_command_live(command: str, console) -> int:
    """Runs a shell command asynchronously and streams the output in a blue panel."""
    if command.startswith('!'):
        cmd = command[1:].strip()
    elif command.startswith('/cmd '):
        cmd = command[5:].strip()
    elif command.startswith('/run '):
        cmd = command[5:].strip()
    else:
        cmd = command.strip()
        
    # Handle 'cd' commands directly in the parent Python process
    if cmd.startswith("cd ") or cmd == "cd":
        parts = cmd.split(" ", 1)
        if len(parts) > 1:
            target_dir = parts[1].strip()
            try:
                os.chdir(target_dir)
                console.print(f"[bold blue]Changed working directory to: {os.getcwd()}[/bold blue]")
                return 0
            except Exception as e:
                console.print(f"[bold red]Failed to change directory: {e}[/bold red]")
                return -1
        else:
            console.print(f"[bold blue]Current directory: {os.getcwd()}[/bold blue]")
            return 0

    output_text = ""
    panel = Panel("Starting...", title=f"💻 Terminal: {cmd}", border_style="blue", box=ROUNDED)
    
    with Live(panel, console=console, auto_refresh=False) as live:
        try:
            # Start process asynchronously
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            
            # Read stdout line by line
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                try:
                    decoded_line = line.decode('utf-8')
                except UnicodeDecodeError:
                    decoded_line = line.decode('cp1252', errors='ignore')
                    
                output_text += decoded_line
                live.update(Panel(Text(output_text), title=f"💻 Terminal: {cmd}", border_style="blue", box=ROUNDED))
                live.refresh()
                
            await process.wait()
            # If no output was produced
            if not output_text:
                output_text = f"Command finished with exit code {process.return_code}."
                live.update(Panel(Text(output_text), title=f"💻 Terminal: {cmd}", border_style="blue", box=ROUNDED))
                live.refresh()
            return process.return_code
        except Exception as e:
            output_text += f"\nExecution failed: {str(e)}"
            live.update(Panel(Text(output_text), title=f"💻 Terminal: {cmd}", border_style="red", box=ROUNDED))
            live.refresh()
            return -1

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

    # Check for saved session
    session_data = SessionManager.load_session()
    if session_data:
        console.print("[bold yellow]Found an existing session![/bold yellow]")
        if input("Resume previous session? (Y/n): ").strip().lower() != 'n':
            chat_history = session_data.chat_history
            payload = session_data.context_payload
            
            client = InferenceClient()
            orchestrator = SwarmOrchestrator(context_payload=payload, inference_client=client)
            orchestrator.state = session_data.swarm_state
            
            console.print("[bold green]✔ Session Resumed Successfully[/bold green]\n")
        else:
            SessionManager.clear_session()
            session_data = None

    if not session_data:
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

        client = InferenceClient()
        orchestrator = SwarmOrchestrator(context_payload=payload, inference_client=client)
        
        chat_history = [
            {"role": "system", "content": f"You are a helpful assistant discussing the recent Agentic Swarm Workflow.\nContext Payload:\n{payload}"}
        ]

    async def prompt_permission(cmd: str) -> bool:
        live_instance_pause = getattr(orchestrator, '_current_live', None)
        if live_instance_pause:
            live_instance_pause.stop()
        console.print(f"\n[bold yellow]⚠️ Permission Request[/bold yellow]")
        console.print(f"The Swarm wants to execute: [bold white]{cmd}[/bold white]")
        choice = input("Allow? (Y/n): ").strip().lower()
        if live_instance_pause:
            live_instance_pause.start()
        return choice != 'n'
        
    orchestrator.sandbox.ask_permission = prompt_permission

    async def run_agentic_workflow(task_request: str, mode: str = "full"):
        thought_content = ""
        live_instance = None
        log_lines = []
        
        layout = Layout()
        layout.split_row(
            Layout(name="main", ratio=2),
            Layout(name="sidebar", ratio=1)
        )
        layout["sidebar"].update(Panel("No tasks yet.", title="📋 Task List", border_style="cyan"))
        
        def refresh_ui():
            if not live_instance: return
            
            # Build Task Table
            table = Table(box=ROUNDED, border_style="cyan", show_header=True)
            table.add_column("Task ID", style="cyan")
            table.add_column("Status", style="bold")
            
            for t in orchestrator.state.completed_tasks:
                table.add_row(t.id, "[green]Completed[/green]")
            for t in orchestrator.state.active_tasks:
                table.add_row(t.id, "[yellow]In Progress[/yellow]")
                
            layout["sidebar"].update(Panel(table, title="📋 Task List", border_style="cyan"))
            
            from rich.console import Group
            from rich.markdown import Markdown
            
            main_content = []
            if log_lines:
                main_content.append(Text("\n".join(log_lines[-10:])))
                
            import re
            think_match = re.search(r'<(think|thought)>(.*?)(?:</\1>|$)', thought_content, re.DOTALL | re.IGNORECASE)
            if think_match:
                actual_thought = think_match.group(2).strip()
                if actual_thought:
                    main_content.append(Panel(Markdown(actual_thought), title="💭 Agent Thinking...", border_style="cyan", box=ROUNDED))
            
            layout["main"].update(Panel(Group(*main_content), title="🚀 Swarm Execution", border_style="blue", box=ROUNDED))
            live_instance.update(layout)

        def make_event_logger(event_name, style, emoji):
            async def handler(data=None):
                nonlocal thought_content
                thought_content = ""
                log_msg = f"[{style}]{emoji} {event_name}[/{style}]"
                if data:
                    if event_name == "WORKFLOW_STARTED":
                        log_msg += f": {data}"
                    elif event_name == "TASK_COMPLETED":
                        log_msg += f": Finished {len(data)} tasks."
                    elif event_name == "EXECUTION_STARTED":
                        log_msg += f": Workspace path {data}"
                    else:
                        log_msg += " ..."
                log_lines.append(log_msg)
                refresh_ui()
            return handler
    
        orchestrator.event_bus.subscribe("WORKFLOW_STARTED", make_event_logger("WORKFLOW_STARTED", "cyan", "🚀"))
        orchestrator.event_bus.subscribe("PROMPT_BUILDER_STARTED", make_event_logger("PROMPT_BUILDER_STARTED", "blue", "✍️"))
        orchestrator.event_bus.subscribe("PROMPT_BUILDER_COMPLETED", make_event_logger("PROMPT_BUILDER_COMPLETED", "green", "✨"))
        orchestrator.event_bus.subscribe("PLAN_CREATED", make_event_logger("PLAN_CREATED", "yellow", "📋"))
        orchestrator.event_bus.subscribe("TASK_STARTED", make_event_logger("TASK_STARTED", "blue", "⚙"))
        orchestrator.event_bus.subscribe("TASK_COMPLETED", make_event_logger("TASK_COMPLETED", "green", "✔"))
        orchestrator.event_bus.subscribe("EXECUTION_STARTED", make_event_logger("EXECUTION_STARTED", "magenta", "📦"))
        orchestrator.event_bus.subscribe("TESTS_COMPLETED", make_event_logger("TESTS_COMPLETED", "green", "📊"))
        orchestrator.event_bus.subscribe("REPAIR_COMPLETED", make_event_logger("REPAIR_COMPLETED", "yellow", "🔧"))
        orchestrator.event_bus.subscribe("REVIEW_COMPLETED", make_event_logger("REVIEW_COMPLETED", "green", "📝"))
        
        async def thought_handler(data: str):
            nonlocal thought_content
            thought_content += data
            refresh_ui()
                
        orchestrator.event_bus.subscribe("MODEL_THINKING", thought_handler)
        
        console.print(f"\n[bold yellow]Executing multi-agent swarm workflow... ({mode} mode)[/bold yellow]")
        try:
            with Live(layout, console=console, refresh_per_second=15) as live:
                live_instance = live
                orchestrator._current_live = live
                if mode == "plan":
                    await orchestrator.generate_plan(task_request)
                    result = None
                elif mode == "execute":
                    result = await orchestrator.execute_plan()
                else:
                    await orchestrator.generate_plan(task_request)
                    live.stop()
                    console.print("\n[bold yellow]📋 Plan Generated:[/bold yellow]")
                    for task in orchestrator.state.plan.tasks:
                        console.print(f"  - [bold]{task.id}[/bold]: {task.title}")
                    
                    choice = input("\nDo you approve this plan to proceed with execution? (Y/n): ").strip().lower()
                    if choice != 'n':
                        live.start()
                        result = await orchestrator.execute_plan()
                    else:
                        console.print("[yellow]Execution aborted by user.[/yellow]")
                        result = None
                live_instance = None
                orchestrator._current_live = None
                
            console.print("\n[bold green]✔ Workflow step completed successfully![/bold green]")
            # Auto-save session
            SessionManager.save_session(chat_history, payload, orchestrator.state)
            return result
        except Exception as e:
            console.print(f"\n[bold red]❌ Swarm execution failed:[/bold red] {e}")
            import traceback
            traceback.print_exc()
            return None

    import re
    from app.tools.scrape_url import scrape_url

    # Step 4: Interactive Chat Loop
    console.print("\n[bold cyan]Step 4: Interactive Swarm Shell[/bold cyan]")
    console.print("You can ask questions, or use the following commands:")
    console.print("  [bold]!cmd[/bold]          - Run a terminal command (or just type common bash cmds)")
    console.print("  [bold]/agent msg[/bold]    - Full autonomous swarm run")
    console.print("  [bold]/plan msg[/bold]     - Generate an execution plan only")
    console.print("  [bold]/execute[/bold]      - Execute the currently generated plan")
    console.print("  [bold]/pr url[/bold]       - Run AI PR Review & Release Assistant")
    console.print("  [bold]/quit[/bold]         - Exit")
    
    BASH_COMMANDS = ("ls", "cat", "git", "python", "mkdir", "rm", "cp", "mv", "grep", "echo", "pwd", "cd")
    
    while True:
        try:
            chat_input = console.input("\n[bold cyan][Swarm] >[/bold cyan] ").strip()
            if chat_input.lower() in ['exit', '/quit', 'quit']:
                break
            if not chat_input:
                continue
                
            # Scrape URLs if any are in the input
            urls = re.findall(r'(https?://[^\s]+)', chat_input)
            if urls:
                for url in urls:
                    console.print(f"[cyan]Scraping URL: {url}[/cyan]")
                    scraped_text = await scrape_url(url)
                    chat_input += f"\n\n[Scraped content from {url}]:\n{scraped_text}\n"
                    
            if chat_input.startswith("!") or chat_input.startswith("/run ") or chat_input.startswith("/cmd "):
                await run_terminal_command_live(chat_input, console)
                continue
                
            if chat_input.startswith("/pr "):
                pr_context = chat_input.split(" ", 1)[1] if " " in chat_input else ""
                console.print(f"[bold magenta]Running Release Assistant for: {pr_context}[/bold magenta]")
                report = await orchestrator.run_release_assistant(pr_context)
                if report:
                    console.print(f"[bold green]Release Report Generated![/bold green]")
                    console.print(report.model_dump_json(indent=2))
                continue
                
            if any(chat_input.startswith(cmd + " ") or chat_input == cmd for cmd in BASH_COMMANDS):
                await run_terminal_command_live("!" + chat_input, console)
                continue
                
            if chat_input.startswith("/agent ") or chat_input.startswith("/swarm "):
                new_task = chat_input.split(" ", 1)[1]
                new_result = await run_agentic_workflow(new_task, mode="full")
                if new_result:
                    chat_history.append({"role": "system", "content": f"Task '{new_task}' completed. Review: {new_result.approved}"})
                continue
                
            if chat_input.startswith("/plan "):
                new_task = chat_input.split(" ", 1)[1]
                await run_agentic_workflow(new_task, mode="plan")
                chat_history.append({"role": "system", "content": f"Plan generated for: '{new_task}'."})
                continue
                
            if chat_input.startswith("/execute"):
                new_result = await run_agentic_workflow("", mode="execute")
                if new_result:
                    chat_history.append({"role": "system", "content": f"Execution completed. Review: {new_result.approved}"})
                continue
                
            chat_history.append({"role": "user", "content": chat_input})
            SessionManager.save_session(chat_history, payload, orchestrator.state)
            
            from rich.columns import Columns
            user_panel = Panel(chat_input, title="👤 [bold green]You[/bold green]", border_style="green", box=ROUNDED)
            console.print(Columns([user_panel], align="right"))
            
            response_content = ""
            from rich.markdown import Markdown
            
            agent_panel = Panel("...", title="🤖 [bold cyan]Swarm Agent[/bold cyan]", border_style="cyan", box=ROUNDED)
            with Live(agent_panel, console=console, auto_refresh=False) as live_chat:
                try:
                    async for chunk in client.chat_stream(chat_history):
                        response_content += chunk
                        live_chat.update(
                            Panel(Markdown(response_content), title="🤖 [bold cyan]Swarm Agent[/bold cyan]", border_style="cyan", box=ROUNDED)
                        )
                        live_chat.refresh()
                except Exception as e:
                    live_chat.update(Panel(f"[bold red]Error:[/bold red] {e}", title="🤖 [bold cyan]Swarm Agent[/bold cyan]", border_style="red", box=ROUNDED))
                    live_chat.refresh()
                    
            chat_history.append({"role": "assistant", "content": response_content})
            SessionManager.save_session(chat_history, payload, orchestrator.state)
                
        except (KeyboardInterrupt, EOFError):
            break
                
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Aborted by user.[/bold yellow]")
        sys.exit(0)
