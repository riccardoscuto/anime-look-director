"""Build the installable extension zip into ``dist/``.

The manifest excludes the research evidence and the dev files, so the package
contains only the add-on code, the manifest and the user docs.

Run::

    blender -b --factory-startup --python preset_dev/build_release.py
"""

import os
import subprocess
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DIST = os.path.join(ROOT, "dist")


def main():
    os.makedirs(DIST, exist_ok=True)
    result = subprocess.run(
        [bpy.app.binary_path, "-b", "--factory-startup",
         "--command", "extension", "build",
         "--source-dir", ROOT,
         "--output-dir", DIST])
    if result.returncode:
        print("ALD BUILD: FAIL")
        return 1
    print("ALD BUILD: PASS", DIST)
    return 0


if __name__ == "__main__":
    sys.exit(main())
