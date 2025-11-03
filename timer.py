"""
Basic timer module to run functions at specified intervals.
Author: Ronen Ness.
Created: 2025.
"""
import threading
import time
from typing import Callable, Union


def register_timer(func: Callable[[], None], interval_minutes: Union[int, float]) -> threading.Thread:
    """
    Register a function to run every X minutes.
    
    Args:
        func (Callable[[], None]): Function to call (should take no arguments and return None)
        interval_minutes (Union[int, float]): How often to run (in minutes)
        
    Returns:
        threading.Thread: The daemon thread running the timer
    """
    def timer_loop() -> None:
        """Internal loop function that runs the timer."""
        while True:
            time.sleep(interval_minutes * 60)
            try:
                func()
            except Exception as e:
                print(f"Timer error: {e}")
    
    thread = threading.Thread(target=timer_loop, daemon=True)
    thread.start()
    return thread

