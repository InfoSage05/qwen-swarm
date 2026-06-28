import re
from rich.panel import Panel
from rich.text import Text
from rich.layout import Layout
from rich.table import Table
from rich.console import Group
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.box import ROUNDED

def build_main_layout() -> Layout:
    layout = Layout()
    layout.split_row(
        Layout(name="main", ratio=2),
        Layout(name="sidebar", ratio=1)
    )
    layout["sidebar"].update(Panel("No tasks yet.", title="📋 Task List", border_style="cyan"))
    return layout

def update_layout(layout: Layout, state, log_lines: list, thought_content: str):
    # Build Task Table
    table = Table(box=ROUNDED, border_style="cyan", show_header=True)
    table.add_column("Task ID", style="cyan")
    table.add_column("Status", style="bold")
    
    for t in state.completed_tasks:
        if isinstance(t, dict):
            table.add_row(t.get("id", "-"), "[green]Completed[/green]")
        else:
            table.add_row(t.id, "[green]Completed[/green]")
    for t in state.active_tasks:
        if isinstance(t, dict):
            table.add_row(t.get("id", "-"), "[yellow]In Progress[/yellow]")
        else:
            table.add_row(t.id, "[yellow]In Progress[/yellow]")
        
    layout["sidebar"].update(Panel(table, title="📋 Task List", border_style="cyan"))
    
    main_content = []
    if log_lines:
        for line in log_lines[-8:]:
            if isinstance(line, str):
                main_content.append(Text(line))
            else:
                main_content.append(line)
        
    parts = re.split(r'(```diff\n.*?(?:```|$))', thought_content, flags=re.DOTALL | re.IGNORECASE)
    
    formatted_items = []
    for part in parts:
        if part.lower().startswith("```diff"):
            diff_text = part[7:]
            if diff_text.endswith("```"):
                diff_text = diff_text[:-3]
            formatted_items.append(Syntax(diff_text, "diff", theme="monokai", word_wrap=True))
        else:
            think_match = re.search(r'<(?:think|thought)>(.*?)(?:</(?:think|thought)>|$)', part, re.DOTALL | re.IGNORECASE)
            text = think_match.group(1).strip() if think_match else part.strip()
            if text:
                formatted_items.append(Markdown(text))
                
    if formatted_items:
        main_content.append(Panel(Group(*formatted_items), title="💭 Agent Output...", border_style="cyan", box=ROUNDED))
    
    layout["main"].update(Panel(Group(*main_content), title="🚀 Swarm Execution", border_style="blue", box=ROUNDED))

def make_user_panel(text: str) -> Panel:
    return Panel(text, title="👤 [bold green]You[/bold green]", border_style="green", box=ROUNDED)

def make_agent_panel(text: str) -> Panel:
    return Panel(Markdown(text), title="🤖 [bold cyan]Swarm Agent[/bold cyan]", border_style="cyan", box=ROUNDED)

def show_startup_banner(console):
    console.clear()
    console.print(Panel(
        Text("QwenSwarm: RepoPilot CLI", style="bold cyan", justify="center"),
        subtitle="Zero-Copy Multi-Agent Software Engineering System",
        box=ROUNDED,
        border_style="cyan"
    ))

def show_config_info(console, settings):
    console.print("[bold cyan]Configuration Loaded:[/bold cyan]")
    console.print(f"  • Backend Type: [bold green]{settings.BACKEND_TYPE}[/bold green]")
    console.print(f"  • Model Name: [bold green]{settings.MODEL_NAME}[/bold green]")
    console.print(f"  • Endpoint URL: [bold green]{settings.MODAL_ENDPOINT_URL}[/bold green]\n")
    
    if settings.BACKEND_TYPE == "sglang" and settings.MODAL_ENDPOINT_URL == "http://localhost:30000":
        console.print("[yellow]Note: MODAL_ENDPOINT_URL is pointing to localhost:30000. If you are deploying to Modal, make sure to update this endpoint in your .env file.[/yellow]\n")
