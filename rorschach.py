import sim
import blobs
import pipeline
import inkblot
import visualizer

import os
import pathlib
import random


def _get_rand_param_val(name, min_val, max_val, is_percent=False, as_int=False):
    res = min_val + random.random() * (max_val - min_val)

    if as_int:
        res = int(res)

    if is_percent:
        print("INFO: using {}: {}".format(name, "{0:.0%}".format(res)))
    else:
        print("INFO: using {}: {}".format(name, res))
    return res


def get_blob_sim(w, h, cooling_time):
    min_spawn_rate = 0.6
    max_spawn_rate = 0.8
    spawn_rate = _get_rand_param_val("initial blob density", min_spawn_rate, max_spawn_rate, is_percent=True)

    res = blobs.BlobSimulator(w, h, intial_spawn_rate=spawn_rate)

    res.cooling_time = cooling_time
    res.cooling_time_pow = 1.0
    res.set_parallel(False)

    return res


def get_blob_duplicator(blob_sim):
    res = get_blob_sim(blob_sim.w, blob_sim.h, blob_sim.cooling_time)
    new_blob_layer = res.get_layer(blobs.BlobSimulator.BLOB_LAYER)
    for xy in res.all_points():
        val = blob_sim.get_value(blobs.BlobSimulator.BLOB_LAYER, xy)
        new_blob_layer.set_value_not_threadsafe(xy, val)

    return res


def get_blob_to_inkblot_mapper(blob_sim):
    ink_height = _get_rand_param_val("ink height", 1.2, 1.35)
    basic_inkify = False

    size = (blob_sim.w * upscale, blob_sim.h * upscale)

    res = inkblot.InkblotSimulator(size[0], size[1])

    blob_layer = blob_sim.get_layer(blobs.BlobSimulator.BLOB_LAYER)
    ink_layer = res.get_layer(inkblot.INK)

    if basic_inkify:
        xfer_func = get_rect_mapping_function((0, 0), size, (0, 0), blob_sim.get_size())
        xfer_layer_to_layer(blob_layer, ink_layer,
                            l2_xy_to_l1_xy_func=xfer_func,
                            value_xform=lambda blob_val, ink_val: ink_val + (ink_height if blob_val > 0 else 0))

    else:
        min_x_overlap_pcnt = 0.10  # controls how much the mirrored blobs will overlap
        max_x_overlap_pcnt = 0.33
        x_overlap_pcnt = _get_rand_param_val("overlap percentage", min_x_overlap_pcnt, max_x_overlap_pcnt, is_percent=True)

        x_offs = int(size[0] * x_overlap_pcnt)

        mid_x = size[0] // 2
        mid_y = size[1] // 2

        xfer_func_left = get_rect_mapping_function((mid_x + x_offs, mid_y - size[0] // 2),
                                                   (mid_x + x_offs - size[1], mid_y + size[0] // 2),
                                                   (0, 0), blob_sim.get_size(), swap_x_and_y=True)
        xfer_layer_to_layer(blob_layer, ink_layer,
                            l2_xy_to_l1_xy_func=xfer_func_left,
                            value_xform=lambda blob_val, ink_val: ink_val + (ink_height if blob_val > 0 else 0))

        xfer_func_right = get_rect_mapping_function((mid_x - x_offs, mid_y - size[0] // 2),
                                                    (mid_x - x_offs + size[1], mid_y + size[0] // 2),
                                                    (0, 0), blob_sim.get_size(), swap_x_and_y=True)
        xfer_layer_to_layer(blob_layer, ink_layer,
                            l2_xy_to_l1_xy_func=xfer_func_right,
                            value_xform=lambda blob_val, ink_val: ink_val + (ink_height if blob_val > 0 else 0))

    res.max_static_pressure = 0.45
    res.boundary_pressure = 1.4  # 1.2
    res.max_val_for_render = 1.25
    res.set_parallel(False)

    return res


def get_rect_mapping_function(r1_x1y1, r1_x2y2, r2_x1y1, r2_x2y2, swap_x_and_y=False):

    def _map_it(r1_xy):
        x, y = r1_xy
        x_t = (x - r1_x1y1[0]) / (r1_x2y2[0] - r1_x1y1[0])
        y_t = (y - r1_x1y1[1]) / (r1_x2y2[1] - r1_x1y1[1])

        if swap_x_and_y:
            temp = x_t
            x_t = y_t
            y_t = temp

        return (
            round((1 - x_t) * r2_x1y1[0] + x_t * r2_x2y2[0]),
            round((1 - y_t) * r2_x1y1[1] + y_t * r2_x2y2[1])
        )

    return _map_it


def xfer_layer_to_layer(l1, l2, l2_xy_to_l1_xy_func=lambda xy: xy, value_xform=lambda l1_v, l2_v: l1_v + l2_v):
    for x in range(0, l2.w):
        for y in range(0, l2.h):
            l2_xy = (x, y)
            l1_xy = l2_xy_to_l1_xy_func(l2_xy)

            l1_val = l1.get_value(l1_xy)
            l2_val = l2.get_value(l2_xy)

            new_l2_val = value_xform(l1_val, l2_val)
            l2.set_value_not_threadsafe(l2_xy, new_l2_val)


# global params
w = 60
h = int(w / (640 / 480))
upscale = 3


def get_pipeline():
    blob_cooling_time = 100
    blob_sim_time = int(blob_cooling_time * 0.95)

    pipe = pipeline.SimulationPipeline(get_blob_sim(w, h, blob_cooling_time), n_steps=blob_sim_time)

    pipe.add_simulation(get_blob_to_inkblot_mapper)

    return pipe


if __name__ == "__main__":
    display = visualizer.SimulationDisplay(get_pipeline, name="Rorschach")

    output_base_dir = pathlib.Path("output/rorschach/")
    n = len(os.listdir(str(output_base_dir)))
    output_dir = pathlib.Path(output_base_dir, "run{}/".format(n))

    img_size = (w * upscale, h * upscale)
    img_size = (img_size[0] * 2, img_size[1] * 2)

    display.record_output(output_dir=str(output_dir), img_size=img_size)
    display.start()

