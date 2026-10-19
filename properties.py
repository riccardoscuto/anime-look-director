import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, PointerProperty

PALETTES = [
    ("GOLDEN_HOUR", "Shinkai Golden Hour", "Warm backlight, orange halation"),
    ("SUMMER_NOON", "Ghibli Summer Noon", "Bright sky, clean high-key light"),
    ("RAINY_TOKYO", "Rainy Tokyo Night", "Cool rain-soaked night"),
    ("NEON_NIGHT", "Cyberpunk Neon", "Magenta and cyan artificial light"),
]


def _on_palette(self, context):
    try:
        from . import palette, compositor
        palette.apply_palette(context.scene, self.palette)
        if context.scene.compositing_node_group:
            compositor.build(context.scene)
    except Exception:
        pass


class ALD_Settings(bpy.types.PropertyGroup):
    palette: EnumProperty(
        name="Atmosphere",
        description="Global atmospheric palette",
        items=PALETTES,
        default="GOLDEN_HOUR",
        update=_on_palette,
    )
    halation: BoolProperty(name="Halation", default=True,
                           description="Warm bloom around highlights (Glare/Bloom)")
    painterly: BoolProperty(name="Painterly (Kuwahara)", default=True,
                            description="Kuwahara filter mixed in by depth")
    dispersion: BoolProperty(name="Chromatic dispersion", default=True,
                             description="Subtle lens dispersion")
    halation_strength: FloatProperty(name="Halation Strength", default=0.6,
                                     min=0.0, max=5.0)
    kuwahara_size: FloatProperty(name="Kuwahara Size", default=6.0,
                                 min=1.0, max=32.0)
    dispersion_amount: FloatProperty(name="Dispersion", default=0.01,
                                     min=0.0, max=1.0)
    depth_near: FloatProperty(name="Depth Near", default=4.0, min=0.0,
                              max=1000.0, subtype="DISTANCE")
    depth_far: FloatProperty(name="Depth Far", default=35.0, min=0.0,
                             max=10000.0, subtype="DISTANCE")


_classes = (ALD_Settings,)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.ald = PointerProperty(type=ALD_Settings)


def unregister():
    del bpy.types.Scene.ald
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
