
import sim
import threading


class SimulationPipeline(sim.Simulator):

    def __init__(self, first_simulation, n_steps=None):
        self._active_sim = first_simulation
        self._step_limit = n_steps

        self._past_timesteps = 0

        self._sim_provider_queue = []  # list of (provider, n_steps)

        self._simul_lock = threading.Lock()
        self._is_simulating = False

        self._simul_swap_lock = threading.Lock()

    def add_simulation(self, provider, n_steps=None):
        """
        :param provider: Simulator -> Simulator
        :param n_steps:
        """
        self._sim_provider_queue.append((provider, n_steps))

    def is_done(self):
        return self._active_sim.is_done() and len(self._sim_provider_queue) == 0

    def get_timestep(self):
        with self._simul_swap_lock:
            return self._past_timesteps + self._active_sim.get_timestep()

    def request_simulation_async(self):
        with self._simul_lock:
            if self._is_simulating:
                print("WARN: there's already a simulation happening, skipping request")
                return None
            else:
                self._is_simulating = True

        return super().request_simulation_async()

    def do_simulation(self):
        with self._simul_lock:
            self._is_simulating = True

        self._active_sim.do_simulation()

        if len(self._sim_provider_queue) > 0:
            if self._active_sim.is_done() or (self._step_limit is not None and self._active_sim.get_timestep() >= self._step_limit):
                with self._simul_swap_lock:
                    print("INFO: moving to next simulation in pipeline")
                    self._past_timesteps += self._active_sim.get_timestep()

                    provider, n_steps = self._sim_provider_queue.pop(0)
                    self._step_limit = n_steps
                    self._active_sim = provider(self._active_sim)

        with self._simul_lock:
            self._is_simulating = False

    def is_simulating(self):
        with self._simul_lock:
            return self._is_simulating

    def fetch_colors_safely(self, rect, color_funct, expected_total_size=None):
        with self._simul_swap_lock:
            return self._active_sim.fetch_colors_safely(rect, color_funct, expected_total_size=expected_total_size)

    def get_percent_completed(self):
        return self._active_sim.get_percent_completed()

    def get_color_for_render(self, xy):
        return self._active_sim.get_color_for_render(xy)

    def get_size(self):
        return self._active_sim.get_size()



