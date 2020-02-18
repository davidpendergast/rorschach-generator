
import sim as sim

# layers
STATIC_PRESSURE = "static_pressure"
DYNAMIC_PRESSURE = "dyna_pressure"
INK = "ink"
DRIED_INK = "dried_ink"


class InkblotSimulator(sim.ParticleSimulator):

    def __init__(self, w, h):
        sim.ParticleSimulator.__init__(self, w, h)

    def update_layer(self, layer_key, val, xy, t, write_buffer):
        pass

    def get_color_for_render(self, xy):
        return (0, 0, 0)