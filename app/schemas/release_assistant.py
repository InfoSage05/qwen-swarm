from pydantic import BaseModel, Field
from typing import List, Optional

class ReleaseReport(BaseModel):
    is_ready: bool = Field(..., description="Whether the PR is ready for release based on the checklist.")
    checklist_status: List[str] = Field(..., description="Status of various release checklist items (e.g. docs, tests).")
    flagged_risks: List[str] = Field(..., description="Any potential risks or broken flows identified in the PR.")
    test_plans: List[str] = Field(..., description="Proposed test plans to verify the changes.")
    release_notes: str = Field(..., description="Generated release notes summarizing the changes for end users.")
    summary: str = Field(..., description="A short summary of the review.")
