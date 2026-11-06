#!/usr/bin/env python3
"""Check build prerequisites without invoking licensing or reading license files."""

import os
from pathlib import Path
import shutil
import sys


def main():
    problems = []
    for name in ("QNX_HOST", "QNX_TARGET"):
        value = os.environ.get(name)
        if not value or not Path(value).is_dir():
            problems.append(f"{name} is unset or not a directory; source qnxsdp-env.sh")

    if not shutil.which("qcc"):
        problems.append("qcc is not on PATH; source qnxsdp-env.sh")

    # QNX's licensing library writes a lock next to the installed license.
    # Check directory metadata only. Do not create a lock or copy license data.
    config = Path(os.environ.get("QNX_CONFIGURATION_EXCLUSIVE")
                  or os.environ.get("QNX_CONFIGURATION")
                  or Path.home() / ".qnx")
    license_dir = config / "license"
    try:
        if os.statvfs(license_dir).f_flag & os.ST_RDONLY:
            problems.append("QNX license directory is on a read-only filesystem; "
                            "qcc cannot acquire its license lock")
        elif not os.access(license_dir, os.W_OK | os.X_OK):
            problems.append("QNX license directory is not writable/searchable "
                            "by this process")
    except OSError as error:
        problems.append(f"QNX license directory is unavailable ({error.strerror}); "
                        "check the existing local SDK configuration")

    if problems:
        for problem in problems:
            print(f"BLOCKED: {problem}", file=sys.stderr)
        print("Run in the authorized local SDK context. Do not copy credentials "
              "or reinstall the SDK to work around execution restrictions.",
              file=sys.stderr)
        return 2
    print("QNX build prerequisites available; compiler licensing and native "
          "execution still require their own checks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
