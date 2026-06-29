import asyncio
import os
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.columns import Columns
from rich.markdown import Markdown
from rich.box import ROUNDED

from app.tools.web_search import perform_web_search
from app.cli.tui import build_main_layout, make_user_panel

async def run_terminal_command_live(command: str, console) -> int:
    cmd = command.strip()
    if cmd.startswith("cd ") or cmd == "cd":
        parts = cmd.split(" ", 1)
        if len(parts) > 1:
            try:
                os.chdir(parts[1].strip())
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
            process = await asyncio.create_subprocess_shell(
                cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
            )
            while True:
                line = await process.stdout.readline()
                if not line: break
                try:
                    decoded_line = line.decode('utf-8')
                except UnicodeDecodeError:
                    decoded_line = line.decode('cp1252', errors='ignore')
                output_text += decoded_line
                live.update(Panel(Text(output_text), title=f"💻 Terminal: {cmd}", border_style="blue", box=ROUNDED))
                live.refresh()
            await process.wait()
            if not output_text:
                if process.returncode == 0:
                    output_text = "Command executed successfully (No output)."
                    live.update(Panel(Text(output_text), title=f"💻 Terminal: {cmd}", border_style="green", box=ROUNDED))
                else:
                    output_text = f"Command failed with exit code {process.returncode}."
                    live.update(Panel(Text(output_text), title=f"💻 Terminal: {cmd}", border_style="red", box=ROUNDED))
                live.refresh()
            return process.returncode
        except Exception as e:
            output_text += f"\nExecution failed: {str(e)}"
            live.update(Panel(Text(output_text), title=f"💻 Terminal: {cmd}", border_style="red", box=ROUNDED))
            live.refresh()
            return -1

async def handle_search(shell, input_text: str, prefix: str):
    query = input_text[len(prefix):].strip()
    if query:
        shell.console.print(f"[bold magenta]Searching web for:[/bold magenta] {query}")
        search_results = await perform_web_search(query)
        shell.console.print(search_results)
        shell.cm.add_external_context(f"Web Search: {query}", search_results)
        shell.console.print("[bold green]✔ Stored search results in context memory![/bold green]")
        shell.payload = shell.cm.retrieve_context()
        if shell.orchestrator:
            shell.orchestrator.context_payload = shell.payload
        if shell.chat_history:
            shell.chat_history[0]["content"] = f"You are a helpful assistant discussing the recent Agentic Swarm Workflow.\nContext Payload:\n{shell.payload}"

async def handle_cmd(shell, input_text: str, prefix: str):
    cmd = input_text[len(prefix):].strip()
    if prefix == "!":
        cmd = input_text[1:].strip()
    await run_terminal_command_live(cmd, shell.console)

async def handle_pr(shell, input_text: str, prefix: str):
    pr_context = input_text[len(prefix):].strip()
    shell.console.print(f"[bold magenta]Running Release Assistant for: {pr_context}[/bold magenta]")
    report = await shell.orchestrator.run_release_assistant(pr_context)
    if report:
        shell.console.print("[bold green]Release Report Generated![/bold green]")
        shell.console.print(report.model_dump_json(indent=2))

