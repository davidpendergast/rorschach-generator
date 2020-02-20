import random
import math

import sim
import colors
import visualizer


class BlobSimulator(sim.ParticleSimulator):

    BLOB_LAYER = "blobs"
    FITNESS_CALC_LAYER = "fitness"
    SCENT_LAYER = "scent"

    def __init__(self, w, h, intial_spawn_rate=0.1, inital_boundary_percent=0.25):
        sim.ParticleSimulator.__init__(self, w, h)

        self.ortho_weight = 2
        self.diag_weight = 1

        self.blob_scent_weight = 5
        self.scent_base_diffusion_rate = 1.0
        self.cooling_time = 100
        self.cooling_time_pow = 1

        self._diffusion_rate = -1

        def initializer(xy):
            if (w * inital_boundary_percent <= xy[0] <= w * (1 - inital_boundary_percent) and
                    h * inital_boundary_percent <= xy[1] <= h * (1 - inital_boundary_percent)):
                return 1 if random.random() < intial_spawn_rate else 0
            else:
                return 0

        self.add_layer(BlobSimulator.BLOB_LAYER, min_val=0, max_val=10, initializer_funct=initializer)
        self.add_layer(BlobSimulator.FITNESS_CALC_LAYER, default_val=-1, out_of_bounds_val=0, min_val=-1)
        self.add_layer(BlobSimulator.SCENT_LAYER, default_val=0, min_val=0)

    def get_color_for_render(self, xy):
        base_color = colors.WHITE
        if self.get_value(BlobSimulator.BLOB_LAYER, xy) > 0:
            return colors.BLACK
        elif self.blob_scent_weight > 0:
            colors_per_level = [base_color, colors.LIGHT_BLUE, colors.PURPLE, colors.LIGHT_RED, colors.YELLOW]
            scent_val = self.get_value(BlobSimulator.SCENT_LAYER, xy)

            for i in range(1, len(colors_per_level)):
                if scent_val < i * self.blob_scent_weight:
                    lerp_val = (scent_val - (i - 1) * self.blob_scent_weight) / self.blob_scent_weight
                    return colors.lerp(colors_per_level[i-1], colors_per_level[i],  lerp_val)

            return colors_per_level[-1]
        else:
            return base_color

    def _fitness_at(self, xy, t, write_buffers, minus_2_if_blocked=True):
        if minus_2_if_blocked and self.get_value(BlobSimulator.BLOB_LAYER, xy) > 0:
            return -2

        cur_val = write_buffers[BlobSimulator.FITNESS_CALC_LAYER].get_value(xy)
        if cur_val != -1:
            return cur_val
        else:
            new_val = self._calc_fitness(xy, t)
            write_buffers[BlobSimulator.FITNESS_CALC_LAYER].set_value_not_threadsafe(xy, new_val)
            return new_val

    def _calc_fitness(self, xy, t):
        blob_layer = self.get_layer(BlobSimulator.BLOB_LAYER)
        fitness = blob_layer.sum_neighbor_values(xy, func=lambda v: self.ortho_weight * v,
                                                 include_ortho=True, include_diagonals=False)

        fitness += blob_layer.sum_neighbor_values(xy, func=lambda v: self.diag_weight * v,
                                                  include_ortho=False, include_diagonals=True)

        if fitness > 0:
            fitness = math.sqrt(fitness)

        if blob_layer.get_value(xy) == 0:
            fitness += self.get_value(BlobSimulator.SCENT_LAYER, xy)
        else:
            fitness += self.get_value(BlobSimulator.SCENT_LAYER, xy) / 4  # not sure why

        return fitness

    def pre_update(self, t):
        self.get_layer(BlobSimulator.FITNESS_CALC_LAYER).fill_not_threadsafe(-1)

        cooling_scale = (1 - (t / self.cooling_time) ** (1 / self.cooling_time_pow))
        self._diffusion_rate = max(0, self.scent_base_diffusion_rate * cooling_scale)

    def count_blobs(self):
        count = 0
        for xy in self.all_points():
            count += self.get_value(BlobSimulator.BLOB_LAYER, xy)
        return count

    def update_layers(self, xy, t, write_buffers):
        scent_layer = self.get_layer(BlobSimulator.SCENT_LAYER)

        my_scent = scent_layer.get_value(xy)
        write_buffers[BlobSimulator.SCENT_LAYER].add_value(xy, -my_scent)
        if my_scent > 0.001 and self._diffusion_rate > 0:
            for n in scent_layer.get_neighbors(xy, include_ortho=True, include_diagonals=True):
                write_buffers[BlobSimulator.SCENT_LAYER].add_value(n, self._diffusion_rate * my_scent / 8)

        if self._diffusion_rate > 0 and self.get_value(BlobSimulator.BLOB_LAYER, xy) > 0:
            write_buffers[BlobSimulator.SCENT_LAYER].add_value(xy, self._diffusion_rate * self.blob_scent_weight)

        blob_layer = self.get_layer(BlobSimulator.BLOB_LAYER)
        my_fitness = self._fitness_at(xy, t, write_buffers, minus_2_if_blocked=False)

        neighbors_with_fitness = []
        neighbor_fitnesses = []

        available_neighbors = []

        if blob_layer.get_value(xy) == 0:
            return

        for n in blob_layer.get_neighbors(xy, include_ortho=True, include_diagonals=False):
            n_fitness = self._fitness_at(n, t, write_buffers) - self.ortho_weight
            if n_fitness != -2:
                available_neighbors.append(n)
            if n_fitness > my_fitness and n_fitness > 0:
                neighbors_with_fitness.append(n)
                neighbor_fitnesses.append(n_fitness)

        for n in blob_layer.get_neighbors(xy, include_ortho=False, include_diagonals=True):
            n_fitness = self._fitness_at(n, t, write_buffers) - self.diag_weight
            if n_fitness != -2:
                available_neighbors.append(n)
            if n_fitness > my_fitness and n_fitness > 0:
                neighbors_with_fitness.append(n)
                neighbor_fitnesses.append(n_fitness)

        if len(neighbors_with_fitness) > 0:
            # move to a better neighbor
            new_xy = random.choices(population=neighbors_with_fitness, weights=neighbor_fitnesses, k=1)[0]
            write_buffers[BlobSimulator.BLOB_LAYER].add_value(xy, -1)
            write_buffers[BlobSimulator.BLOB_LAYER].add_value(new_xy, 1)

        elif my_fitness == 0 and len(available_neighbors) > 0:
            # rand walk
            new_xy = random.choice(available_neighbors)
            write_buffers[BlobSimulator.BLOB_LAYER].add_value(xy, -1)
            write_buffers[BlobSimulator.BLOB_LAYER].add_value(new_xy, 1)

        else:
            pass


def get_simulator():
    res = BlobSimulator(60, 40, intial_spawn_rate=0.99)
    res.cooling_time = 100
    res.cooling_time_pow = 1.0
    res.set_parallel(False)
    return res


if __name__ == "__main__":
    display = visualizer.SimulationDisplay(get_simulator, name="Blobs")
    display.set_stop_at_t(get_simulator().cooling_time)
    display.start()
