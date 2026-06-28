import asyncio
import argparse
import sys
from app.cli.setup import setup_command

def main():
    parser = argparse.ArgumentParser(description="QwenSwarm RepoPilot CLI")
    parser.add_argument("command", nargs="?", default="shell", choices=["shell", "setup"], help="Command to run (shell or setup)")
    parser.add_argument("--version", action="version", version="0.1.0")
    
    args = parser.parse_args()
    
    if args.command == "setup":
        setup_command()
    else:
        # We need to defer importing the shell to avoid circular dependencies and slow startup
        from app.cli.shell import SwarmShell
        shell = SwarmShell()
        try:
            asyncio.run(shell.run())
        except KeyboardInterrupt:
            print("\nAborted by user.")
            sys.exit(0)

if __name__ == "__main__":
    main()
