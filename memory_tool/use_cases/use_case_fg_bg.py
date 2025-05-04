import time
import utils
import logging


def simulate_user_interactions(memory_tool):
    for i in range(0, 100):
        logging.info(f"Mambo number {i+1}")
        time.sleep(25)
        utils.execute_adb_command(
            [
                "adb",
                "shell",
                "monkey",
                "-p ",
                "com.google.android.calendar",
                "1",
            ],
        )
        logging.info("switched to calendar")
        time.sleep(25)
        utils.execute_adb_command(
            [
                "adb",
                "shell",
                "am",
                "start",
                "-n",
                "com.sygic.profi.beta/com.sygic.profi.platform.splashscreen.feature.ui.main.SplashScreenActivity",
            ]
        )
        logging.info("switched to profi navi")
    memory_tool.stop_monitoring()
