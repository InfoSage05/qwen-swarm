import asyncio
import os
import re
import sys
from rich.console import Console
from rich.columns import Columns

from app.config import settings
from app.context.context_manager import ContextManager
from app.inference.client import InferenceClient
from app.orchestration.orchestrator import SwarmOrchestrator
from app.orchestration.session_manager import SessionManager
from app.cli.tui import build_main_layout, make_user_panel, make_agent_panel, show_startup_banner, show_config_info
from app.cli.handlers import (
    handle_search, handle_cmd, handle_pr, handle_agent, 
    handle_plan, handle_execute, handle_chat
)

console = Console()

class SwarmShell:
    def __init__(self):
        self.console = console
        self.cm = ContextManager(".")
        self.client = InferenceClient()
        self.orchestrator = None
        self.chat_history = []
        self.payload = ""
        
        self.commands = {
            "/search": handle_search,
            "/pr": handle_pr,
            "/agent": handle_agent,
            "/swarm": handle_agent,
            "/plan": handle_plan,
            "/execute": handle_execute,
            "!": handle_cmd,
            "/cmd": handle_cmd,
            "/run": handle_cmd
        }
        
    async def initialize(self):
        show_startup_banner(self.console)
        show_config_info(self.console, settings)
        
        session_data = SessionManager.load_session()
        if session_data:
            self.console.print("[bold yellow]Found an existing session![/bold yellow]")
            if input("Resume previous session? (Y/n): ").strip().lower() != 'n':
                self.chat_history = session_data.chat_history
                self.payload = session_data.context_payload
                
                self.orchestrator = SwarmOrchestrator(context_payload=self.payload, inference_client=self.client)
                self.orchestrator.state = session_data.swarm_state
                
                self.console.print("[bold green]✔ Session Resumed Successfully[/bold green]\n")
            else:
                SessionManager.clear_session()
                session_data = None
                
        if not session_data:
            with self.console.status("[bold yellow]Building Repository Context Graph...[/bold yellow]") as status:
                try:
                    self.cm.build()
                    self.payload = self.cm.retrieve_context()
                    self.console.print("[bold green]✔[/bold green] Repository Context Graph built successfully!")
                    self.console.print(f"  • Total files indexed: [bold]{len(self.cm.graph.files)}[/bold]")
                    self.console.print(f"  • Total symbols extracted: [bold]{len(self.cm.graph.symbols)}[/bold]")
                except Exception as e:
                    self.console.print(f"[bold red]❌ Failed to build repository context:[/bold red] {e}")
                    sys.exit(1)
                    
            self.orchestrator = SwarmOrchestrator(context_payload=self.payload, inference_client=self.client)
            self.chat_history = [
                {"role": "system", "content": f"You are a helpful assistant discussing the recent Agentic Swarm Workflow.\nContext Payload:\n{self.payload}"}
            ]
            
        # Hook up permission prompt
        async def prompt_permission(cmd: str) -> bool:
            live_instance_pause = getattr(self.orchestrator, '_current_live', None)
            if live_instance_pause:
                live_instance_pause.stop()
            self.console.print(f"\n[bold yellow]⚠️ Permission Request[/bold yellow]")
            self.console.print(f"The Swarm wants to execute: [bold white]{cmd}[/bold white]")
            choice = input("Allow? (Y/n): ").strip().lower()
            if live_instance_pause:
                live_instance_pause.start()
            return choice != 'n'
            
        self.orchestrator.sandbox.ask_permission = prompt_permission

    async def dispatch(self, input_text: str):
        urls = re.findall(r'(https?://[^\s]+)', input_text)
        if urls:
            from app.tools.scrape_url import scrape_url
            for url in urls:
                self.console.print(f"[cyan]Scraping URL: {url}[/cyan]")
                scraped_text = await scrape_url(url)
                self.cm.add_external_context(url, scraped_text)
                self.console.print(f"[bold green]✔ Stored URL content in context memory![/bold green]")
            self.payload = self.cm.retrieve_context()
            self.orchestrator.context_payload = self.payload
            self.chat_history[0]["content"] = f"You are a helpful assistant discussing the recent Agentic Swarm Workflow.\nContext Payload:\n{self.payload}"
        
        for prefix, handler in self.commands.items():
            if input_text.startswith(prefix):
                await handler(self, input_text, prefix)
                return
                
        # Bash aliases
        BASH_COMMANDS = ("ls", "cat", "git", "python", "mkdir", "rm", "cp", "mv", "grep", "echo", "pwd", "cd")
        if any(input_text.startswith(cmd + " ") or input_text == cmd for cmd in BASH_COMMANDS):
            await handle_cmd(self, "!" + input_text, "!")
            return
            
        await handle_chat(self, input_text)
        
    async def run(self):
        await self.initialize()
        
        self.console.print("\n[bold cyan]Interactive Swarm Shell[/bold cyan]")
        self.console.print("  [bold]!cmd[/bold]          - Run a terminal command")
        self.console.print("  [bold]/agent msg[/bold]    - Full autonomous swarm run")
        self.console.print("  [bold]/plan msg[/bold]     - Generate an execution plan only")
        self.console.print("  [bold]/execute[/bold]      - Execute the currently generated plan")
        self.console.print("  [bold]/search q[/bold]      - Perform web search")
        self.console.print("  [bold]/pr url[/bold]       - Run AI PR Review Assistant")
        self.console.print("  [bold]/quit[/bold]         - Exit")
        
        while True:
            try:
                chat_input = self.console.input("\n[bold cyan][Swarm] >[/bold cyan] ").strip()
                if chat_input.lower() in ['exit', '/quit', 'quit']:
                    break
                if not chat_input:
                    continue
                await self.dispatch(chat_input)
            except (KeyboardInterrupt, EOFError):
                break
