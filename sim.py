
import random
import threading
import concurrent.futures as futures


class ParticleSimulator:

    CHUNK_SIZE = (64, 64)

    def __init__(self, w, h, rand_seed=None):
        self.w = w
        self.h = h

        self.t = 0

        self._static_layers = {}  # static = not updated

        self._dynamic_layers = {}

        if rand_seed is not None:
            random.seed(rand_seed)

        self._simul_lock = threading.Lock()
        self._color_lock = threading.Lock()

        # status stuff
        self._is_simulating = False
        self._pixels_done_count = AtomicInteger(value=0)

        self._parallel = True

    def get_size(self):
        return self.w, self.h

    def add_layer(self, key, min_val=None, max_val=None, is_static=False, initializer_funct=None, default_val=0, out_of_bounds_val=0):
        if self.get_layer(key) is not None:
            raise ValueError("key already in use: {}".format(key))

        new_layer = _ParticleLayer(self.w, self.h, default_val=default_val, min_val=min_val, max_val=max_val,
                                   out_of_bounds_val=out_of_bounds_val)
        if initializer_funct is not None:
            for x in range(0, self.w):
                for y in range(0, self.h):
                    new_layer.set_value_not_threadsafe((x, y), initializer_funct((x, y)))

        if is_static:
            self._static_layers[key] = new_layer
        else:
            self._dynamic_layers[key] = new_layer

    def set_parallel(self, val):
        self._parallel = val

    def get_layer(self, key):
        if key in self._static_layers:
            return self._static_layers[key]
        elif key in self._dynamic_layers:
            return self._dynamic_layers[key]
        else:
            return None

    def get_value(self, key, xy):
        return self.get_layer(key).get_value(xy)

    def get_timestep(self):
        return self.t

    def all_points(self):
        for y in range(0, self.h):
            for x in range(0, self.w):
                yield x, y

    def _make_chunks(self, t, write_buffers, progress_count):
        res = []
        chunk_w, chunk_h = ParticleSimulator.CHUNK_SIZE
        for x in range(0, self.w, chunk_w):
            for y in range(0, self.h, chunk_h):
                rect = [x,
                        y,
                        min(chunk_w, self.w - x),
                        min(chunk_h, self.h - y)]
                res.append(SimulChunk(self, rect, t, write_buffers, progress_count))
        return res

    def request_simulation_async(self):
        if self._simul_lock.locked():
            print("WARN: there's already a simulation happening, skipping request")
            return None

        x = threading.Thread(target=self.do_simulation, args=())
        x.start()

        return x

    def do_simulation(self):
        with self._simul_lock:
            self._is_simulating = True
            self.t += 1
            self._pixels_done_count.set(0)

            self.pre_update(self.t)

            write_buffers = {}
            for layer_key in self._dynamic_layers:
                write_buffers[layer_key] = self._dynamic_layers[layer_key].make_copy()

            if self._parallel:
                chunks = self._make_chunks(self.t, write_buffers, self._pixels_done_count)

                with futures.ThreadPoolExecutor() as executor:
                    executor.map(lambda chunk: chunk.simulate(), chunks)
            else:
                for y in range(0, self.h):
                    for x in range(0, self.w):
                        self.update_layers((x, y), self.t, write_buffers)

                    self._pixels_done_count.inc(amount=self.w)

            with self._color_lock:
                self._dynamic_layers = write_buffers

            self.post_update(self.t)

            self._is_simulating = False
            self._pixels_done_count.set(0)

    def is_simulating(self):
        return self._is_simulating

    def get_percent_completed(self):
        if not self.is_simulating():
            return 0.0
        else:
            pixels_done = self._pixels_done_count.get()
            return pixels_done / (self.w * self.h)

    def pre_update(self, t):
        pass

    def post_update(self, t):
        pass

    def update_layers(self, xy, t, write_buffers):
        raise NotImplementedError()

    def get_color_for_render(self, xy):
        raise NotImplementedError()

    def fetch_colors_safely(self, rect, color_funct):
        """
        :param rect: [x, y, w, h]
        :param color_funct: lambda xy, color -> None
        """
        with self._color_lock:
            for x in range(rect[0], rect[0] + rect[2]):
                for y in range(rect[1], rect[1] + rect[3]):
                    color_funct((x, y), self.get_color_for_render((x, y)))


