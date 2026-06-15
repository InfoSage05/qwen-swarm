from app.sandbox.models import SandboxRequest, SandboxResponse
from app.sandbox.sandbox_server import SandboxServer

class SandboxClient:
    """Client abstraction to communicate with the SandboxServer.
    Currently uses an in-memory server instance for the hackathon constraints,
    but keeps the architectural boundary intact.
    """
    
    def __init__(self):
        self._server = SandboxServer()
        
    async def execute(self, command: str, args: list[str], cwd: str = ".", timeout: int = 30) -> SandboxResponse:
        req = SandboxRequest(command=command, args=args, cwd=cwd, timeout=timeout)
        return await self._server.handle_request(req)
