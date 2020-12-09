from nlcontrol.visualisation.file_management import __write_to_browser__
from nlcontrol.visualisation.drawing_tools import draw_line, generate_system_renderer_info, generate_parallel_renderer_info, generate_renderer_sources, generate_connection_coordinates, generate_series_renderer_info
from nlcontrol.visualisation.utils import pretty_print_dict

from bokeh.io import show, output_file, curdoc
from bokeh.resources import CDN
from bokeh.embed import file_html
from bokeh.models import (Arrow, ColumnDataSource, Ellipse, HoverTool, MultiLine, NormalHead, PanTool, Plot, Range1d, Rect, Text)

import uuid

FONT_SIZE_IN_PIXELS = 15
x_offset, y_offset = 0, 0

class RendererBase(object):
    def __init__(self, system_obj, **kwargs):
        print('RendererBase: init called')
        self.plot = None
        self.plot_dict = dict()
        self.system_obj = system_obj
        self.renderer_info = None

    def show(self, open_browser=True):
        print("Showing the system {} with name '{}'".format(type(self.system_obj), self.system_obj.name))
        self.set_coordinates()
        
        source_systems, source_sum, source_commons = generate_renderer_sources(self.renderer_info)
        # pretty_print_dict(self.renderer_info)

        x_polynomials, y_polynomials, output_lines = generate_connection_coordinates(self.renderer_info)

        glyph_system_text = Text(x="x", y="y", text="text", text_font_size="{}px".format(FONT_SIZE_IN_PIXELS), text_color="#000000", text_baseline="middle", text_align="center")
        glyph_system_box = Rect(x="x", y="y", width="width", height="height", fill_color="#cab2d6", fill_alpha=0.4)
        glyph_sum_text = Text(x="x", y="y", text="text", text_font_size="{}px".format(FONT_SIZE_IN_PIXELS), text_color="#000000", text_baseline="middle", text_align="center")
        glyph_sum_box = Ellipse(x="x", y="y", width="diameter", height="diameter", fill_color="#cab2d6", fill_alpha=0.4)
        glyph_commons = Ellipse(x="x", y="y", width="width", height="width", fill_color="#000000")

        # Create plot
        self.plot = Plot(
            min_height=500,
            width_policy='max',
            height_policy='max', 
            match_aspect=True)
        
        # Add block glyphs to plot
        glyph_system_box_renderer = self.plot.add_glyph(source_systems, glyph_system_box)
        glyph_sum_box_renderer = self.plot.add_glyph(source_sum, glyph_sum_box)
        glyph_system_text_renderer = self.plot.add_glyph(source_systems, glyph_system_text)
        glyph_sum_text_renderer = self.plot.add_glyph(source_sum, glyph_sum_text)
        glyph_commons_renderer = self.plot.add_glyph(source_commons, glyph_commons)

        # Add arrows
        for x_poly, y_poly in zip(x_polynomials, y_polynomials):
            glyph_arrow = Arrow(end=NormalHead(size=15, fill_color="#000000"),
                                x_start=x_poly[-2],
                                y_start=y_poly[-2],
                                x_end=x_poly[-1],
                                y_end=y_poly[-1],
                                line_width=0,
                                line_color = "#000000")
            self.plot.add_layout(glyph_arrow)

        # Add lines
        source_lines = ColumnDataSource(dict(xs=x_polynomials, ys=y_polynomials, output=output_lines))
        glyph_lines = MultiLine(xs="xs", ys="ys", line_color="#000000", line_width=3)
        glyph_lines_renderer = self.plot.add_glyph(source_lines, glyph_lines)

        # Tools
        node_hover_tool = HoverTool(
            line_policy="nearest", 
            tooltips="""
            <div>
                <div>
                    <b>Class Name:</b>
                    <i>@classname </i>
                </div>
                <div>
                    <b>States:</b>
                    <i>@states</i>
                </div>
                <div>
                    <b>Outputs:</b>
                    <i>@output</i>
                </div>
            </div>
                """,
            renderers=[glyph_system_box_renderer])

        # Should work from Bokeh 2.3.x
        sum_hover_tool = HoverTool(
            line_policy="nearest", 
            tooltips="""
                <div>
                    <div>
                        <b>Output:</b>
                        <i>@output </i>
                    </div>
                </div>
                    """,
            renderers=[glyph_sum_box_renderer, glyph_lines_renderer]
        )
        self.plot.add_tools(PanTool(), node_hover_tool, sum_hover_tool)

        if open_browser:
            html = file_html(self.plot, CDN, "my plot")
            __write_to_browser__(html)
        

class SystemRenderer(RendererBase):
    def __init__(self, system_obj, **kwargs):
        print('SystemRenderer: init called')
        super().__init__(system_obj, **kwargs)
        self.renderer_info = self.__init_renderer_info__(**kwargs)

    def __init_renderer_info__(self, block_type="system", **kwargs):
        print('SystemRenderer : renderer_info')
        unique_id = uuid.uuid4().hex
        info = {unique_id : dict()}
        info_id = info[unique_id]
        if 'block_type' in kwargs:
            block_type = kwargs['block_type']
        # print(block_type)

        if block_type == "system":
            info_dict = generate_system_renderer_info(self.system_obj)
        elif block_type == "parallel":
            if 'systems' not in kwargs:
                error_text = "[RendererBase] In the case of a 'parallel' block_type a keyword argument 'systems' should be supplied."
                raise AttributeError(error_text)
            info_dict = generate_parallel_renderer_info(self.system_obj, kwargs['systems'])
        elif block_type == "series":
            if 'systems' not in kwargs:
                error_text = "[RendererBase] In the case of a 'series' block_type a keyword argument 'systems' should be supplied."
                raise AttributeError(error_text)
            info_dict = generate_series_renderer_info(self.system_obj, kwargs['systems'])
        info_id.update(info_dict)
        return info

    
    def set_coordinates(self, current_element=None):
        if current_element is None:
            current_element = self.renderer_info
        for current_id in current_element.keys():
            current_data = current_element[current_id]
            current_data['position'] = current_data['rel_position'](current_data['x_offset'], current_data['y_offset'])
            if 'nodes' in current_data:
                self.set_coordinates(current_element=current_data['nodes'])
        # print(self.renderer_info)

class ParallelRenderer(RendererBase):
    def __init__(self, system_obj, **kwargs):
        print('ParallelRenderer: init called')
        super().__init__(system_obj, **kwargs)
        self.renderer_info = self.__init_renderer_info__(**kwargs)

    def __init_renderer_info__(self, block_type="parallel", **kwargs):
        print('ParallelRenderer : renderer_info')

class SeriesRenderer(RendererBase):
    def __init__(self, system_obj, **kwargs):
        super().__init__(system_obj, **kwargs)
        self.renderer_info = self.__init_renderer_info__(**kwargs)

    def __init_renderer_info__(self, block_type="series", **kwargs):
        print(SeriesRenderer: renderer_info)
        
