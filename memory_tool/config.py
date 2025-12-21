APPLICATIONS = {
    "Sygic Profi": {
        "internal_name": "sygic_profi",
        "package_name": {
            "release": "com.sygic.profi.beta",
            "debug": "com.sygic.profi.beta.debug",
        },
        "start_activity": "com.sygic.profi.platform.splashscreen.feature.ui.main.SplashScreenActivity",
        "use_cases": [
            "search",
            "demonstrate",
            "compute",
            "fg_bg",
            "zoom",
            "freedrive",
            "demon_fg_bg",
            "recompute",
        ],
    },
    "EW Navi": {
        "internal_name": "ew_navi",
        "package_name": {
            "release": "com.roadlods.android",
            "debug": "com.roadlods.android",
        },
        "start_activity": "com.sygic.profi.platform.splashscreen.feature.ui.main.SplashScreenActivity",
        "use_cases": ["sample_1", "sample_2"],
    },
}

# Global Configuration
DEFAULT_LOG_INTERVAL = 5  # Seconds between memory checks
