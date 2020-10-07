__filename__ = "newsdaemon.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import time
from newswire import getDictFromNewswire


def runNewswireDaemon(baseDir: str, httpd, unused: str):
    """Periodically updates RSS feeds
    """
    # initial sleep to allow the system to start up
    time.sleep(50)
    while True:
        # has the session been created yet?
        if not httpd.session:
            print('Newswire daemon waiting for session')
            time.sleep(60)
            continue

        # try to update the feeds
        newNewswire = None
        try:
            newNewswire = getDictFromNewswire(httpd.session, baseDir)
        except Exception as e:
            print('WARN: unable to update newswire ' + str(e))
            time.sleep(120)
            continue

        httpd.newswire = newNewswire
        print('Newswire updated')
        # wait a while before the next feeds update
        time.sleep(1200)


def runNewswireWatchdog(projectVersion: str, httpd) -> None:
    """This tries to keep the newswire update thread running even if it dies
    """
    print('Starting newswire watchdog')
    newswireOriginal = \
        httpd.thrPostSchedule.clone(runNewswireDaemon)
    httpd.thrNewswireDaemon.start()
    while True:
        time.sleep(50)
        if not httpd.thrNewswireDaemon.isAlive():
            httpd.thrNewswireDaemon.kill()
            httpd.thrNewswireDaemon = \
                newswireOriginal.clone(runNewswireDaemon)
            httpd.thrNewswireDaemon.start()
            print('Restarting newswire daemon...')
