import time

class ThroughputTracker:
    def __init__(self):
        self.start_time = 0
        self.tasks_completed = 0
        
    def start(self):
        self.start_time = time.time()
        
    def record_task(self):
        self.tasks_completed += 1
        
    def get_metrics(self) -> dict:
        duration_minutes = (time.time() - self.start_time) / 60.0
        tpm = self.tasks_completed / duration_minutes if duration_minutes > 0 else 0
        return {
            "tasks_completed": self.tasks_completed,
            "tasks_per_minute": round(tpm, 2),
            "average_task_duration_ms": int(((time.time() - self.start_time) * 1000) / max(1, self.tasks_completed)) if self.tasks_completed > 0 else 0
        }
