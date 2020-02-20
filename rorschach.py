import sim
import blobs
import pipeline
import inkblot
import visualizer


def get_blob_sim(w, h, cooling_time):
    res = blobs.BlobSimulator(w, h, intial_spawn_rate=0.8)

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
    ink_height = 1.5
    upscale = 3
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
        x_offs = size[0] // 5
        mid_x = size[0] // 2
        mid_y = size[1] // 2

        xfer_func_left = get_rect_mapping_function((mid_x + x_offs, mid_y - size[0] // 2),
                                                   (mid_x + x_offs - size[1], mid_y + size[0] // 2),
                                                   (0, 0), blob_sim.get_size())
        xfer_layer_to_layer(blob_layer, ink_layer,
                            l2_xy_to_l1_xy_func=xfer_func_left,
                            value_xform=lambda blob_val, ink_val: ink_val + (ink_height if blob_val > 0 else 0))

        xfer_func_right = get_rect_mapping_function((mid_x - x_offs, mid_y - size[0] // 2),
                                                    (mid_x - x_offs + size[1], mid_y + size[0] // 2),
                                                    (0, 0), blob_sim.get_size())
        xfer_layer_to_layer(blob_layer, ink_layer,
                            l2_xy_to_l1_xy_func=xfer_func_right,
                            value_xform=lambda blob_val, ink_val: ink_val + (ink_height if blob_val > 0 else 0))

    res.max_static_pressure = 0.45
    res.boundary_pressure = 1.2
    res.max_val_for_render = 1.33
    res.set_parallel(False)

    return res


def get_rect_mapping_function(r1_x1y1, r1_x2y2, r2_x1y1, r2_x2y2):
    print("mapping rect of size={} to {}".format((r1_x2y2[0] - r1_x1y1[0], r1_x2y2[1] - r1_x1y1[1]),
                                                 (r2_x2y2[0] - r2_x1y1[0], r2_x2y2[1] - r2_x1y1[1])))
    def _map_it(r1_xy):
        x, y = r1_xy
        x_t = (x - r1_x1y1[0]) / (r1_x2y2[0] - r1_x1y1[0])
        y_t = (y - r1_x1y1[1]) / (r1_x2y2[1] - r1_x1y1[1])

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


def get_pipeline():
    w = 60
    h = int(w / (640 / 480))

    blob_cooling_time = 100
    blob_sim_time = int(blob_cooling_time * 0.75)

    pipe = pipeline.SimulationPipeline(get_blob_sim(w, h, blob_cooling_time), n_steps=blob_sim_time)

    pipe.add_simulation(get_blob_to_inkblot_mapper)

    return pipe


if __name__ == "__main__":
    display = visualizer.SimulationDisplay(get_pipeline, name="Rorshach")
    display.start()

