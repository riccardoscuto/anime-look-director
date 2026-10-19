bl_info = {
    "name": "Anime Look Director",
    "author": "Riccardo",
    "version": (0, 2, 1),
    "blender": (5, 1, 0),
    "location": "Scene Properties > Anime Look Director",
    "description": "Atmospheric palettes and a non-destructive anime compositor stack",
    "category": "Render",
}

from . import properties, compositor, palette, materials, operators, panels

# compositor, palette and materials are helper modules without registration hooks.
_modules = (properties, operators, panels)


def register():
    for module in _modules:
        module.register()


def unregister():
    for module in reversed(_modules):
        module.unregister()
