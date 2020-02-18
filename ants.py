import random
import time

import sim as sim
import colors as colors


class AntSimulator(sim.ParticleSimulator):

    TRAIL_LAYER = "TRAIL"
    ANT_LAYER = "ANTS"
    DEAD_ANT_LAYER = "DEAD_ANTS"

    def __init__(self, w, h, initial_spawn_chance=0.01, split_chance=0.01, trail_strength=16):
        sim.ParticleSimulator.__init__(self, w, h)

        self.initial_spawn_chance = initial_spawn_chance
        self.split_chance = split_chance
        self.trail_strength = trail_strength

        self.add_layer(AntSimulator.ANT_LAYER, min_val=0,
                       initializer_funct=lambda xy: 1 if random.random() < self.initial_spawn_chance else 0)
        self.add_layer(AntSimulator.TRAIL_LAYER, min_val=0, max_val=trail_strength, default_val=0)
        self.add_layer(AntSimulator.DEAD_ANT_LAYER, min_val=0, default_val=0)

    def get_color_for_render(self, xy):
        if self.get_value(AntSimulator.ANT_LAYER, xy) > 0:
            return colors.BLACK

        if self.get_value(AntSimulator.DEAD_ANT_LAYER, xy) > 0:
            return colors.RED

        base_color = colors.WHITE

        trail_val = self.get_value(AntSimulator.TRAIL_LAYER, xy)
        if trail_val > 0:
            return colors.lerp(base_color, colors.PURPLE, trail_val / self.trail_strength)
        else:
            return base_color

    def num_ants_alive(self):
        count = 0
        for xy in self.all_points():
            count += self.get_value(AntSimulator.ANT_LAYER, xy)
        return count

    def update_layers(self, xy, t, write_buffers):
        ant_layer = self.get_layer(AntSimulator.ANT_LAYER)
        trail_layer = self.get_layer(AntSimulator.TRAIL_LAYER)
        dead_layer = self.get_layer(AntSimulator.DEAD_ANT_LAYER)

        ant_val = ant_layer.get_value(xy)
        if ant_val > 0:
            for _ in range(0, ant_val):
                neighbors = ant_layer.get_neighbors(xy, include_diagonals=True, shuffled=True)
                neighbors = [n for n in neighbors if trail_layer.get_value(n) == 0 and dead_layer.get_value(n) == 0]

                if len(neighbors) >= 2 and random.random() < self.split_chance:
                    # we can split
                    write_buffers[AntSimulator.ANT_LAYER].add_value(neighbors[0], 1)
                    write_buffers[AntSimulator.ANT_LAYER].add_value(neighbors[1], 1)
                    write_buffers[AntSimulator.ANT_LAYER].add_value(xy, -1)
                    write_buffers[AntSimulator.TRAIL_LAYER].add_value(xy, self.trail_strength)

                elif len(neighbors) > 0:
                    # we can move
                    write_buffers[AntSimulator.ANT_LAYER].add_value(neighbors[0], 1)
                    write_buffers[AntSimulator.ANT_LAYER].add_value(xy, -1)
                    write_buffers[AntSimulator.TRAIL_LAYER].add_value(xy, self.trail_strength)

                else:
                    # we died (._.)
                    write_buffers[AntSimulator.ANT_LAYER].add_value(xy, -1)
                    write_buffers[AntSimulator.DEAD_ANT_LAYER].add_value(xy, 1)
        else:
            write_buffers[AntSimulator.TRAIL_LAYER].add_value(xy, -1)


if __name__ == "__main__":
    ant_sim = AntSimulator(6400, 64)
    ant_sim.request_simulation_async()

    N = 20
    while True:
        time.sleep(0.25)
        if ant_sim.is_simulating():
            print("step {}:\t{:.1%} done".format(
                ant_sim.get_timestep(), ant_sim.get_percent_completed()))
        else:
            print("step {}:\tfinished with {} ants alive.\n".format(
                ant_sim.get_timestep(), ant_sim.num_ants_alive()))

            if ant_sim.get_timestep() >= N:
                break
            else:
                ant_sim.request_simulation_async()

    #for i in range(0, 20):
    #    alive = ant_sim.num_ants_alive()
    #    print("t={}:\tants={}".format(ant_sim.get_timestep(), alive))
    #
    #    ant_sim.do_simulation()



