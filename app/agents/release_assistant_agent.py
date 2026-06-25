from app.agents.base_agent import BaseAgent
from app.schemas.release_assistant import ReleaseReport
from typing import Callable, Awaitable, Optional

class ReleaseAssistantAgent(BaseAgent):
    """Reviews PR context against a release checklist and prepares release readiness reports."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.system_prompt = (
            "You are an AI PR Review & Release Readiness Assistant. "
            "Your job is to review the given PR context (diffs, commits) and evaluate it against standard release checklists. "
            "Identify missing docs, untested edge cases, migration risks, and broken flows. "
            "Produce a structured ReleaseReport with flagged risks, test plans, and release notes."
        )

    async def analyze_pr(self, context_payload: str, pr_context: str, stream_callback: Optional[Callable[[str], Awaitable[None]]] = None) -> ReleaseReport:
        prompt = (
            f"Review the following Pull Request context and provide a Release Readiness Report.\n\n"
            f"PR Context:\n{pr_context}\n\n"
            "Ensure you cover:\n"
            "1. Checklist status (e.g., tests, docs, migrations)\n"
            "2. Flagged risks\n"
            "3. Test plans\n"
            "4. Release notes"
        )
        return await self.run(context_payload, prompt, ReleaseReport, stream_callback)
