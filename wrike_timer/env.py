"""Guard against snap-packaged terminals (e.g. VS Code's integrated terminal)
injecting GTK/GIO env vars that point at /snap/.../usr/lib, built against the
snap's bundled libc. When pystray loads GTK from a non-snap Python, that
mismatch causes a `symbol lookup error` on libpthread. Only stripped when they
actually point at /snap/, so a normal terminal is unaffected.
"""

import os

SNAP_POLLUTED_ENV_VARS = (
    "GTK_PATH",
    "GTK_EXE_PREFIX",
    "GTK_IM_MODULE_FILE",
    "LOCPATH",
    "GIO_MODULE_DIR",
    "GSETTINGS_SCHEMA_DIR",
    "XDG_DATA_DIRS",
    "XDG_DATA_HOME",
)


def sanitize_snap_env():
    for name in SNAP_POLLUTED_ENV_VARS:
        if "/snap/" in os.environ.get(name, ""):
            os.environ.pop(name, None)
