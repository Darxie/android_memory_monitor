import time
import utils
import logging


def simulate_user_interactions(memory_tool):
    for i in range(1, 50):
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
                "com.sygic.profi.beta/com.sygic.aura.activity.NaviNativeActivity",
            ]
        )
        logging.info("switched to profi navi")
    memory_tool.stop_monitoring()
