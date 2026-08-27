import time
import logging
from . import demonstrate

"""
NECESSARY MAPS - Germany
"""

PACKAGE = "com.sygic.profi.volvo"
START_ACTIVITY = "com.sygic.profi.platform.splashscreen.feature.ui.main.SplashScreenActivity"
FOREGROUND_APP = "com.google.android.calendar"

# ~10h at 20s per iteration (10s backgrounded + 10s foregrounded).
ITERATIONS_FULL = 1800
ITERATIONS_DRY_RUN = 6
SLEEP_SECONDS = 10


def run_test(device, memory_tool):
    """
    Start a demonstrated route, then repeatedly push the app to the background
    (switch to Calendar) and back to the foreground while memory is sampled.
    """
    demonstrate.start_demonstration(device)
    time.sleep(3)

    iterations = ITERATIONS_DRY_RUN if memory_tool.dry_run else ITERATIONS_FULL
    for i in range(iterations):
        logging.info(f"Mambo number {i+1}")
        time.sleep(SLEEP_SECONDS)
        memory_tool.adb.shell("monkey", "-p", FOREGROUND_APP, "1")
        logging.info("switched to calendar")
        time.sleep(SLEEP_SECONDS)
        memory_tool.adb.shell("am", "start", "-n", f"{PACKAGE}/{START_ACTIVITY}")
        logging.info("switched to profi navi")

    demonstrate.cancel_route(device)
    memory_tool.stop_monitoring()
