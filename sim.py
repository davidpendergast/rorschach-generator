
import random


class ParticleSimulator:

    def __init__(self, w, h, rand_seed=None):
        self.w = w
        self.h = h

        self.t = 0

        self._static_layers = {}  # static = not updated

        self._dynamic_layers = {}

        if rand_seed is not None:
            random.seed(rand_seed)

    def add_layer(self, key, min_val=None, max_val=None, is_static=False, initializer_funct=None, default_val=0, out_of_bounds_val=0):
        if self.get_layer(key) is not None:
            raise ValueError("key already in use: {}".format(key))

        new_layer = _ParticleLayer(self.w, self.h, default_val=default_val, min_val=min_val, max_val=max_val,
                                   out_of_bounds_val=out_of_bounds_val)
        if initializer_funct is not None:
            for x in range(0, self.w):
                for y in range(0, self.h):
                    new_layer.set_value((x, y), initializer_funct((x, y)))

        if is_static:
            self._static_layers[key] = new_layer
        else:
            self._dynamic_layers[key] = new_layer

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

    def do_simul(self):
        self.t += 1

        write_buffers = {}
        for layer_key in self._dynamic_layers:
            write_buffers[layer_key] = self._dynamic_layers[layer_key].make_copy()

        for y in range(0, self.h):
            for x in range(0, self.w):
                self.update_layers((x, y), self.t, write_buffers)

        self._dynamic_layers = write_buffers

    def update_layers(self, xy, t, write_buffers):
        raise NotImplementedError()

    def get_color_for_render(self, xy):
        raise NotImplementedError()


class _ParticleLayer:

    def __init__(self, w, h, default_val=0, min_val=None, max_val=None, out_of_bounds_val=0):
        self.w = w
        self.h = h
        self._oob_val = out_of_bounds_val
        self._default_val = default_val

        self._max_val = max_val
        self._min_val = min_val

        self._array = []
        for i in range(0, self.h):
            self._array.append([default_val] * self.w)

    def make_copy(self, leave_empty=False):
        res = _ParticleLayer(self.w, self.h,
                             default_val=self._default_val,
                             min_val=self._min_val,
                             max_val=self._max_val,
                             out_of_bounds_val=self._oob_val)
        if not leave_empty:
            for y in range(0, self.h):
                for x in range(0, self.w):
                    res.set_value((x, y), self.get_value((x, y)))
        return res

    def is_valid(self, xy):
        return 0 <= xy[0] < self.w and 0 <= xy[1] < self.h

    def set_value(self, xy, val):
        if self.is_valid(xy):
            self._array[xy[0]][xy[1]] = val

    def add_value(self, xy, val):
        if self.is_valid(xy):
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

    def get_neighbors(self, xy, valid_only=True, include_diagonals=False, shuffled=False):
        res = []
        candidates = [(-1, 0), (0, -1), (1, 0), (0, 1)]
        if include_diagonals:
            candidates.extend([(-1, -1), (1, -1), (1, 1), (-1, 1)])
        for c in candidates:
            if not valid_only or self.is_valid(c):
                res.append((c[0] + xy[0], c[1] + xy[1]))
        if shuffled:
            random.shuffle(res)
        return res
