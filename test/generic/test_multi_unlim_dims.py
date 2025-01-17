import unittest
import numpy as np
import netCDF4 as nc
from ncagg.config import Config
from ncagg.aggregator import generate_aggregation_list, evaluate_aggregation_list
import os
import tempfile


class TestMultiUnlimDims(unittest.TestCase):
    def setUp(self):
        np.random.seed(
            2
        )  # don't want test results to potentially change based on random
        _, self.filename = tempfile.mkstemp()
        # since files sorted by name with no UDC, prefix tmp file so ordering
        # will be deterministic
        self.inputs = [tempfile.mkstemp(prefix=str(_))[1] for _ in range(3)]
        for i, inp in enumerate(self.inputs):
            with nc.Dataset(inp, "w") as nc_in:  # type: nc.Dataset
                nc_in.createDimension("a", None)
                nc_in.createDimension("b", None)

                nc_in.createVariable("a", np.int32, ("a",))
                nc_in.createVariable("b", str, ("b",))
                nc_in.createVariable("c", np.int32, ("a", "b"))

                # the variable a just [0, 1, 2] * i * 3 such that when aggregated,
                # we can verify that in the dimension "a", the aggregated variable a
                # contains a = 0, 1, 2 ... (3*3)
                nc_in.variables["a"][:] = np.arange(3) + (i * 3)

                # recall i is the ith input file we're creating...
                # then variable b has i elements, being some random selection of "a", "b", and "c"
                # I.e. the first file has only one element, next has two, etc. impl by the [:i+1]
                # the variable c also has i _columns_.
                # for j, b in enumerate(sorted(["a", "b", "c"], key=lambda x: np.random.rand())[:i+1]):

                # actually, since we don't have the flatten with index_by working yet,
                # instead keep in order...
                for j, b in enumerate(["a", "b", "c"][: i + 1]):
                    nc_in.variables["b"][j] = b
                    nc_in.variables["c"][:, j] = np.arange(3) + (i * 3)

    def tearDown(self):
        os.remove(self.filename)
        [os.remove(f) for f in self.inputs]

    def test_default_multi_dim(self):
        config = Config.from_nc(self.inputs[0])
        l = generate_aggregation_list(config, self.inputs)
        evaluate_aggregation_list(config, l, self.filename)
        with nc.Dataset(self.filename) as nc_out:  # type: nc.Dataset
            # this is the default aggregation produced by aggregation
            # along both unlimited dimensions. This isn't really practically
            # useful, but, by our "basic" definition of aggregation along unlitimed
            # dimensions is correct. Need to make sure we get what's expected.

            # [[0 -- -- -- -- --]
            #  [1 -- -- -- -- --]
            #  [2 -- -- -- -- --]
            #  [-- 3 3 -- -- --]
            #  [-- 4 4 -- -- --]
            #  [-- 5 5 -- -- --]
            #  [-- -- -- 6 6 6]
            #  [-- -- -- 7 7 7]
            #  [-- -- -- 8 8 8]]
            c = nc_out.variables["c"][:]
            self.assertEqual(c.shape, (9, 6))
            self.assertEqual(np.sum(c), 90)
            self.assertEqual(np.ma.count_masked(c), 36)

    def test_collapse_second_dim(self):
        config = Config.from_nc(self.inputs[0])
        config.dims["b"].update({"flatten": True, "index_by": "b"})
        l = generate_aggregation_list(config, self.inputs)
        evaluate_aggregation_list(config, l, self.filename)
        with nc.Dataset(self.filename) as nc_out:  # type: nc.Dataset
            # This is the more practically useful method of aggregation,
            # where, for example, the dimension "a" might represent time
            # and dim "b" is maybe satellite, or event, etc. (something that,
            # at any point in time, there could be an arbitrary number of).

            # flatten b dimension, should turn out like:

            # [[0 -- --]
            #  [1 -- --]
            #  [2 -- --]
            #  [3 3 --]
            #  [4 4 --]
            #  [5 5 --]
            #  [6 6 6]
            #  [7 7 7]
            #  [8 8 8]]
            c = nc_out.variables["c"][:]
            self.assertEqual(c.shape, (9, 3))
            self.assertEqual(np.sum(c), 90)
            self.assertEqual(np.ma.count_masked(c), 9)
            for i, a in enumerate(["a", "b", "c"]):
                self.assertEqual(nc_out.variables["b"][i], a)
