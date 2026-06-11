"""Runtime hook to configure GObject-Introspection paths for the frozen bundle.

On Linux, PyWebView's GTK backend uses GObject-Introspection (gi) to call
WebKit2GTK, Gtk, and other system libraries through Python. The gi module
reads GObject-Introspection typelib files (.typelib) that describe the C APIs.

In a frozen bundle, the typelibs must be discoverable at runtime via the
GI_TYPELIB_PATH environment variable. This hook sets it to point to the bundled
typelib location so `import gi` and subsequent library introspection succeed.
"""

import os
import sys
from pathlib import Path

# _MEIPASS is set by PyInstaller to the bundle root (_internal/ on recent builds).
meipass = Path(getattr(sys, "_MEIPASS", "."))

# Set GI_TYPELIB_PATH to find bundled typelibs. The structure after freeze:
#   _internal/gi/repository/typelibs/  (or just _internal/lib/girepository-1.0/)
# The exact location varies by PyInstaller version and gi version; check both.
typelib_paths = [
    meipass / "gi" / "repository" / "typelibs",
    meipass / "lib" / "girepository-1.0",
    meipass / "lib64" / "girepository-1.0",
]
existing_paths = [str(p) for p in typelib_paths if p.exists()]

if existing_paths:
    existing_gi_typelib = os.environ.get("GI_TYPELIB_PATH", "")
    new_paths = existing_paths + (existing_gi_typelib.split(":") if existing_gi_typelib else [])
    os.environ["GI_TYPELIB_PATH"] = ":".join(new_paths)

# Also set LD_LIBRARY_PATH to find bundled cairo/glib/gobject shared libs if needed.
# (PyInstaller should have already bundled them in _internal/lib.)
lib_dir = meipass / "lib"
if lib_dir.exists():
    existing_ld = os.environ.get("LD_LIBRARY_PATH", "")
    new_lib_paths = [str(lib_dir)] + (existing_ld.split(":") if existing_ld else [])
    os.environ["LD_LIBRARY_PATH"] = ":".join(new_lib_paths)