async def _run_agentic_workflow(shell, task_request: str, mode: str, image_url: str = None):
    thought_content = ""
    live_instance = None
    log_lines = []
    
    layout = build_main_layout()
    
    def refresh_ui():
        if not live_instance: return
        from app.cli.tui import update_layout
        update_layout(layout, shell.orchestrator.state, log_lines, thought_content)
        live_instance.update(layout)

    def make_event_logger(event_name, style, emoji):
        async def handler(data=None):
            nonlocal thought_content
            thought_content = ""
            if event_name == "TOOL_CALLED":
                args_str = "\n".join([f"{k}: {v}" for k, v in data.get("args", {}).items()])
                panel = Panel(args_str, title=f"🛠️ [bold yellow]Tool Call: {data.get('name')}[/bold yellow]", border_style="yellow", box=ROUNDED)
                log_lines.append(panel)
            elif event_name == "TOOL_COMPLETED":
                log_lines.append(f"[{style}]{emoji} Tool {data.get('name')} Finished[/{style}]")
            elif event_name in ["REPAIR_STARTED", "REVIEW_STARTED"]:
                msg = str(getattr(data, 'message', data))
                panel = Panel(msg, title=f"{emoji} [bold {style}]{event_name}[/bold {style}]", border_style=style, box=ROUNDED)
                log_lines.append(panel)
            else:
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

    shell.orchestrator.event_bus.subscribe("WORKFLOW_STARTED", make_event_logger("WORKFLOW_STARTED", "cyan", "🚀"))
    shell.orchestrator.event_bus.subscribe("PROMPT_BUILDER_STARTED", make_event_logger("PROMPT_BUILDER_STARTED", "blue", "✍️"))
    shell.orchestrator.event_bus.subscribe("PROMPT_BUILDER_COMPLETED", make_event_logger("PROMPT_BUILDER_COMPLETED", "green", "✨"))
    shell.orchestrator.event_bus.subscribe("PLAN_CREATED", make_event_logger("PLAN_CREATED", "yellow", "📋"))
    shell.orchestrator.event_bus.subscribe("TASK_STARTED", make_event_logger("TASK_STARTED", "blue", "⚙"))
    shell.orchestrator.event_bus.subscribe("TASK_COMPLETED", make_event_logger("TASK_COMPLETED", "green", "✔"))
    shell.orchestrator.event_bus.subscribe("EXECUTION_STARTED", make_event_logger("EXECUTION_STARTED", "magenta", "📦"))
    shell.orchestrator.event_bus.subscribe("TESTS_COMPLETED", make_event_logger("TESTS_COMPLETED", "green", "📊"))
    shell.orchestrator.event_bus.subscribe("REPAIR_STARTED", make_event_logger("REPAIR_STARTED", "red", "🔧"))
    shell.orchestrator.event_bus.subscribe("REPAIR_COMPLETED", make_event_logger("REPAIR_COMPLETED", "yellow", "🔧"))
    shell.orchestrator.event_bus.subscribe("REVIEW_STARTED", make_event_logger("REVIEW_STARTED", "blue", "📝"))
    shell.orchestrator.event_bus.subscribe("REVIEW_COMPLETED", make_event_logger("REVIEW_COMPLETED", "green", "📝"))
    shell.orchestrator.event_bus.subscribe("TOOL_CALLED", make_event_logger("TOOL_CALLED", "yellow", "🛠️"))
    shell.orchestrator.event_bus.subscribe("TOOL_COMPLETED", make_event_logger("TOOL_COMPLETED", "green", "✅"))
    
    async def thought_handler(data: str):
        nonlocal thought_content
        thought_content += data
        refresh_ui()
            
    shell.orchestrator.event_bus.subscribe("MODEL_THINKING", thought_handler)
    
    shell.console.print(f"\n[bold yellow]Executing multi-agent swarm workflow... ({mode} mode)[/bold yellow]")
    try:
        with Live(layout, console=shell.console, refresh_per_second=15) as live:
            live_instance = live
            shell.orchestrator._current_live = live
            
            if mode == "execute":
                result = await shell.orchestrator.execute_plan()
            else:
                while True:
                    await shell.orchestrator.generate_plan(task_request, image_url)
                    if getattr(shell.orchestrator.state.workflow, "needs_clarification", False):
                        live.stop()
                        shell.console.print("\n[bold yellow]🤔 The Swarm needs clarification:[/bold yellow]")
                        shell.console.print(shell.orchestrator.state.workflow.clarification_question)
                        clarification = input("\nRefine task (or press Enter to ignore and force execution): ").strip()
                        if clarification:
                            task_request += f"\n\nUser Clarification: {clarification}"
                            live.start()
                            continue
                    break
                    
                if mode == "plan":
                    result = None
                else:
                    live.stop()
                    shell.console.print("\n[bold yellow]📋 Plan Generated:[/bold yellow]")
                    for task in shell.orchestrator.state.plan.tasks:
                        shell.console.print(f"  - [bold]{task['id']}[/bold]: {task['title']}")
                    
                    choice = input("\nDo you approve this plan to proceed with execution? (Y/n): ").strip().lower()
                    if choice != 'n':
                        live.start()
                        result = await shell.orchestrator.execute_plan()
                    else:
                        shell.console.print("[yellow]Execution aborted by user.[/yellow]")
                        result = None
                        
            live_instance = None
            shell.orchestrator._current_live = None
            
        shell.console.print("\n[bold green]✔ Workflow step completed successfully![/bold green]")
        shell.session_store.save(shell.session_id, os.path.abspath("."), shell.chat_history, shell.orchestrator.state, "context_hash")
        return result
    except Exception as e:
        shell.console.print(f"\n[bold red]❌ Swarm execution failed:[/bold red] {e}")
        import traceback
        traceback.print_exc()
        return None

async def handle_agent(shell, input_text: str, prefix: str):
    cmd_body = input_text[len(prefix):].strip()
    image_url = None
    if " --image " in cmd_body:
        cmd_body, image_url = cmd_body.split(" --image ", 1)
        image_url = image_url.strip()
    
    new_result = await _run_agentic_workflow(shell, cmd_body, mode="full", image_url=image_url)
    if new_result:
        shell.chat_history.append({"role": "system", "content": f"Task '{cmd_body}' completed. Review: {new_result.approved}"})

async def handle_plan(shell, input_text: str, prefix: str):
    cmd_body = input_text[len(prefix):].strip()
    image_url = None
    if " --image " in cmd_body:
        cmd_body, image_url = cmd_body.split(" --image ", 1)
        image_url = image_url.strip()
        
    await _run_agentic_workflow(shell, cmd_body, mode="plan", image_url=image_url)
    shell.chat_history.append({"role": "system", "content": f"Plan generated for: '{cmd_body}'."})

async def handle_execute(shell, input_text: str, prefix: str):
    new_result = await _run_agentic_workflow(shell, "", mode="execute")
    if new_result:
        shell.chat_history.append({"role": "system", "content": f"Execution completed. Review: {new_result.approved}"})

async def handle_chat(shell, input_text: str):
    shell.chat_history.append({"role": "user", "content": input_text})
    shell.session_store.save(shell.session_id, os.path.abspath("."), shell.chat_history, shell.orchestrator.state, "context_hash")
    
    user_panel = make_user_panel(input_text)
    shell.console.print(Columns([user_panel], align="right"))
    
    response_content = ""
    agent_panel = Panel("...", title="🤖 [bold cyan]Swarm Agent[/bold cyan]", border_style="cyan", box=ROUNDED)
    
    with Live(agent_panel, console=shell.console, auto_refresh=False) as live_chat:
        try:
            async for chunk in shell.client.chat_stream(shell.chat_history):
                response_content += chunk
                live_chat.update(Panel(Markdown(response_content), title="🤖 [bold cyan]Swarm Agent[/bold cyan]", border_style="cyan", box=ROUNDED))
                live_chat.refresh()
        except Exception as e:
            live_chat.update(Panel(f"[bold red]Error:[/bold red] {e}", title="🤖 [bold cyan]Swarm Agent[/bold cyan]", border_style="red", box=ROUNDED))
            live_chat.refresh()
            
    shell.chat_history.append({"role": "assistant", "content": response_content})
    shell.session_store.save(shell.session_id, os.path.abspath("."), shell.chat_history, shell.orchestrator.state, "context_hash")
