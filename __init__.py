bl_info = {
    "name": "ModularRenamer",
    "author": "Pluglug",
    "version": (0, 1, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Tool Tab",
    "description": "A modular, customizable object naming system",
    "warning": "",
    "doc_url": "",
    "category": "3D View",
}

import bpy
from . import preferences
from . import core
from . import ui


# Registration
def register():
    preferences.register()
    ui.register()


def unregister():
    ui.unregister()
    preferences.unregister()


if __name__ == "__main__":
    register()
