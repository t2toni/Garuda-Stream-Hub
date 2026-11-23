import logging
from typing import Tuple

logger = logging.getLogger("AdaptiveBuffer")

class AdaptiveBufferController:
    """
    Monitors real-time network jitter and RTT.
    Provides dynamic buffer scaling recommendations and quality fallback detection.
    """
    def __init__(self, base_buffer_ms: int = 15, max_buffer_ms: int = 100):
        self.base_buffer_ms = base_buffer_ms
        self.max_buffer_ms = max_buffer_ms
        self.current_recommended_buffer = base_buffer_ms
        self.current_quality_tier: str = "HIGH" # HIGH, MEDIUM, LOW

    def evaluate(self, jitter_ms: float, rtt_ms: float) -> Tuple[int, str, bool]:
        """
        Returns:
            recommended_buffer_ms: int
            quality_tier: str ("HIGH" 16M, "MEDIUM" 10M, "LOW" 6M)
            fallback_recommended: bool
        """
        # Buffer calculation: minimum 15ms, expands if jitter is high
        buf = int(self.base_buffer_ms + (jitter_ms * 2.0))
        buf = max(self.base_buffer_ms, min(self.max_buffer_ms, buf))
        self.current_recommended_buffer = buf

        fallback_needed = False
        old_tier = self.current_quality_tier

        if rtt_ms > 90.0 or jitter_ms > 25.0:
            self.current_quality_tier = "LOW"
            fallback_needed = (old_tier != "LOW")
        elif rtt_ms > 45.0 or jitter_ms > 12.0:
            self.current_quality_tier = "MEDIUM"
            fallback_needed = (old_tier != "MEDIUM")
        else:
            self.current_quality_tier = "HIGH"

        return buf, self.current_quality_tier, fallback_needed
