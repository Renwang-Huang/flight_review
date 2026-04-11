""" methods to generate various tables used in configured_plots.py """

from html import escape
from math import sqrt
import datetime

import numpy as np

from bokeh.layouts import column
from bokeh.models import ColumnDataSource
from bokeh.models.widgets import DataTable, TableColumn, Div, HTMLTemplateFormatter

from config import plot_color_red
from helper import (
    get_default_parameters, get_airframe_name,
    get_total_flight_time, error_labels_table
    )
from events import get_logged_events

#pylint: disable=consider-using-enumerate,too-many-statements


def _get_vtol_means_per_mode(vtol_states, timestamps, data):
    """
    get the mean values separated by MC and FW mode for some
    data vector
    :return: tuple of (mean mc, mean fw)
    """
    vtol_state_index = 0
    current_vtol_state = -1
    sum_mc = 0
    counter_mc = 0
    sum_fw = 0
    counter_fw = 0
    for i in range(len(timestamps)):
        if timestamps[i] > vtol_states[vtol_state_index][0]:
            current_vtol_state = vtol_states[vtol_state_index][1]
            vtol_state_index += 1
        if current_vtol_state == 2: # FW
            sum_fw += data[i]
            counter_fw += 1
        elif current_vtol_state == 3: # MC
            sum_mc += data[i]
            counter_mc += 1
    mean_mc = None
    if counter_mc > 0: mean_mc = sum_mc / counter_mc
    mean_fw = None
    if counter_fw > 0: mean_fw = sum_fw / counter_fw
    return (mean_mc, mean_fw)


def get_heading_html(ulog, px4_ulog, db_data, link_to_3d_page,
                     additional_links=None, title_suffix=''):
    """
    Get the html (as string) for the heading information (plots title)
    :param additional_links: list of (label, link) tuples
    """
    sys_name = ''
    if 'sys_name' in ulog.msg_info_dict:
        sys_name = escape(ulog.msg_info_dict['sys_name']) + ' '

    if link_to_3d_page is not None and \
        any(elem.name == 'vehicle_gps_position' for elem in ulog.data_list):
        link_to_3d = ("<a class='btn btn-outline-primary' href='"+
                      link_to_3d_page+"'>Open 3D View</a>")
    else:
        link_to_3d = ''

    added_links = ''
    if additional_links is not None:
        for label, link in additional_links:
            added_links += ("<a class='btn btn-outline-primary' href='"+
                            link+"'>"+label+"</a>")

    if title_suffix != '': title_suffix = ' - ' + title_suffix

    title_html = ("<table width='100%'><tr><td><h3>"+sys_name + px4_ulog.get_mav_type()+
                  title_suffix+"</h3></td><td align='right'>" + link_to_3d +
                  added_links+"</td></tr></table>")
    if db_data.description != '':
        title_html += "<h5>"+db_data.description+"</h5>"
    return title_html

from html import escape

def get_info_table_html(ulog, px4_ulog, db_data, vehicle_data, vtol_states):
    
    def format_duration(seconds, verbose=False):
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if not verbose:
            return f"{h:d}:{m:02d}:{s:02d}"
        
        days, h = divmod(h, 24)
        parts = []
        if days > 0: parts.append(f'{days} days')
        if h > 0: parts.append(f'{h} hours')
        if m > 0: parts.append(f'{m} minutes')
        parts.append(f'{s} seconds')
        return ' '.join(parts)

    msg_info = ulog.msg_info_dict
    table_data = []

    airframe_tuple = get_airframe_name(ulog, True)
    if airframe_tuple:
        name, aid = airframe_tuple
        val = aid if not name else f"{name} <small>({aid})</small>"
        table_data.append(('Airframe', val))

    sys_hw = escape(msg_info.get('ver_hw', ''))
    if sys_hw:
        sub_type = msg_info.get('ver_hw_subtype')
        if sub_type:
            sys_hw += f" ({escape(sub_type)})"
        table_data.append(('Hardware', sys_hw))

    sw_ver_git = msg_info.get('ver_sw', '')
    if sw_ver_git:
        release_str = ulog.get_version_info_str() or ''
        branch = msg_info.get('ver_sw_branch', '')
        branch_info = f"<br> branch: {branch}" if branch else ""
        ver_link = f"https://github.com/PX4/Firmware/commit/{sw_ver_git}"
        sw_val = f"{release_str} <small>(<a href='{ver_link}' target='_blank'>{sw_ver_git[:8]}</a>)</small>{branch_info}"
        table_data.append(('Software Version', sw_val))

    os_name = msg_info.get('sys_os_name')
    if os_name:
        os_ver = ulog.get_version_info_str('sys_os_ver_release')
        table_data.append(('OS Version', f"{escape(os_name)}{', ' + os_ver if os_ver else ''}"))

    table_data.append(('Estimator', px4_ulog.get_estimator()))
    table_data.append(('SEP', '---')) 

    duration_s = (ulog.last_timestamp - ulog.start_timestamp) / 1e6
    table_data.append(('Logging Duration', format_duration(duration_s)))

    if ulog.dropouts:
        total_drop_ms = sum(d.duration for d in ulog.dropouts) / 1000
        drop_fmt = f"{total_drop_ms:.0f}" if total_drop_ms > 5 else f"{total_drop_ms:.2f}"
        table_data.append(('Dropouts', f"{len(ulog.dropouts)} ({drop_fmt} s)"))
    else:
        table_data.append(('Dropouts', 'None'))

    flight_time_s = get_total_flight_time(ulog)
    if flight_time_s is not None:
        table_data.append(('Vehicle Life<br/>Flight Time', format_duration(flight_time_s, verbose=True)))

    table_data.append(('SEP', '---'))

    if 'sys_uuid' in msg_info and sys_hw not in ['SITL', 'PX4_SITL']:
        uuid_val = escape(msg_info['sys_uuid'])
        if vehicle_data and vehicle_data.name:
            uuid_val += f" ({vehicle_data.name})"
        table_data.append(('Vehicle UUID', uuid_val))

    def render_table(data_list):
        html_rows = []
        is_padding_next = False
        
        for label, value in data_list:
            if label == 'SEP':
                is_padding_next = True
                continue
            
            style = ' style="padding-top: 0.8em;"' if is_padding_next else ''
            row = (f'<tr><td{style} class="left"><strong>{label}:</strong></td>'
                   f'<td{style}>{value}</td></tr>')
            html_rows.append(row)
            is_padding_next = False
            
        return f'<table style="width:100%; border-collapse:collapse;">{"".join(html_rows)}</table>'

    return f'<div class="info-table-wrapper">{render_table(table_data)}</div>'

