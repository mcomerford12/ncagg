import unittest
import netCDF4 as nc
import numpy as np
import tempfile
from ncagg.config import Config
from ncagg.aggregator import generate_aggregation_list, evaluate_aggregation_list
from datetime import datetime
import glob
import os
import json


class TestEvaluateAggregationList(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super(TestEvaluateAggregationList, cls).setUpClass()
        pwd = os.path.dirname(__file__)
        cls.start_time = datetime(2017, 6, 8, 16, 45)
        cls.end_time = datetime(2017, 6, 8, 16, 50)
        cls.files = glob.glob(os.path.join(pwd, "data", "*.nc"))
        with open(os.path.join(pwd, "seis-l1b-sgps-east.json")) as product_config_file:
            cls.config = Config.from_dict(json.load(product_config_file))
        cls.config.dims["report_number"].update(
            {
                "index_by": "L1a_SciData_TimeStamp",
                "min": cls.start_time,  # for convenience, will convert according to index_by units if this is datetime
                "max": cls.end_time,
                "expected_cadence": {"report_number": 1, "sensor_unit": 0},
            }
        )
        _, cls.filename = tempfile.mkstemp()
        agg_list = generate_aggregation_list(cls.config, cls.files)
        evaluate_aggregation_list(cls.config, agg_list, cls.filename)
        cls.output = nc.Dataset(cls.filename, "r")

    @classmethod
    def tearDownClass(cls):
        super(TestEvaluateAggregationList, cls).tearDownClass()
        os.remove(cls.filename)

    """
    This test tests a feature that was added a while ago, but was          
    then removed during a refactoring. The feature in question has         
    not been reimplemented yet. This test is expected to fail for          
    the time being.      
    """

    @unittest.expectedFailure
    def test_time(self):
        """Make sure the time array looks ok. Evenly spaced, bounds are correct."""
        numeric_times = self.output.variables["L1a_SciData_TimeStamp"][:]
        self.assertAlmostEqual(np.mean(np.diff(numeric_times)), 1, delta=0.01)
        self.assertAlmostEqual(np.min(np.diff(numeric_times)), 1, delta=0.01)
        self.assertAlmostEqual(np.max(np.diff(numeric_times)), 1, delta=0.01)

        datetimes = nc.num2date(
            numeric_times, self.output.variables["L1a_SciData_TimeStamp"].units
        )
        self.assertLess(abs((datetimes[0] - self.start_time).total_seconds()), 0.1)
        self.assertLess(abs((datetimes[-1] - self.end_time).total_seconds()), 0.1)
