"""
Copyright (c) 2019 Lorenz Diener

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

* The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.
* You and any organization you work for may not promote white supremacy, hate
speech and homo- or transphobia - this license is void if you do.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

https://github.com/halcy/blurhash-python

Pure python blurhash decoder with no additional dependencies, for
both de- and encoding.

Very close port of the original Swift implementation by Dag Ågren.
"""

import math


# Alphabet for base 83
alphabet = \
    "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ" + \
    "abcdefghijklmnopqrstuvwxyz#$%*+,-.:;=?@[]^_{|}~"
alphabet_values = dict(zip(alphabet, range(len(alphabet))))


def _base83_encode(value, length):
    """
    Decodes an integer to a base83 string, as used in blurhash.

    Length is how long the resulting string should be. Will complain
    if the specified length is too short.
    """
    if int(value) // (83 ** (length)) != 0:
        raise ValueError("Specified length is too short to " +
                         "encode given value.")

    result = ""
    for i in range(1, length + 1):
        digit = int(value) // (83 ** (length - i)) % 83
        result += alphabet[int(digit)]
    return result


def _srgb_to_linear(value):
    """
    srgb 0-255 integer to linear 0.0-1.0 floating point conversion.
    """
    value = float(value) / 255.0
    if value <= 0.04045:
        return value / 12.92
    return math.pow((value + 0.055) / 1.055, 2.4)


def _sign_pow(value, exp):
    """
    Sign-preserving exponentiation.
    """
    return math.copysign(math.pow(abs(value), exp), value)


def _linear_to_srgb(value):
    """
    linear 0.0-1.0 floating point to srgb 0-255 integer conversion.
    """
    value = max(0.0, min(1.0, value))
    if value <= 0.0031308:
        return int(value * 12.92 * 255 + 0.5)
    return int((1.055 * math.pow(value, 1 / 2.4) - 0.055) * 255 + 0.5)


def blurhash_encode(image, components_x=4, components_y=4, linear=False):
    """
    Calculates the blurhash for an image using the given x and y
     component counts.

    Image should be a 3-dimensional array, with the first dimension
    being y, the second being x, and the third being the three rgb
    components that are assumed to be 0-255 srgb integers
    (incidentally, this is the format you will get from a PIL RGB image).

    You can also pass in already linear data - to do this, set linear
    to True. This is useful if you want to encode a version of your
    image resized to a smaller size (which you should ideally do in
    linear colour).
    """
    if components_x < 1 or components_x > 9 or \
       components_y < 1 or components_y > 9:
        raise ValueError("x and y component counts must be " +
                         "between 1 and 9 inclusive.")
    height = float(len(image))
    width = float(len(image[0]))

    # Convert to linear if neeeded
    image_linear = []
    if linear is False:
        for y in range(int(height)):
            image_linear_line = []
            for x in range(int(width)):
                image_linear_line.append([
                    _srgb_to_linear(image[y][x][0]),
                    _srgb_to_linear(image[y][x][1]),
                    _srgb_to_linear(image[y][x][2])
                ])
            image_linear.append(image_linear_line)
    else:
        image_linear = image

    # Calculate components
    components = []
    max_ac_component = 0.0
    for j in range(components_y):
        for i in range(components_x):
            norm_factor = 1.0 if (i == 0 and j == 0) else 2.0
            component = [0.0, 0.0, 0.0]
            for y in range(int(height)):
                for x in range(int(width)):
                    basis = \
                        norm_factor * \
                        math.cos(math.pi * float(i) * float(x) / width) * \
                        math.cos(math.pi * float(j) * float(y) / height)
                    component[0] += basis * image_linear[y][x][0]
                    component[1] += basis * image_linear[y][x][1]
                    component[2] += basis * image_linear[y][x][2]

            component[0] /= (width * height)
            component[1] /= (width * height)
            component[2] /= (width * height)
            components.append(component)

            if not (i == 0 and j == 0):
                max_ac_component = \
                    max(max_ac_component, abs(component[0]),
                        abs(component[1]), abs(component[2]))

    # Encode components
    dc_value = (_linear_to_srgb(components[0][0]) << 16) + \
        (_linear_to_srgb(components[0][1]) << 8) + \
        _linear_to_srgb(components[0][2])

    quant_max_ac_component = int(max(0, min(82,
                                            math.floor(max_ac_component *
                                                       166 - 0.5))))
    ac_component_norm_factor = float(quant_max_ac_component + 1) / 166.0

    ac_values = []
    for r, g, b in components[1:]:
        r2 = r / ac_component_norm_factor
        g2 = g / ac_component_norm_factor
        b2 = b / ac_component_norm_factor
        r3 = math.floor(_sign_pow(r2, 0.5) * 9.0 + 9.5)
        g3 = math.floor(_sign_pow(g2, 0.5) * 9.0 + 9.5)
        b3 = math.floor(_sign_pow(b2, 0.5) * 9.0 + 9.5)
        ac_values.append(
            int(max(0.0, min(18.0, r3))) * 19 * 19 +
            int(max(0.0, min(18.0, g3))) * 19 +
            int(max(0.0, min(18.0, b3)))
        )

    # Build final blurhash
    blurhash = ""
    blurhash += _base83_encode((components_x - 1) + (components_y - 1) * 9, 1)
    blurhash += _base83_encode(quant_max_ac_component, 1)
    blurhash += _base83_encode(dc_value, 4)
    for ac_value in ac_values:
        blurhash += _base83_encode(ac_value, 2)

    return blurhash