def get_error_labels_html():
    """
    Get the html (as string) for user-selectable error labels
    """
    error_label_select = \
        '<select id="error-label" class="chosen-select" multiple="True" '\
        'style="display: none; " tabindex="-1" ' \
        'data-bs-placeholder="Add a detected error..." " >'
    for err_id, err_label in error_labels_table.items():
        error_label_select += '<option data-bs-id="{:d}">{:s}</option>'.format(err_id, err_label)
    error_label_select = '<p>' + error_label_select + '</select></p>'

    return error_label_select

def get_corrupt_log_html(ulog):
    """
    Get the html (as string) for corrupt logs,
    if the log is corrupt, otherwise returns None
    """
    if ulog.file_corruption:
        corrupt_log_html = """
<div class="card text-white bg-danger mb-3">
  <div class="card-header">Warning</div>
  <div class="card-body">
    <h4 class="card-title">Corrupt Log File</h4>
    <p class="card-text">
        This log contains corrupt data. Some of the shown data might be wrong
        and some data might be missing.
        <br />
        A possible cause is a corrupt file system and exchanging or reformatting
        the SD card fixes the problem.
        </p>
  </div>
</div>
"""
        return corrupt_log_html
    return None

def get_hardfault_html(ulog):
    """
    Get the html (as string) for hardfault information,
    if the log contains any, otherwise returns None
    """
    if 'hardfault_plain' in ulog.msg_info_multiple_dict:

        hardfault_html = """
<div class="card text-white bg-danger mb-3">
  <div class="card-header">Warning</div>
  <div class="card-body">
    <h4 class="card-title">Software Crash</h4>
    <p class="card-text">
        This log contains hardfault data from a software crash
        (see <a style="color:#fff; text-decoration: underline;"
        href="https://docs.px4.io/main/en/debug/gdb_hardfault.html#hard-fault-debugging">
        here</a> how to debug).
        <br/>
        The hardfault data is shown below.
        </p>
  </div>
</div>
"""

        counter = 1
        for hardfault in ulog.msg_info_multiple_dict['hardfault_plain']:
            hardfault_text = escape(''.join(hardfault)).replace('\n', '<br/>')
            hardfault_html += ('<p>Hardfault #'+str(counter)+':<br/><pre>'+
                               hardfault_text+'</pre></p>')
            counter += 1
        return hardfault_html
    return None

