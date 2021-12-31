__filename__ = "fitnessFunctions.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"

import os
import time
from webapp_utils import html_header_with_external_style
from webapp_utils import html_footer
from utils import get_config_param
from utils import save_json


def fitness_performance(startTime, fitnessState: {},
                        fitnessId: str, watch_point: str, debug: bool) -> None:
    """Log a performance watchpoint
    """
    if 'performance' not in fitnessState:
        fitnessState['performance'] = {}
    if fitnessId not in fitnessState['performance']:
        fitnessState['performance'][fitnessId] = {}
    if watch_point not in fitnessState['performance'][fitnessId]:
        fitnessState['performance'][fitnessId][watch_point] = {
            "total": float(0),
            "ctr": int(0)
        }

    time_diff = float(time.time() - startTime)

    fitnessState['performance'][fitnessId][watch_point]['total'] += time_diff
    fitnessState['performance'][fitnessId][watch_point]['ctr'] += 1
    if fitnessState['performance'][fitnessId][watch_point]['ctr'] >= 1024:
        fitnessState['performance'][fitnessId][watch_point]['total'] /= 2
        fitnessState['performance'][fitnessId][watch_point]['ctr'] = \
            int(fitnessState['performance'][fitnessId][watch_point]['ctr'] / 2)

    if debug:
        ctr = fitnessState['performance'][fitnessId][watch_point]['ctr']
        total = fitnessState['performance'][fitnessId][watch_point]['total']
        print('FITNESS: performance/' + fitnessId + '/' +
              watch_point + '/' + str(total * 1000 / ctr))


def sorted_watch_points(fitness: {}, fitnessId: str) -> []:
    """Returns a sorted list of watchpoints
    times are in mS
    """
    if not fitness.get('performance'):
        return []
    if not fitness['performance'].get(fitnessId):
        return []
    result = []
    for watch_point, item in fitness['performance'][fitnessId].items():
        if not item.get('total'):
            continue
        average_time = item['total'] * 1000 / item['ctr']
        average_time_str = str(average_time).zfill(8)
        result.append(average_time_str + ' ' + watch_point)
    result.sort(reverse=True)
    return result


def html_watch_points_graph(base_dir: str, fitness: {}, fitnessId: str,
                            maxEntries: int) -> str:
    """Returns the html for a graph of watchpoints
    """
    watch_points_list = sorted_watch_points(fitness, fitnessId)

    css_filename = base_dir + '/epicyon-graph.css'
    if os.path.isfile(base_dir + '/graph.css'):
        css_filename = base_dir + '/graph.css'

    instance_title = \
        get_config_param(base_dir, 'instanceTitle')
    html_str = \
        html_header_with_external_style(css_filename, instance_title, None)
    html_str += \
        '<table class="graph">\n' + \
        '<caption>Watchpoints for ' + fitnessId + '</caption>\n' + \
        '<thead>\n' + \
        '  <tr>\n' + \
        '    <th scope="col">Item</th>\n' + \
        '    <th scope="col">Percent</th>\n' + \
        '  </tr>\n' + \
        '</thead><tbody>\n'

    # get the maximum time
    max_average_time = float(1)
    if len(watch_points_list) > 0:
        max_average_time = float(watch_points_list[0].split(' ')[0])
    for watch_point in watch_points_list:
        average_time = float(watch_point.split(' ')[0])
        if average_time > max_average_time:
            max_average_time = average_time

    ctr = 0
    for watch_point in watch_points_list:
        name = watch_point.split(' ', 1)[1]
        average_time = float(watch_point.split(' ')[0])
        heightPercent = int(average_time * 100 / max_average_time)
        timeMS = int(average_time)
        if heightPercent == 0:
            continue
        html_str += \
            '<tr style="height:' + str(heightPercent) + '%">\n' + \
            '  <th scope="row">' + name + '</th>\n' + \
            '  <td><span>' + str(timeMS) + '</span></td>\n' + \
            '</tr>\n'
        ctr += 1
        if ctr >= maxEntries:
            break

    html_str += '</tbody></table>\n' + html_footer()
    return html_str


def fitness_thread(base_dir: str, fitness: {}):
    """Thread used to save fitness function scores
    """
    fitness_filename = base_dir + '/accounts/fitness.json'
    while True:
        # every 10 mins
        time.sleep(60 * 10)
        save_json(fitness, fitness_filename)
