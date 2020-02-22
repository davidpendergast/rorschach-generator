import pygame
import colors
import time
import pathlib


class SimulationDisplay:

    FPS = 20

    def __init__(self, simulation_provider, name="Simulation", window_size=(640, 480)):
        self.simulation_provider = simulation_provider
        self.simulation = simulation_provider()

        self.auto_play = True
        self.auto_play_delay = 200     # milliseconds
        self.min_auto_play_delay = 200
        self.max_auto_play_delay = 5000
        self.auto_play_increment = 200
        self.has_finished = False

        self.show_loading_bar = True

        self.last_step_time = 0

        self._last_timestep_drawn = -1
        self._simul_surface_dirty = True
        self.simulation_surface = None

        self._name = name
        self._initial_window_size = window_size

        self._record_output = False
        self._output_dest = pathlib.Path("outputs/default/")
        self._output_size = (640, 480)
        self._last_timestep_saved = -1

        self.screen = None

    def restart_simulation(self):
        print("INFO: restarting simulation")
        self._last_timestep_drawn = -1
        self._last_timestep_saved = -1
        self._simul_surface_dirty = True
        self.auto_play = True
        self.simulation = self.simulation_provider()
        self.has_finished = False

    def _draw_simulation(self, timestep):
        if self._simul_surface_dirty:
            rect_size = self.simulation_surface.get_size()
            rect = [0, 0, rect_size[0], rect_size[1]]

            def set_pixel(xy, color):
                self.simulation_surface.set_at(xy, color)

            self.simulation_surface.lock()
            self.simulation.fetch_colors_safely(rect, set_pixel, expected_total_size=rect_size)
            self.simulation_surface.unlock()

            self._last_timestep_drawn = timestep

    def record_output(self, output_dir=None, img_size=None):
        self._record_output = True
        self._output_dest = pathlib.Path(output_dir) if output_dir is not None else self._output_dest
        self._output_size = img_size  # None means use the simulation's actual size
        self._last_timestep_saved = -1
        print("INFO: recording outputs to: {}".format(self._output_dest))

    def _save_output_to_disk_if_necessary(self, simul_surface, timestep):
        if timestep != self._last_timestep_saved:
            self._last_timestep_saved = timestep
            self._output_dest.mkdir(parents=True, exist_ok=True)
            simul_size = simul_surface.get_size()

            if self._output_size is None or simul_size == self._output_size:
                surface_to_save = simul_surface
            else:
                surface_to_save = pygame.Surface(self._output_size, flags=pygame.SRCALPHA | pygame.HWSURFACE)
                pygame.transform.scale(simul_surface, self._output_size, surface_to_save)

            fname = "output_{}.png".format(str(timestep).zfill(4))
            filepath = pathlib.Path(self._output_dest, fname)

            print("INFO: writing {}".format(filepath))
            pygame.image.save(surface_to_save, str(filepath))

    def _draw_loading_bar(self):
        prog = self.simulation.get_percent_completed()
        if prog <= 0:
            return
        else:
            screen_size = self.screen.get_size()
            bar_h = min(4, 8 * screen_size[1] // 480)
            bar_w = int(prog * screen_size[0])

            pygame.draw.rect(self.screen, colors.RED, [0, screen_size[1]-bar_h, bar_w, bar_h])

    def start(self):
        pygame.init()

        pygame.display.set_caption(self._name)

        self.screen = pygame.display.set_mode(self._initial_window_size, pygame.RESIZABLE | pygame.DOUBLEBUF)

        running = True
        clock = pygame.time.Clock()

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    continue

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        self.restart_simulation()
                    elif event.key == pygame.K_q:
                        if self._output_dest is not None:
                            self._record_output = not self._record_output
                        else:
                            self._record_output = False
                        print("INFO: set record_output={}".format(self._record_output))
                    elif event.key == pygame.K_ESCAPE:
                        running = False
                        continue
                    elif event.key == pygame.K_RETURN:
                        self.auto_play = not self.auto_play
                        print("INFO: set auto_play={}".format(self.auto_play))
                    elif event.key == pygame.K_RIGHT:
                        self.auto_play_delay = min(self.min_auto_play_delay,
                                                   self.auto_play_delay - self.auto_play_increment)
                    elif event.key == pygame.K_LEFT:
                        self.auto_play_delay = max(self.max_auto_play_delay,
                                                   self.auto_play_delay + self.auto_play_increment)
                    elif event.key == pygame.K_l:
                        self.show_loading_bar = not self.show_loading_bar
                        print("INFO: set show_loading_bar={}".format(self.show_loading_bar))

            self.screen.fill(colors.WHITE)

            simul_size = self.simulation.get_size()
            if self.simulation_surface is None or self.simulation_surface.get_size() != simul_size:
                print("INFO: setting simulation surface size to: {}".format(simul_size))
                self.simulation_surface = pygame.Surface(simul_size, flags=pygame.SRCALPHA | pygame.HWSURFACE)

            timestep = self.simulation.get_timestep()

            if self._last_timestep_drawn != timestep:
                self._draw_simulation(timestep)

                if self._record_output:
                    self._save_output_to_disk_if_necessary(self.simulation_surface, timestep)

            screen_size = self.screen.get_size()
            pygame.transform.scale(self.simulation_surface, screen_size, self.screen)

            cur_time = int(time.time() * 1000)

            if self.simulation.is_simulating():
                if self.show_loading_bar and cur_time - self.last_step_time > 1000:
                    self._draw_loading_bar()
            elif not self.has_finished:
                if self.auto_play and cur_time - self.last_step_time >= self.auto_play_delay:
                    if self.simulation.is_done():
                        print("INFO: simulation is done")
                        self.has_finished = True
                    else:
                        self.simulation.request_simulation_async()
                        self.last_step_time = int(time.time() * 1000.0)

            clock.tick(SimulationDisplay.FPS)

            pygame.display.flip()
