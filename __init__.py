bl_info = {
    "name": "Anime Look Director",
    "author": "Riccardo",
    "version": (0, 4, 0),
    "blender": (5, 1, 0),
    "location": "Scene Properties > Anime Look Director",
    "description": "Atmospheric palettes and a non-destructive anime compositor stack",
    "category": "Render",
}

from . import properties, compositor, palette, materials, shots, operators, panels

# palette/compositor register the sun + God Rays frame handlers.
_modules = (properties, shots, palette, compositor, operators, panels)


def register():
    for module in _modules:
        module.register()


def unregister():
    for module in reversed(_modules):
        module.unregister()
