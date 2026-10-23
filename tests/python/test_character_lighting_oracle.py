"""Synthetic equations with hand-computable results; no game resources."""

import math
import unittest

from tools.qa.character_lighting_oracle import (
    DirectionalLight,
    Spotlight16,
    light_vertex,
    quantize_gs_color,
)


class CharacterLightingTests(unittest.TestCase):
    def evaluate(self, **changes):
        args = dict(
            position=(0, 0, 2),
            normal=(0, 0, 1),
            material_diffuse=(2, 3, 4),
            material_ambient=(5, 6, 7),
            scene_ambient=(0.1, 0.2, 0.3, 120),
            directionals=(),
        )
        args.update(changes)
        return light_vertex(**args)

    def spot(self, **changes):
        args = dict(
            position=(0, 0, 0),
            direction=(0, 0, 1),
            color=(10, 20, 30, 2),
            attenuation=(1, 0, 0.25, 0.25),
        )
        args.update(changes)
        return Spotlight16(**args)

    def assert_color(self, actual, expected):
        for a, b in zip(actual, expected, strict=True):
            self.assertAlmostEqual(a, b, places=12)

    def test_ambient_has_independent_rgb_and_unscaled_alpha(self):
        self.assert_color(self.evaluate(), (0.5, 1.2, 2.1, 120))

    def test_directionals_are_transposed_columns_not_rows_and_do_not_normalize(self):
        lights = (
            DirectionalLight((1, 2, -1), (1, 2, 3, 4)),
            DirectionalLight((-1, 0, 0), (80, 90, 100, 120)),
            DirectionalLight((0, 1, 0), (3, 5, 7, 9)),
        )
        # N=(2,1,1): dot products 3,-2,1; negative light contributes zero.
        self.assert_color(
            self.evaluate(normal=(2, 1, 1), directionals=lights), (12.5, 34.2, 66.1, 141)
        )

    def test_spot_distance_cone_and_lambert_are_multiplied(self):
        # distance attenuation 1/2; cone 1/2; Lambert 1 -> intensity 1/4.
        self.assert_color(self.evaluate(spotlight=self.spot()), (5.5, 16.2, 32.1, 120.5))

    def test_spot_and_directionals_add_before_material_multiplication(self):
        self.assert_color(
            self.evaluate(
                spotlight=self.spot(), directionals=(DirectionalLight((0, 0, 2), (2, 3, 4, 5)),)
            ),
            (13.5, 34.2, 64.1, 130.5),
        )

    def test_spot_direction_is_vertex_minus_light(self):
        self.assert_color(self.evaluate(normal=(0, 0, -1), spotlight=self.spot()), self.evaluate())

    def test_spot_normal_term_has_upper_clamp(self):
        self.assertEqual(
            self.evaluate(normal=(0, 0, 5), spotlight=self.spot()),
            self.evaluate(spotlight=self.spot()),
        )

    def test_spot_distance_is_reciprocal(self):
        self.assert_color(
            self.evaluate(position=(0, 0, 4), spotlight=self.spot()), (3, 8.7, 17.1, 120.25)
        )

    def test_distance_and_cone_clamp_independently(self):
        for coeffs in ((8, 0, 2, 0), (8, -1, 3, -1)):
            with self.subTest(coeffs=coeffs):
                self.assert_color(
                    self.evaluate(spotlight=self.spot(attenuation=coeffs)), (20.5, 61.2, 122.1, 122)
                )
        for coeffs in ((0, -1, 0, -1), (1, 0, 0, -1), (0, -1, 1, 0)):
            with self.subTest(coeffs=coeffs):
                self.assert_color(
                    self.evaluate(spotlight=self.spot(attenuation=coeffs)), self.evaluate()
                )

    def test_cone_uses_unmodified_supplied_direction(self):
        self.assert_color(
            self.evaluate(spotlight=self.spot(direction=(0, 0, 0))), (3, 8.7, 17.1, 120.25)
        )

    def test_translation_of_vertex_and_light_together_preserves_result(self):
        self.assertEqual(
            self.evaluate(position=(10, -3, 22), spotlight=self.spot(position=(10, -3, 20))),
            self.evaluate(spotlight=self.spot()),
        )

    def test_quantize_clamps_then_truncates_without_rounding_or_rgb_rescale(self):
        self.assertEqual(
            quantize_gs_color((-0.5, 12.999, 128.001, 999), (128, 128, 128, 255)), (0, 12, 128, 255)
        )
        self.assertEqual(quantize_gs_color((20, 30, 40, 50), (3.9, 2.2, 1.1, 0)), (3, 2, 1, 0))

    def test_invalid_vectors_are_rejected(self):
        for field in (
            "position",
            "normal",
            "material_diffuse",
            "material_ambient",
            "scene_ambient",
        ):
            size = 4 if field == "scene_ambient" else 3
            for bad in (
                (),
                (0,) * (size + 1),
                (True,) * size,
                ("1",) * size,
                (math.nan,) * size,
                (math.inf,) * size,
                (10**400,) * size,
                None,
            ):
                with self.subTest(field=field, bad=repr(bad)[:60]), self.assertRaises(ValueError):
                    self.evaluate(**{field: bad})

    def test_lights_validate_and_freeze_caller_sequences(self):
        direction = [0, 0, 1]
        light = DirectionalLight(direction, [1, 2, 3, 4])
        direction[2] = 99
        self.assertEqual(light.direction, (0, 0, 1))
        for constructor in (
            lambda: DirectionalLight((0, 1), (1, 2, 3, 4)),
            lambda: self.spot(attenuation=(1, 2, 3)),
            lambda: self.spot(color=(1, 2, 3, math.inf)),
        ):
            with self.assertRaises(ValueError):
                constructor()

    def test_unsupported_light_profiles_are_rejected(self):
        for changes in (
            dict(directionals=(DirectionalLight((0, 0, 1), (1, 1, 1, 1)),) * 4),
            dict(directionals=(None,)),
            dict(directionals=None),
            dict(spotlight=object()),
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.evaluate(**changes)

    def test_singular_distance_is_not_silently_assigned_a_fallback(self):
        with self.assertRaises(ValueError):
            self.evaluate(position=(0, 0, 0), spotlight=self.spot())

    def test_overflow_is_rejected(self):
        for changes in (
            dict(
                normal=(1e308, 0, 0), directionals=(DirectionalLight((1e308, 0, 0), (1, 1, 1, 1)),)
            ),
            dict(material_ambient=(1e308, 1, 1), scene_ambient=(1e308, 1, 1, 1)),
            dict(position=(1e308, 0, 0), spotlight=self.spot(position=(-1e308, 0, 0))),
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.evaluate(**changes)

    def test_invalid_quantization_inputs(self):
        for limit in ((-1, 1, 1, 1), (1, 1, 1, 256), (1, 1), (1, 1, 1, math.inf)):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                quantize_gs_color((1, 1, 1, 1), limit)
        with self.assertRaises(ValueError):
            quantize_gs_color((1, math.nan, 1, 1), (128, 128, 128, 255))


if __name__ == "__main__":
    unittest.main()
