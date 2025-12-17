import logging
import time

def run_test(device, memory_tool):
    """
    Placeholder test for New App - Sample 2.
    This test just logs a message and waits for a short time.
    """
    logging.info("Running Sample 2 test for New App...")
    
    # Example of interaction:
    # 1. Do some swipes
    # device(scrollable=True).fling.vert.backward()
    
    for i in range(5):
        logging.info(f"New App Sample 2: Step {i+1}")
        time.sleep(3)
        
    logging.info("New App Sample 2 finished.")
    memory_tool.stop_monitoring()