def get_changed_parameters(ulog, plot_width):
    """
    get a bokeh column object with a table of the changed parameters
    :param initial_parameters: ulog.initial_parameters
    """
    param_names = []
    param_values = []
    param_defaults = []
    param_mins = []
    param_maxs = []
    param_descriptions = []
    param_colors = []
    default_params = get_default_parameters()
    initial_parameters = ulog.initial_parameters
    system_defaults = None
    airframe_defaults = None
    if ulog.has_default_parameters:
        system_defaults = ulog.get_default_parameters(0)
        airframe_defaults = ulog.get_default_parameters(1)

    for param_name in sorted(initial_parameters):
        param_value = initial_parameters[param_name]

        if param_name.startswith('RC') or param_name.startswith('CAL_'):
            continue

        system_default = None
        airframe_default = None
        is_airframe_default = True
        if system_defaults is not None:
            system_default = system_defaults.get(param_name, param_value)
        if airframe_defaults is not None:
            airframe_default = airframe_defaults.get(param_name, param_value)
            is_airframe_default = abs(float(airframe_default) - float(param_value)) < 0.00001

        try:
            if param_name in default_params:
                default_param = default_params[param_name]
                if system_default is None:
                    system_default = default_param['default']
                    airframe_default = default_param['default']
                if default_param['type'] == 'FLOAT':
                    is_default = abs(float(system_default) - float(param_value)) < 0.00001
                    if 'decimal' in default_param:
                        param_value = round(param_value, int(default_param['decimal']))
                        airframe_default = round(float(airframe_default), int(default_param['decimal'])) #pylint: disable=line-too-long
                else:
                    is_default = int(system_default) == int(param_value)
                if not is_default:
                    param_names.append(param_name)
                    param_values.append(param_value)
                    param_defaults.append(airframe_default)
                    param_mins.append(default_param.get('min', ''))
                    param_maxs.append(default_param.get('max', ''))
                    param_descriptions.append(default_param.get('short_desc', ''))
                    param_colors.append('black' if is_airframe_default else plot_color_red)
            else:
                # not found: add it as if it were changed
                param_names.append(param_name)
                param_values.append(param_value)
                param_defaults.append(airframe_default if airframe_default else '')
                param_mins.append('')
                param_maxs.append('')
                param_descriptions.append('(unknown)')
                param_colors.append('black' if is_airframe_default else plot_color_red)
        except Exception as error:
            print(type(error), error)
    param_data = {
        'names': param_names,
        'values': param_values,
        'defaults': param_defaults,
        'mins': param_mins,
        'maxs': param_maxs,
        'descriptions': param_descriptions,
        'colors': param_colors
        }
    source = ColumnDataSource(param_data)
    formatter = HTMLTemplateFormatter(template='<font color="<%= colors %>"><%= value %></font>')
    columns = [
        TableColumn(field="names", title="Name",
                    width=int(plot_width*0.2), sortable=False),
        TableColumn(field="values", title="Value",
                    width=int(plot_width*0.15), sortable=False, formatter=formatter),
        TableColumn(field="defaults",
                    title="Frame Default" if airframe_defaults else "Default",
                    width=int(plot_width*0.1), sortable=False),
        TableColumn(field="mins", title="Min",
                    width=int(plot_width*0.075), sortable=False),
        TableColumn(field="maxs", title="Max",
                    width=int(plot_width*0.075), sortable=False),
        TableColumn(field="descriptions", title="Description",
                    width=int(plot_width*0.40), sortable=False),
        ]
    data_table = DataTable(source=source, columns=columns, width=plot_width,
                           height=300, sortable=False, selectable=False,
                           autosize_mode='none')
    div = Div(text="""<b>Non-default Parameters</b> (except RC and sensor calibration)""",
              width=int(plot_width/2))
    return column(div, data_table, width=plot_width)


def get_logged_messages(ulog, plot_width):
    """
    get a bokeh column object with a table of the logged text messages and events
    :param ulog: ULog object
    """
    messages = get_logged_events(ulog)

    def time_str(t):
        m1, s1 = divmod(int(t/1e6), 60)
        h1, m1 = divmod(m1, 60)
        return "{:d}:{:02d}:{:02d}".format(h1, m1, s1)

    logged_messages = ulog.logged_messages
    for m in logged_messages:
        # backwards compatibility: a string message with appended tab is output
        # in addition to an event with the same message so we can ignore those
        if m.message[-1] == '\t':
            continue
        messages.append((m.timestamp, m.log_level_str(), m.message))

    messages = sorted(messages, key=lambda m: m[0])

    log_times, log_levels, log_messages = zip(*messages) if len(messages) > 0 else ([],[],[])
    log_times_str = [time_str(t) for t in log_times]
    log_data = {
        'times': log_times_str,
        'levels': log_levels,
        'messages': log_messages
        }
    source = ColumnDataSource(log_data)
    columns = [
        TableColumn(field="times", title="Time",
                    width=int(plot_width*0.15), sortable=False),
        TableColumn(field="levels", title="Level",
                    width=int(plot_width*0.1), sortable=False),
        TableColumn(field="messages", title="Message",
                    width=int(plot_width*0.75), sortable=False),
        ]
    data_table = DataTable(source=source, columns=columns, width=plot_width,
                           height=300, sortable=False, selectable=False,
                           autosize_mode='none')
    div = Div(text="""<b>Logged Messages</b>""", width=int(plot_width/2))
    return column(div, data_table, width=plot_width)
