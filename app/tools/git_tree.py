import os
import subprocess
from pathlib import Path
from rich.tree import Tree

def get_git_status() -> dict:
    """Returns a dict mapping file paths to their short git status (e.g. M, A, D, ??)"""
    try:
        output = subprocess.check_output(
            ['git', 'status', '--short'], 
            stderr=subprocess.DEVNULL
        ).decode('utf-8')
        
        status_map = {}
        for line in output.splitlines():
            if len(line) < 3:
                continue
            status = line[:2].strip()
            filepath = line[3:].strip()
            status_map[filepath] = status
        return status_map
    except Exception:
        return {}

def build_visual_git_tree(workspace: str = ".") -> Tree:
    """Constructs a Rich.Tree showcasing git-modified files and folders."""
    status_map = get_git_status()
    root_path = Path(workspace).resolve()
    
    # Root node of the tree
    tree = Tree(f"📁 [bold blue]{root_path.name}[/]")
    
    # Store sub-trees to build recursively
    nodes = {root_path: tree}

    # Walk the directory
    for path in sorted(root_path.rglob('*'), key=lambda p: (not p.is_dir(), p.name)):
        # Ignore common caches and git internals
        if any(part.startswith('.') or part in ['__pycache__', 'node_modules', 'myenv'] for part in path.parts):
            continue
            
        parent_node = nodes.get(path.parent, tree)
        rel_path = str(path.relative_to(root_path)).replace("\\", "/")
        
        status = status_map.get(rel_path, "")
        
        # Determine color coding based on Git status
        style = "dim white"
        icon = "📄 "
        status_label = ""
        
        if path.is_dir():
            icon = "📁 "
            style = "bold blue"
            # If any file inside this folder is modified, highlight the folder
            if any(k.startswith(rel_path + "/") for k in status_map.keys()):
                style = "bold yellow"
        else:
            if "M" in status:
                style = "bold yellow"
                status_label = " [italic yellow](modified)[/]"
            elif "A" in status or "??" in status:
                style = "bold green"
                status_label = " [italic green](new)[/]"
            elif "D" in status:
                style = "bold red"
                status_label = " [italic red](deleted)[/]"
                
        # Add to the tree structure
        node_label = f"{icon}[{style}]{path.name}[/]{status_label}"
        node = parent_node.add(node_label)
        
        if path.is_dir():
            nodes[path] = node
            
    return tree
