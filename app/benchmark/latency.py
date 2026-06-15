import time

class LatencyTracker:
    def __init__(self):
        self.start_time = 0
        self.ttft_time = 0
        self.end_time = 0
        
    def start(self):
        self.start_time = time.time()
        
    def record_first_token(self):
        self.ttft_time = time.time()
        
    def end(self):
        self.end_time = time.time()
        
    def get_ttft_ms(self) -> int:
        if self.ttft_time == 0: return 0
        return int((self.ttft_time - self.start_time) * 1000)
        
    def get_total_ms(self) -> int:
        if self.end_time == 0: return 0
        return int((self.end_time - self.start_time) * 1000)
