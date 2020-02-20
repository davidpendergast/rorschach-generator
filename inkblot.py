import random
import math

import sim
import visualizer
import colors

# layers
STATIC_PRESSURE = "static_pressure"
INK = "ink"
DRIED_INK = "dried_ink"


class InkblotSimulator(sim.ParticleSimulator):

    def __init__(self, w, h, wet_ink_func):
        sim.ParticleSimulator.__init__(self, w, h)

        self.flow_rate = 0.25
        self.dried_ink_pressure_pcnt = 0.5

        self.max_static_pressure = 0.2
        self.boundary_pressure = 0.15

        self.pcnt_to_dry_base = 0.00
        self.pcnt_to_dry_inc_per_step = 0.01

        self.add_layer(INK, min_val=0, initializer_funct=wet_ink_func)
        self.add_layer(DRIED_INK, min_val=0, default_val=0)
        self.add_layer(STATIC_PRESSURE, is_static=True, initializer_funct=lambda xy: random.random())

    def _pressure_at(self, xy, t):
        res = (self.get_value(INK, xy) +
               self.max_static_pressure * self.get_value(STATIC_PRESSURE, xy) +
               self.dried_ink_pressure_pcnt * self.get_value(DRIED_INK, xy))

        if self.get_value(INK, xy) == 0 and self.get_value(DRIED_INK, xy) == 0:
            res += self.boundary_pressure

        return res

    def update_layers(self, xy, t, write_buffers):
        ink_val = self.get_value(INK, xy)
        if ink_val >= 0:
            orig_pressure = self._pressure_at(xy, t)

            # spread the ink
            low_pressure_neighbors = []  # list of ((x, y), pressure, flow_rate_mult)
            for n in self.get_layer(INK).get_neighbors(xy, valid_only=True, include_ortho=True, include_diagonals=True):
                pressure = self._pressure_at(n, t)
                is_ortho = abs(n[0] - xy[0]) + abs(n[1] - xy[1]) <= 1
                weight = 1 if is_ortho else 1 / 1.4142  # "care less" about diagonal neighbors
                if pressure < orig_pressure:
                    low_pressure_neighbors.append((n, pressure, weight))

            max_amount_to_flow = self.flow_rate * ink_val
            low_pressure_neighbors.sort(key=lambda lpn: lpn[2] * abs(orig_pressure - lpn[1]), reverse=True)
            amount_flowed = 0

            for lpn in low_pressure_neighbors:
                n_xy = lpn[0]
                n_pressure = lpn[1]
                my_pressure = orig_pressure - amount_flowed

                amount_to_give = min(max_amount_to_flow - amount_flowed,
                                     (my_pressure - n_pressure) / 2)

                if amount_to_give <= 0:
                    break  # no more ink to give
                else:
                    # give the ink
                    write_buffers[INK].add_value(n_xy, amount_to_give)
                    write_buffers[INK].add_value(xy, -amount_to_give)
                    amount_flowed += amount_to_give

            # dry a portion of what's left
            ink_remaining = ink_val - amount_flowed
            pcnt_to_dry = min(1, random.random() * (self.pcnt_to_dry_base + t * self.pcnt_to_dry_inc_per_step))
            amount_to_dry = pcnt_to_dry * ink_remaining

            write_buffers[INK].add_value(xy, -amount_to_dry)
            write_buffers[DRIED_INK].add_value(xy, amount_to_dry)

    def get_color_for_render(self, xy):
        ink_val = self.get_value(INK, xy)
        dried_val = self.get_value(DRIED_INK, xy)

        base_color = colors.WHITE
        wet_base_color = colors.RED
        dry_base_color = colors.BLACK

        if ink_val + dried_val > 0:
            max_val = 1
            ink_color = colors.lerp(base_color, wet_base_color, ink_val / max_val)
            dried_color = colors.lerp(base_color, dry_base_color, dried_val / max_val)

            pcnt_dried = dried_val / (ink_val + dried_val)
            return colors.lerp(ink_color, dried_color, pcnt_dried)
        else:
            return base_color


def get_droplet_func(center, radius, height):
    def _func(xy):
        dist = math.sqrt((center[0] - xy[0])**2 + (center[1] - xy[1])**2)
        if dist <= radius:
            return height * math.sqrt(1 - dist / radius)
        else:
            return 0
    return _func


def get_droplet_square_func(center, length, height):
    def _func(xy):
        if abs(center[0] - xy[0]) <= length / 2 and abs(center[1] - xy[1]) <= length / 2:
            return height
        else:
            return 0
    return _func


def get_simulator():
    w = 64
    h = int(w * 48 / 64)

    ink_height = 3
    ink_radius = w // 5

    # drop_func = get_droplet_func((w // 2, h // 2), ink_radius, ink_height)

    drop_func = get_droplet_square_func((w // 2, h // 2), ink_radius, ink_height)

    res = InkblotSimulator(w, h, drop_func)

    res.max_static_pressure = 0.5
    res.boundary_pressure = 0.65
    res.set_parallel(False)
    return res


if __name__ == "__main__":
    display = visualizer.SimulationDisplay(get_simulator, name="Inkblot")
    display.start()
