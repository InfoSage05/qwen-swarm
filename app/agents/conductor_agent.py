from typing import Callable, Awaitable
import logging

from app.inference.client import InferenceClient
from app.schemas.conductor import ConductorWorkflow

logger = logging.getLogger(__name__)

CONDUCTOR_SYSTEM_PROMPT = """
Your role as an assistant involves obtaining answers to questions by an iterative process of querying powerful language models, each with a different skillset.

You are given a user-provided question, a repository context, and a list of available numbered language models. Your objective is to output a sequence of up to 5 workflow steps.

Each routing is made of three elements: A language model, its assigned subtask to accomplish, and an "access list" of past workflow steps it will see in its context when trying to accomplish the subtask.

A subtask could directly ask the language model to solve the given question from scratch, refine the solution of the previous subtask in the sequence, or perform any other completely different task that would facilitate later language models in the sequence to answer the original question with their expertise.

Based on your answer, the first model selected will be prompted with the user question and the first subtask you define. Each following model in the sequence will be prompted with the history of the previous subtask and response messages specified in its access list, and will be asked to accomplish its relative subtask. The answer of the final model and subtask will be provided back as the final solution to the user.

Your response should be provided according to the structured schema output, containing these key fields:
- needs_clarification: Set this to true ONLY IF the user's request is too ambiguous or underspecified to formulate a solid plan.
- clarification_question: If needs_clarification is true, provide the exact question you want to ask the user to clarify their intent.
- model_id: the integers corresponding to the numbered language models in the sequence you want to prompt.
- subtasks: strings that will be used to prompt the corresponding language model.
- access_list: lists of past routing messages to include in the context. E.g., ['all'] for everything, or [] for none.

AVAILABLE LANGUAGE MODELS:
Model 0: Qwen 2.5 (Planner/Executor)
Model 1: Qwen 2.5 (Planner/Executor)
Model 2: Qwen 2.5 (Planner/Executor)
Model 3: Qwen 2.5 (Planner/Executor)
Model 4: Qwen 2.5 (Reviewer/Validator)
Model 5: Qwen 2 VL (Vision/Multimodal) - Use this model if the subtask requires analyzing an image, UI screenshot, or diagram.

For instance:

EXAMPLE 1 (Complex coding task needing planning, execution, and review):
model_id = [0, 1, 4]
subtasks = [
  "Analyze the problem, understand the constraints, and propose a step-by-step strategy to solve the problem.",
  "Follow the plan and assigned subtask provided by the first model to implement the Python code.",
  "Based on the assigned subtask provided by the previous model, identify any runtime errors or issues with the algorithm and return the final correct Python code."
]
access_list = [[], ["all"], ["all"]]

EXAMPLE 2 (Simple query):
model_id = [0]
subtasks = ["Answer the question directly and provide the solution."]
access_list = [[]]
"""

class ConductorAgent:
    """The Conductor Agent that dynamically creates agentic workflows."""
    
    def __init__(self, inference_client: InferenceClient):
        self.client = inference_client

    async def create_workflow(
        self, 
        context_payload: str, 
        user_request: str, 
        on_chunk: Callable[[str], Awaitable[None]] = None
    ) -> ConductorWorkflow:
        
        user_content = f"USER QUESTION:\n{user_request}\n\nREPOSITORY CONTEXT:\n{context_payload}"
        
        messages = [
            {"role": "system", "content": CONDUCTOR_SYSTEM_PROMPT.strip()},
            {"role": "user", "content": user_content}
        ]
        
        response = await self.client.chat(
            messages=messages,
            response_format=ConductorWorkflow,
            temperature=0.3,
            on_chunk=on_chunk
        )
        
        try:
            return ConductorWorkflow.model_validate(response)
        except Exception as e:
            logger.error(f"Failed to parse Conductor Workflow: {e}")
            # Fallback to a basic single-step workflow
            return ConductorWorkflow(
                model_id=[0],
                subtasks=["Execute the user's request based on the repository context."],
                access_list=[[]]
            )
