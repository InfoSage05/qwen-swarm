class TokenUsageTracker:
    def __init__(self):
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.cached_tokens = 0
        
    def add_usage(self, prompt: int, completion: int, cached: int = 0):
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.cached_tokens += cached
        
    def get_total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens
