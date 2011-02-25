"""
QAQC Viewer based on Chaco & Traits
"""

#from enthought.chaco.example_support import COLOR_PALETTE
#from enthought.enable.example_support import DemoFrame, demo_main

# Enthought library imports
from enthought.enable.api import Window, Component, ComponentEditor
from enthought.traits.api import HasTraits, Instance
from enthought.traits.ui.api import Item, Group, View

# Chaco imports
from enthought.chaco.api import Plot,ArrayDataSource, ArrayPlotData, BarPlot, DataRange1D, \
        LabelAxis, LinearMapper, VPlotContainer, PlotAxis, PlotGrid, \
        LinePlot, add_default_grids, PlotLabel
from enthought.chaco.tools.api import PanTool, ZoomTool


from enthought.chaco.scales.api import CalendarScaleSystem
from enthought.chaco.scales_tick_generator import ScalesTickGenerator

from sonde import Sonde
import time
import numpy as np

class BaseViewer(HasTraits):
    main_tab = Instance(Component)

    traits_view = View(Item('main_tab', editor=ComponentEditor),
         width=500, height=500, resizable=True, title="Salinity Plot")
    
    def __init__(self, **kwargs):
        HasTraits.__init__(self, **kwargs)
        self.init_data()

    def init_data(self):
        file_name = '/home/dpothina/work/apps/pysonde/tests/ysi_test_files/BAYT_20070323_CDT_YS1772AA_000.dat'
        sonde = Sonde(file_name)
        sal_ds = np.array([1,2,3,4,5,6,7,8])#sonde.data['seawater_salinity']
        time_ds = sal_ds**2#[time.mktime(date.utctimetuple()) for date in sonde.dates]
        #time_ds = ArrayDataSource(dt)
        #sal_ds = ArrayDataSource(salinity, sort_order="none")
        self.plot_data = ArrayPlotData(sal_ds=sal_ds,
                                  time_ds=time_ds)


    def _main_tab_default(self):
        self.sal_plot = Plot(self.plot_data)
        self.sal_plot.plot(('time_ds', 'sal_ds'), type='line')
        #sal_plot.overlays.append(PlotAxis(sal_plot, orientation='left'))
        #bottom_axis = PlotAxis(sal_plot, orientation="bottom",# mapper=xmapper,
        #                   tick_generator=ScalesTickGenerator(scale=CalendarScaleSystem()))
        #sal_plot.overlays.append(bottom_axis)

        #hgrid, vgrid = add_default_grids(sal_plot)
        #vgrid.tick_generator = bottom_axis.tick_generator
        #sal_plot.tools.append(PanTool(sal_plot, constrain=True,
        #                              constrain_direction="x"))
        #sal_plot.overlays.append(ZoomTool(sal_plot, drag_button="right",
        #                                  always_on=True,
        #                                  tool_mode="range",
        #                                  axis="index",
        #                                  max_zoom_out_factor=10.0,
        #                                  ))

        container = VPlotContainer(bgcolor = "lightblue",
                                   spacing = 40, 
                                   padding = 50,
                                   fill_padding=False)
        container.add(sal_plot)
        #container.add(price_plot)
        #container.overlays.append(PlotLabel("Salinity Plot with Date Axis",
        #                                    component=container,
        #                                    #font="Times New Roman 24"))
        #                                    font="Arial 24"))
        return container

    #def default_traits_view(self):
    #    return View(Group(Item('main_tab', editor=ComponentEditor)),
    #                width=500, height=500, resizable=True, title="Salinity Plot")

#===============================================================================
# Attributes to use for the plot view.
#size=(800,600)
#title="Salinity plot example"


if __name__ == "__main__":
    viewer = BaseViewer()
    viewer.configure_traits()
