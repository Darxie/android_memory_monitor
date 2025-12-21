import logging
import time

def run_test(device, memory_tool):
    """
    Placeholder test for New App - Sample 1.
    This test just logs a message and waits for a short time.
    """
    logging.info("Running Sample 1 test for New App...")
    
    # Example of interaction:
    # 1. Launch something in the app
    # device.app_start("com.new.app.release", use_monkey=True)
    # 2. Tap a button
    # device(text="...").click()
    
    for i in range(10):
        logging.info(f"New App Sample 1: Step {i+1}")
        time.sleep(2)
        
    logging.info("New App Sample 1 finished.")
    memory_tool.stop_monitoring()
