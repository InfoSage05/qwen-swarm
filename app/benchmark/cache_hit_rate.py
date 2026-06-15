class CacheTracker:
    def __init__(self):
        self.cache_hits = 0
        self.cache_misses = 0
        self.prefix_reuse_percentage = 0.0
        
    def record_hit(self):
        self.cache_hits += 1
        
    def record_miss(self):
        self.cache_misses += 1
        
    def set_prefix_reuse(self, percentage: float):
        self.prefix_reuse_percentage = percentage
