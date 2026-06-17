from pydantic import BaseModel, Field

class PromptBuilderResult(BaseModel):
    """Output from the Prompt Builder agent."""
    enhanced_prompt: str = Field(
        ...,
        description="A detailed, robust, well-structured prompt expanded from the raw user request, to be passed to the Planner Agent."
    )
