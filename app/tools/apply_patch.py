import logging
import tempfile
import os
import re
from app.sandbox.executor import SandboxExecutor

logger = logging.getLogger(__name__)

def apply_patch_pure_python(patch_content: str, target_dir: str) -> bool:
    """Fallback pure-Python unified diff applicator when git apply fails."""
    logger.info("Running pure-Python patch applicator fallback...")
    
    # Split patch content into files
    # Standard diff outputs split by 'diff --git '
    files = re.split(r'^diff --git ', patch_content, flags=re.MULTILINE)
    applied_any = False
    
    for f_patch in files:
        if not f_patch.strip():
            continue
            
        # Extract filename and check if new file
        lines = f_patch.splitlines()
        target_file = None
        is_new_file = False
        
        for line in lines:
            if line.startswith("+++ b/"):
                target_file = line[6:].strip()
            elif line.startswith("+++ "):
                target_file = line[4:].strip()
            if "new file mode" in line:
                is_new_file = True
                
        if not target_file:
            continue
            
        full_path = os.path.join(target_dir, target_file)
        
        # New file creation
        if is_new_file or not os.path.exists(full_path):
            file_lines = []
            in_hunk = False
            for line in lines:
                if line.startswith("@@"):
                    in_hunk = True
                    continue
                if in_hunk:
                    if line.startswith("+"):
                        file_lines.append(line[1:])
                    elif line.startswith(" "):
                        file_lines.append(line[1:])
            
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write("\n".join(file_lines) + "\n")
            logger.info(f"Successfully created new file via fallback: {target_file}")
            applied_any = True
        else:
            # Modify existing file
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    original_content = f.read().splitlines()
            except Exception as e:
                logger.error(f"Failed to read file for patching: {full_path}. Error: {e}")
                continue
                
            hunks = []
            current_hunk = None
            in_hunks_section = False
            
            for line in lines:
                if line.startswith("@@"):
                    in_hunks_section = True
                    if current_hunk:
                        hunks.append(current_hunk)
                    
                    # Parse hunk headers like @@ -old_start,old_count +new_start,new_count @@
                    match = re.match(r'@@ -(\d+),?(\d+)? \+(\d+),?(\d+)? @@', line)
                    if match:
                        old_start = int(match.group(1))
                        current_hunk = {"old_start": old_start, "lines": []}
                    else:
                        current_hunk = {"old_start": 1, "lines": []}
                elif in_hunks_section:
                    if line.startswith("+") or line.startswith("-") or line.startswith(" ") or line.startswith("\\"):
                        current_hunk["lines"].append(line)
            if current_hunk:
                hunks.append(current_hunk)
                
            new_content = list(original_content)
            offset = 0
            file_modified = False
            
            for hunk in hunks:
                old_lines = []
                for hl in hunk["lines"]:
                    if hl.startswith("-") or hl.startswith(" "):
                        old_lines.append(hl[1:])
                
                # Locate old_lines block in new_content
                start_idx = max(0, hunk["old_start"] - 1 + offset)
                matched = False
                
                if start_idx + len(old_lines) <= len(new_content):
                    match_ok = True
                    for i, ol in enumerate(old_lines):
                        if new_content[start_idx + i] != ol:
                            match_ok = False
                            break
                    if match_ok:
                        matched = True
                        
                if not matched:
                    # Search context range
                    for search_offset in range(-20, 20):
                        idx = start_idx + search_offset
                        if 0 <= idx and idx + len(old_lines) <= len(new_content):
                            match_ok = True
                            for i, ol in enumerate(old_lines):
                                if new_content[idx + i] != ol:
                                    match_ok = False
                                    break
                            if match_ok:
                                start_idx = idx
                                matched = True
                                break
                                
                if matched:
                    replacement = []
                    for hl in hunk["lines"]:
                        if hl.startswith("+") or hl.startswith(" "):
                            replacement.append(hl[1:])
                    
                    new_content[start_idx : start_idx + len(old_lines)] = replacement
                    offset += len(replacement) - len(old_lines)
                    file_modified = True
                else:
                    logger.warning(f"Could not locate matching context for hunk in {target_file}")
                    
            if file_modified:
                try:
                    with open(full_path, "w", encoding="utf-8") as f:
                        f.write("\n".join(new_content) + "\n")
                    logger.info(f"Successfully modified file via fallback: {target_file}")
                    applied_any = True
                except Exception as e:
                    logger.error(f"Failed to write patched file: {full_path}. Error: {e}")
                    
    return applied_any

async def apply_patch(patch_content: str, target_dir: str, executor: SandboxExecutor) -> bool:
    """Safely apply generated code changes via patch, falling back to python applicator if git fails."""
    # Ensure trailing newline is present to prevent git apply corrupt patch errors
    if not patch_content.endswith("\n"):
        patch_content += "\n"
        
    with tempfile.NamedTemporaryFile(mode='w', suffix='.patch', delete=False) as f:
        f.write(patch_content)
        temp_path = f.name
        
    try:
        res = await executor.run_command("git", ["apply", "--recount", "--whitespace=fix", temp_path], cwd=target_dir)
        if res.return_code == 0:
            return True
            
        logger.warning(f"git apply failed (exit code {res.return_code}). Trying Python fallback...")
        return apply_patch_pure_python(patch_content, target_dir)
    except Exception as e:
        logger.error(f"Exception during git apply: {e}. Trying Python fallback...")
        return apply_patch_pure_python(patch_content, target_dir)
    finally:
        os.unlink(temp_path)
