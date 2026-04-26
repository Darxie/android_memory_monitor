import time
import logging

ITERATIONS_FULL = 100
ITERATIONS_DRY_RUN = 20
SLEEP_FULL = 25
SLEEP_DRY_RUN = 5


def run_test(device, memory_tool):
    iterations = ITERATIONS_DRY_RUN if memory_tool.dry_run else ITERATIONS_FULL
    sleep_seconds = SLEEP_DRY_RUN if memory_tool.dry_run else SLEEP_FULL

    for i in range(iterations):
        logging.info(f"Mambo number {i+1}")
        time.sleep(sleep_seconds)
        memory_tool.adb.shell("monkey", "-p", "com.google.android.calendar", "1")
        logging.info("switched to calendar")
        time.sleep(sleep_seconds)
        memory_tool.adb.shell(
            "am", "start", "-n",
            "com.sygic.profi.beta/com.sygic.profi.platform.splashscreen.feature.ui.main.SplashScreenActivity",
        )
        logging.info("switched to profi navi")
    memory_tool.stop_monitoring()
