import unittest
import pkg_resources
import thunor.io
import thunor.dip
from thunor.plots import plot_time_course, plot_dip, plot_dip_params, \
    plot_two_dataset_param_scatter, plot_plate_map
from thunor.helpers import plotly_to_dataframe
import pandas as pd


class TestWithDataset(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.filename = pkg_resources.resource_filename('thunor',
                                                       'testdata/VU001.h5')
        cls.dataset = thunor.io.read_hdf(cls.filename)
        ctrl_dip_data, expt_dip_data = thunor.dip.dip_rates(cls.dataset)

        cls.fit_params = thunor.dip.dip_fit_params(ctrl_dip_data,
                                                   expt_dip_data)

    def test_plot_time_course(self):
        abe_bt20 = self.dataset.filter(drugs=['abemaciclib'],
                                       cell_lines=['BT20'])

        tc = plot_time_course(abe_bt20)
        assert isinstance(plotly_to_dataframe(tc), pd.DataFrame)

    def test_plot_dip(self):
        assert isinstance(plotly_to_dataframe(plot_dip(self.fit_params)),
                          pd.DataFrame)

    def test_plot_dip_params_single_param(self):
        assert isinstance(plotly_to_dataframe(plot_dip_params(
            self.fit_params, fit_param='ic50')),
                          pd.DataFrame)

    def test_plot_two_params(self):
        x = plot_dip_params(
            self.fit_params, fit_param='ic50', fit_param_compare='ec50',
            fit_param_sort='ec25')

        assert isinstance(plotly_to_dataframe(x),
            pd.DataFrame)

    def test_plot_dip_params_aggregation(self):
        assert isinstance(plotly_to_dataframe(plot_dip_params(
            self.fit_params, aggregate_cell_lines={'tag': ['BT20', 'HCC1143']},
            aggregate_drugs={'tag': ['abemaciclib', 'Panobinostat']},
            fit_param='ic50')),
                          pd.DataFrame)

    def test_plot_plate_map(self):
        plate_data = self.dataset.plate('HTS007_149-28A',
                                        include_dip_rates=True)
        res = plot_plate_map(
            plate_data
        )
        assert isinstance(plotly_to_dataframe(res), pd.DataFrame)
