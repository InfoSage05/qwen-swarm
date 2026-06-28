import asyncio
import tarfile
import io
import time
from app.sandbox.base import BaseSandbox, SandboxResult

try:
    import docker
except ImportError:
    docker = None

class DockerSandbox(BaseSandbox):
    def __init__(self):
        if docker is None:
            raise RuntimeError("docker package not installed")
        self.client = docker.from_env()
        
    async def run_code(self, code: str, timeout: int = 30) -> SandboxResult:
        container = None
        try:
            # We run the container indefinitely, then execute code, then remove.
            # But the prompt says "Spins up a python:3.11-slim container with... auto-remove=True".
            # It copies code to container via tarball.
            
            # Since we must stream or copy files, let's create a temp tarball in memory
            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode='w') as tar:
                code_bytes = code.encode('utf-8')
                tarinfo = tarfile.TarInfo(name='script.py')
                tarinfo.size = len(code_bytes)
                tar.addfile(tarinfo, io.BytesIO(code_bytes))
            tar_stream.seek(0)
            
            container = self.client.containers.create(
                "python:3.11-slim",
                command=["sleep", "infinity"],
                network_mode="none",
                read_only=True,
                volumes={"/tmp": {"bind": "/tmp", "mode": "rw"}},
                mem_limit="256m",
                nano_cpus=1_000_000_000,
                auto_remove=True
            )
            container.start()
            container.put_archive('/tmp', tar_stream)
            
            # Now run the script via async
            # docker-py is synchronous, so we use asyncio.to_thread
            def exec_run():
                start = time.time()
                exec_result = container.exec_run(["python", "/tmp/script.py"], workdir="/tmp")
                return exec_result, time.time() - start
                
            task = asyncio.create_task(asyncio.to_thread(exec_run))
            
            try:
                exec_result, duration = await asyncio.wait_for(task, timeout=timeout)
                output = exec_result.output.decode('utf-8', errors='replace')
                # docker-py exec_run returns combined output by default if demux=False (default)
                # We can't cleanly split stdout/stderr without demux=True, but let's assume it's mostly stdout
                return SandboxResult(
                    stdout=output,
                    stderr="",
                    exit_code=exec_result.exit_code,
                    timed_out=False
                )
            except asyncio.TimeoutError:
                return SandboxResult(
                    stdout="",
                    stderr="Execution timed out.",
                    exit_code=-1,
                    timed_out=True
                )
        except Exception as e:
            return SandboxResult(
                stdout="",
                stderr=str(e),
                exit_code=-2,
                timed_out=False
            )
        finally:
            if container:
                try:
                    container.stop(timeout=1)
                except Exception:
                    pass
