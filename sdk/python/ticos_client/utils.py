import os
import re
import subprocess
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def find_tf_root_directory() -> Optional[str]:
    """
    Find the root directory of the TF card.

    Returns:
        The root directory of the TF card, or None if not found
    """
    try:
        # Check if we're running on Linux
        if not os.name == "posix":
            logger.warning(
                "Not running on Linux system, TF card detection not supported"
            )
            return None

        # Get mount points from the system
        result = subprocess.run(["mount"], capture_output=True, text=True)

        if result.returncode != 0:
            logger.warning(f"Failed to get mount points: {result.stderr}")
            return None

        # Parse mount output
        for line in result.stdout.splitlines():
            # Format: device on mount_point type filesystem (options)
            parts = line.split()
            if len(parts) >= 3:
                mount_point = parts[2]

                # Check if this mount point is in /media/
                if mount_point.startswith("/media/"):
                    mount_dir = Path(mount_point)
                    if mount_dir.exists() and mount_dir.is_dir():
                        # Check if this looks like a TF card mount
                        mount_name = mount_point.rsplit("/", 1)[-1]
                        if re.match(
                            r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
                            mount_name,
                        ) or re.match(
                            r"^[a-zA-Z0-9_\-]+$", mount_name
                        ):  # Also accept simple names
                            logger.info(f"Found TF card mount point: {mount_dir}")
                            return str(mount_dir)

        logger.warning("No TF card mount point found")
        return None

    except Exception as e:
        logger.warning(f"Error finding TF card mount point: {e}")
        return None
