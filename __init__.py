bl_info = {
    "name": "Anime Look Director",
    "author": "Riccardo",
    "version": (2, 3, 0),
    "blender": (5, 1, 0),
    "location": "Scene Properties > Anime Look Director",
    "description": "Atmospheric palettes and a non-destructive anime compositor stack",
    "category": "Render",
}

from . import (properties, cameras, compositor, palette, materials, shots,
               look, operators, panels, fx)

# cameras, shots, palette, compositor, materials and fx register handlers.
_modules = (properties, cameras, shots, palette, compositor, materials,
            operators, panels, fx)


def register():
    for module in _modules:
        module.register()


def unregister():
    for module in reversed(_modules):
        module.unregister()