class _ParticleLayer:

    def __init__(self, w, h, default_val=0, min_val=None, max_val=None, out_of_bounds_val=0):
        self.w = w
        self.h = h
        self._oob_val = out_of_bounds_val
        self._default_val = default_val

        self._max_val = max_val
        self._min_val = min_val

        self._write_lock = threading.Lock()

        self._array = []
        for _ in range(0, self.w):
            self._array.append([default_val] * self.h)

    def make_copy(self, leave_empty=False):
        res = _ParticleLayer(self.w, self.h,
                             default_val=self._default_val,
                             min_val=self._min_val,
                             max_val=self._max_val,
                             out_of_bounds_val=self._oob_val)
        if not leave_empty:
            for y in range(0, self.h):
                for x in range(0, self.w):
                    res.set_value_not_threadsafe((x, y), self.get_value((x, y)))
        return res

    def is_valid(self, xy):
        return 0 <= xy[0] < self.w and 0 <= xy[1] < self.h

    def set_value_not_threadsafe(self, xy, val):
        """don't call this during update_layers, lest ye violate thread safety"""
        if self.is_valid(xy):
            self._array[xy[0]][xy[1]] = val

    def fill_not_threadsafe(self, val):
        """don't call this during update_layers, lest ye violate thread safety"""
        for y in range(0, self.h):
            for x in range(0, self.w):
                self.set_value_not_threadsafe((x, y), val)

    def add_value(self, xy, val):
        if self.is_valid(xy):
            with self._write_lock:
                self._array[xy[0]][xy[1]] += val

    def get_value(self, xy):
        if self.is_valid(xy):
            val = self._array[xy[0]][xy[1]]
            if self._max_val is not None and val > self._max_val:
                return self._max_val
            elif self._min_val is not None and val < self._min_val:
                return self._min_val
            else:
                return val
        else:
            return self._oob_val

    def get_neighbors(self, xy, valid_only=True, include_ortho=True, include_diagonals=False, shuffled=False):
        res = []
        offsets = []

        if include_ortho:
            offsets.extend([(-1, 0), (0, -1), (1, 0), (0, 1)])

        if include_diagonals:
            offsets.extend([(-1, -1), (1, -1), (1, 1), (-1, 1)])

        for offs in offsets:
            candidate = (xy[0] + offs[0], xy[1] + offs[1])
            if not valid_only or self.is_valid(candidate):
                res.append(candidate)

        if shuffled:
            random.shuffle(res)
        return res

    def sum_neighbor_values(self, xy, func=lambda v: v, valid_only=True, include_ortho=True, include_diagonals=False):
        res = 0
        for n in self.get_neighbors(xy, valid_only=valid_only, include_ortho=include_ortho, include_diagonals=include_diagonals):
            res += func(self.get_value(n))
        return res


class SimulChunk:

    def __init__(self, simulation, rect, t, write_buffers, progress_counter):
        self.simulation = simulation
        self.rect = rect
        self.write_buffers = write_buffers
        self.t = t
        self.progress_counter = progress_counter

    def simulate(self):
        for y in range(self.rect[1], self.rect[1] + self.rect[3]):
            for x in range(self.rect[0], self.rect[0] + self.rect[2]):
                self.simulation.update_layers((x, y), self.t, self.write_buffers)
            self.progress_counter.inc(amount=self.rect[2])


class AtomicInteger:
    def __init__(self, value=0):
        self._value = value
        self._lock = threading.Lock()

    def inc(self, amount=1):
        with self._lock:
            self._value += amount
            return self._value

    def dec(self, amount=1):
        with self._lock:
            self._value -= amount
            return self._value

    def set(self, val):
        with self._lock:
            self._value = val

    def get(self):
        with self._lock:
            return self._value

