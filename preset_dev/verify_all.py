"""Run the whole verification chain: gate, duplicate fixture, audit.

Run with Blender (it needs the binary path)::

    blender -b --factory-startup --python preset_dev/verify_all.py

Every step is a fresh factory-startup Blender, so the duplicate fixture is not
polluted by the multi-scene gate. The process exits 1 when any step fails.
"""

import os
import subprocess
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STEPS = (
    ("gate [structural/runtime/visual]", "verify.py"),
    ("fixture [lifecycle]", "world_fixture.py"),
    ("audit [reduction/world]", "audit_world.py"),
)


def main():
    failed = []
    for name, script in STEPS:
        print("ALD ALL:", name)
        result = subprocess.run(
            [bpy.app.binary_path, "-b", "--factory-startup",
             "--python-exit-code", "1",
             "--python", os.path.join(HERE, script)],
            cwd=ROOT)
        print("ALD ALL:", name, "exit", result.returncode)
        if result.returncode:
            failed.append(name)
    if failed:
        print("ALD ALL: FAIL (%s)" % ", ".join(failed))
        return 1
    print("ALD ALL: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
