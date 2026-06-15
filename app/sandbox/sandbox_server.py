from app.sandbox.runtime import SandboxRuntime
from app.sandbox.models import SandboxRequest, SandboxResponse

class SandboxServer:
    """Local Async Server managing sandbox execution."""
    
    def __init__(self):
        self.runtime = SandboxRuntime()
        
    async def handle_request(self, req: SandboxRequest) -> SandboxResponse:
        """In a real distributed system, this would be an API endpoint."""
        return await self.runtime.execute(req)
