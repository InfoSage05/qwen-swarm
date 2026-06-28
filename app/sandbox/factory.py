from app.sandbox.base import BaseSandbox

def get_sandbox() -> BaseSandbox:
    try:
        import docker
        client = docker.from_env()
        client.ping()
        from app.sandbox.docker_sandbox import DockerSandbox
        return DockerSandbox()
    except Exception:
        from app.sandbox.subprocess_sandbox import SubprocessSandbox
        return SubprocessSandbox()
