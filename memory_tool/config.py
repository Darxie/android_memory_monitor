"""Configuration for Android memory monitoring tool."""

from typing import Dict, List, Optional

# Default monitoring interval in seconds
DEFAULT_LOG_INTERVAL = 5
MIN_LOG_INTERVAL = 1
MAX_LOG_INTERVAL = 300

# Application configurations
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
            "release": "com.roadlords.android",
            "debug": "com.roadlords.android",
        },
        "start_activity": "com.sygic.profi.platform.splashscreen.feature.ui.main.SplashScreenActivity",
        "use_cases": ["ew_compute", "ew_search"],
    },
}


def validate_app_config(app_name: str) -> bool:
    """
    Validate application configuration.
    
    Args:
        app_name: Application name to validate
        
    Returns:
        True if valid, False otherwise
    """
    if app_name not in APPLICATIONS:
        return False
    
    app_config = APPLICATIONS[app_name]
    required_keys = ["internal_name", "package_name", "use_cases"]
    
    for key in required_keys:
        if key not in app_config:
            return False
    
    if not isinstance(app_config["use_cases"], list) or not app_config["use_cases"]:
        return False
    
    if not isinstance(app_config["package_name"], dict):
        return False
    
    return True


def get_package_name(app_name: str, build_version: str = "release") -> Optional[str]:
    """
    Get package name for app and build version.
    
    Args:
        app_name: Application name
        build_version: Build version (release/debug)
        
    Returns:
        Package name or None if not found
    """
    if app_name not in APPLICATIONS:
        return None
    
    return APPLICATIONS[app_name]["package_name"].get(build_version)


def get_use_cases(app_name: str) -> List[str]:
    """
    Get available use cases for an application.
    
    Args:
        app_name: Application name
        
    Returns:
        List of use case names
    """
    if app_name not in APPLICATIONS:
        return []
    
    return APPLICATIONS[app_name].get("use_cases", [])
