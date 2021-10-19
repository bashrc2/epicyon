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
from webapp_utils import htmlHeaderWithExternalStyle
from webapp_utils import htmlFooter
from utils import getConfigParam
from utils import saveJson


def fitnessPerformance(startTime, fitnessState: {},
                       fitnessId: str, watchPoint: str, debug: bool) -> None:
    """Log a performance watchpoint
    """
    if 'performance' not in fitnessState:
        fitnessState['performance'] = {}
    if fitnessId not in fitnessState['performance']:
        fitnessState['performance'][fitnessId] = {}
    if watchPoint not in fitnessState['performance'][fitnessId]:
        fitnessState['performance'][fitnessId][watchPoint] = {
            "total": float(0),
            "ctr": int(0)
        }

    timeDiff = float(time.time() - startTime)

    fitnessState['performance'][fitnessId][watchPoint]['total'] += timeDiff
    fitnessState['performance'][fitnessId][watchPoint]['ctr'] += 1
    if fitnessState['performance'][fitnessId][watchPoint]['ctr'] >= 1024:
        fitnessState['performance'][fitnessId][watchPoint]['total'] /= 2
        fitnessState['performance'][fitnessId][watchPoint]['ctr'] = \
            int(fitnessState['performance'][fitnessId][watchPoint]['ctr'] / 2)

    if debug:
        ctr = fitnessState['performance'][fitnessId][watchPoint]['ctr']
        total = fitnessState['performance'][fitnessId][watchPoint]['total']
        print('FITNESS: performance/' + fitnessId + '/' +
              watchPoint + '/' + str(total * 1000 / ctr))


def sortedWatchPoints(fitness: {}, fitnessId: str) -> []:
    """Returns a sorted list of watchpoints
    times are in mS
    """
    if not fitness.get('performance'):
        return []
    if not fitness['performance'].get(fitnessId):
        return []
    result = []
    for watchPoint, item in fitness['performance'][fitnessId].items():
        if not item.get('total'):
            continue
        averageTime = item['total'] * 1000 / item['ctr']
        result.append(str(averageTime) + ' ' + watchPoint)
    result.sort(reverse=True)
    return result


def htmlWatchPointsGraph(baseDir: str, fitness: {}, fitnessId: str,
                         maxEntries: int) -> str:
    """Returns the html for a graph of watchpoints
    """
    watchPointsList = sortedWatchPoints(fitness, fitnessId)

    cssFilename = baseDir + '/epicyon-graph.css'
    if os.path.isfile(baseDir + '/graph.css'):
        cssFilename = baseDir + '/graph.css'

    instanceTitle = \
        getConfigParam(baseDir, 'instanceTitle')
    htmlStr = htmlHeaderWithExternalStyle(cssFilename, instanceTitle)
    htmlStr += \
        '<table class="graph">\n' + \
        '<caption>Watchpoints for ' + fitnessId + '</caption>\n' + \
        '<thead>\n' + \
        '  <tr>\n' + \
        '    <th scope="col">Item</th>\n' + \
        '    <th scope="col">Percent</th>\n' + \
        '  </tr>\n' + \
        '</thead><tbody>\n'

    # get the maximum time
    maxAverageTime = float(1)
    if len(watchPointsList) > 0:
        maxAverageTime = float(watchPointsList[0].split(' ')[0])
    for watchPoint in watchPointsList:
        averageTime = float(watchPoint.split(' ')[0])
        if averageTime > maxAverageTime:
            maxAverageTime = averageTime

    ctr = 0
    for watchPoint in watchPointsList:
        name = watchPoint.split(' ')[1]
        averageTime = float(watchPoint.split(' ')[0])
        heightPercent = int(averageTime * 100 / maxAverageTime)
        print('heightPercent: ' + str(averageTime) +
              ' ' + str(heightPercent) + '%')
        timeMS = int(averageTime)
        if timeMS == 0:
            break
        htmlStr += \
            '<tr style="height:' + str(heightPercent) + '%">\n' + \
            '  <th scope="row">' + name + '</th>\n' + \
            '  <td><span>' + str(timeMS) + 'mS</span></td>\n' + \
            '</tr>\n'
        ctr += 1
        if ctr >= maxEntries:
            break

    htmlStr += '</tbody></table>\n' + htmlFooter()
    return htmlStr


def fitnessThread(baseDir: str, fitness: {}):
    """Thread used to save fitness function scores
    """
    fitnessFilename = baseDir + '/accounts/fitness.json'
    while True:
        # every 10 mins
        time.sleep(60 * 10)
        saveJson(fitness, fitnessFilename)
