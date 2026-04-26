import time
import logging
import threading

# for side-quest purposes

def run_test(device, memory_tool):
    """
    Starts a long-running thread that stops memory monitoring after a significant delay.
    The 'device' argument is included for signature consistency but is not used.
    """
    def thread_target():
        delay = 172800  # 48 hours
        logging.info(f"Freedrive mode started. Monitoring will stop in {delay / 3600} hours.")
        time.sleep(delay)
        logging.info("Freedrive time elapsed. Stopping memory monitoring.")
        memory_tool.stop_monitoring()

    # Run the monitoring stop logic in a separate thread so it doesn't block
    thread = threading.Thread(target=thread_target, daemon=True)
    thread.start()