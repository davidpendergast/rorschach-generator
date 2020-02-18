
WHITE = 255, 255, 255
LIGHT_GRAY = 170, 170, 170
DARK_GRAY = 85, 85, 85
BLACK = 0, 0, 0
RED = 255, 0, 0
GREEN = 0, 255, 0
PURPLE = 255, 85, 255


def round_to_int256(val):
    val = round(val)
    if val < 0:
        return 0
    elif val > 255:
        return 255
    else:
        return val


def lerp(c1, c2, pcnt):
    r = round_to_int256(c1[0] + pcnt * (c2[0] - c1[0]))
    g = round_to_int256(c1[1] + pcnt * (c2[1] - c1[1]))
    b = round_to_int256(c1[2] + pcnt * (c2[2] - c1[2]))
    return r, g, b

