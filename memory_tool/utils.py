import logging
from pathlib import Path


def _write_to_file(filename, content) -> bool:
    """Append content to a file, creating parent directories as needed."""
    try:
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        with open(filename, "a", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        logging.error(f"Error writing to file {filename}: {e}")
        return False
