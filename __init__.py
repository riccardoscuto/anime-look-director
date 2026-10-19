bl_info = {
    "name": "Anime Look Director",
    "author": "Riccardo",
    "version": (0, 5, 0),
    "blender": (5, 1, 0),
    "location": "Scene Properties > Anime Look Director",
    "description": "Atmospheric palettes and a non-destructive anime compositor stack",
    "category": "Render",
}

from . import properties, compositor, palette, materials, shots, operators, panels

# palette/compositor/materials register the sun, God Rays and material sun
# frame handlers.
_modules = (properties, shots, palette, compositor, materials, operators, panels)


def register():
    for module in _modules:
        module.register()


def unregister():
    for module in reversed(_modules):
        module.unregister()
