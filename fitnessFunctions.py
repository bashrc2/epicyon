__filename__ = "fitnessFunctions.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"

import time


def fitnessPerformance(startTime, fitnessState: {},
                       fitnessId: str, watchPoint: str, debug: bool) -> None:
    """Log a performance watchpoint
    """
    if 'performance' not in fitnessState:
        fitnessState['performance'] = {}
    if fitnessId not in fitnessState['performance']:
        fitnessState['performance'][fitnessId] = {}

    timeDiff = time.time() - startTime

    fitnessState['performance'][fitnessId][watchPoint] = timeDiff
    if 'total' in fitnessState['performance'][fitnessId]:
        fitnessState['performance'][fitnessId]['total'] += timeDiff
        fitnessState['performance'][fitnessId]['ctr'] += 1
        if fitnessState['performance'][fitnessId]['ctr'] >= 1024:
            fitnessState['performance'][fitnessId]['total'] /= 2
            fitnessState['performance'][fitnessId]['ctr'] = \
                int(fitnessState['performance'][fitnessId]['ctr'] / 2)
    else:
        fitnessState['performance'][fitnessId]['total'] = timeDiff
        fitnessState['performance'][fitnessId]['ctr'] = 1

    if debug:
        print('FITNESS: performance/' + fitnessId + '/' +
              watchPoint + '/' +
              str(fitnessState['performance'][fitnessId][watchPoint]))
