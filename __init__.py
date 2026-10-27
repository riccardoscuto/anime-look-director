bl_info = {
    "name": "Anime Look Director",
    "author": "Riccardo",
    "version": (2, 59, 0),
    "blender": (5, 1, 0),
    "location": "Scene Properties > Anime Look Director",
    "description": "Procedural anime skies, atmospheric palettes and an optional compositor",
    "category": "Render",
}

from . import (properties, cameras, compositor, palette, materials, shots,
               look, operators, panels)

# cameras, shots, palette, compositor and materials register handlers.
_modules = (properties, cameras, shots, palette, compositor, materials,
            operators, panels)


def register():
    for module in _modules:
        module.register()


def unregister():
    for module in reversed(_modules):
        module.unregister()
