"""Small checks for the environmental data extractor."""

import unittest

from extract_env import measurements


class MeasurementTests(unittest.TestCase):
    """Check a valid reading and a malformed source row."""

    def test_extracts_co2_and_utc_time(self):
        row = {
            "id": "42", "sensorid": "6012002000869",
            "jsondata": '[{"variable":{"name":"Carbon dioxide","unit":"ppm"},'
                        '"values":[{"time":0,"value":450}]},'
                        '{"variable":{"name":"Temperature","unit":"°C"},'
                        '"values":[{"time":0,"value":22.5}]}]',
        }
        result = list(measurements(row, "Carbon dioxide"))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], {
            "sensor_id": "6012002000869", "timestamp_utc": "1970-01-01T00:00:00+00:00",
            "variable": "Carbon dioxide", "unit": "ppm", "value": 450, "source_row_id": "42",
        })

    def test_bad_json_is_reportable(self):
        row = {"id": "43", "sensorid": "x", "jsondata": "not JSON"}
        with self.assertRaisesRegex(ValueError, "invalid jsondata"):
            list(measurements(row))


if __name__ == "__main__":
    unittest.main()
