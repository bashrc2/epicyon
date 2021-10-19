__filename__ = "fitnessFunctions.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"

import time
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


def fitnessThread(baseDir: str, fitness: {}):
    """Thread used to save fitness function scores
    """
    fitnessFilename = baseDir + '/accounts/fitness.json'
    while True:
        # every 10 mins
        time.sleep(60 * 10)
        saveJson(fitness, fitnessFilename)
