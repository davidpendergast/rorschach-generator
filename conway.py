import random

import sim
import colors
import visualizer


class ConwaySimulator(sim.ParticleSimulator):

    BLOB_LAYER = "blob_layer"

    def __init__(self, w, h, initial_spawn_rate=0.1,
                 die_counts_total=(0, 1, 4, 5, 6, 7, 8),
                 spawn_counts_total=(3,),
                 die_counts_diagonal=(),
                 spawn_counts_diagonal=(),
                 die_counts_ortho=(),
                 spawn_counts_ortho=()):

        sim.ParticleSimulator.__init__(self, w, h)

        self.initial_spawn_rate = initial_spawn_rate

        self.die_counts_total = die_counts_total
        self.spawn_counts_total = spawn_counts_total

        self.die_counts_diagonal = die_counts_diagonal
        self.spawn_counts_diagonal = spawn_counts_diagonal

        self.die_counts_ortho = die_counts_ortho
        self.spawn_counts_ortho = spawn_counts_ortho

        self.add_layer(ConwaySimulator.BLOB_LAYER, min_val=0, max_val=1,
                       initializer_funct=lambda xy: 1 if random.random() < initial_spawn_rate else 0)

    def get_color_for_render(self, xy):
        if self.get_value(ConwaySimulator.BLOB_LAYER, xy) > 0:
            return colors.BLACK
        else:
            return colors.WHITE

    def update_layers(self, xy, t, write_buffers):
        blob_layer = self.get_layer(ConwaySimulator.BLOB_LAYER)

        all_neighbors = blob_layer.get_neighbors(xy, valid_only=True, include_diagonals=True)
        total_count = sum([blob_layer.get_value(n) for n in all_neighbors])

        ortho_neighbors = blob_layer.get_neighbors(xy, valid_only=True, include_diagonals=False)
        ortho_count = sum([blob_layer.get_value(n) for n in ortho_neighbors])
        diag_count = total_count - ortho_count

        if blob_layer.get_value(xy) > 0:
            if (total_count in self.die_counts_total or ortho_count in self.die_counts_ortho
                    or diag_count in self.die_counts_diagonal):
                write_buffers[ConwaySimulator.BLOB_LAYER].add_value(xy, -1)
        else:
            if (total_count in self.spawn_counts_total or ortho_count in self.spawn_counts_ortho
                    or diag_count in self.spawn_counts_diagonal):
                write_buffers[ConwaySimulator.BLOB_LAYER].add_value(xy, 1)


if __name__ == "__main__":

    total_spawn = ()
    total_die = (0, 1, 3,)
    ortho_spawn = (2, 4)
    ortho_die = ()
    diag_spawn = ()
    diag_die = ()

    display = visualizer.SimulationDisplay(lambda: ConwaySimulator(64, 48),
                                                                 #initial_spawn_rate=0.15,
                                                                 #spawn_counts_total=total_spawn,
                                                                 #die_counts_total=total_die,
                                                                 #spawn_counts_ortho=ortho_spawn,
                                                                 #die_counts_ortho=ortho_die,
                                                                 #spawn_counts_diagonal=diag_spawn,
                                                                 #die_counts_diagonal=diag_die),
                                           name="Conway")
    display.start()


