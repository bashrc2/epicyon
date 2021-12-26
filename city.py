__filename__ = "city.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Metadata"

import os
import datetime
import random
import math
from random import randint
from utils import acct_dir

# states which the simulated city dweller can be in
PERSON_SLEEP = 0
PERSON_WORK = 1
PERSON_PLAY = 2
PERSON_SHOP = 3
PERSON_EVENING = 4
PERSON_PARTY = 5


def _getDecoyCamera(decoySeed: int) -> (str, str, int):
    """Returns a decoy camera make and model which took the photo
    """
    cameras = [
        ["Apple", "iPhone SE"],
        ["Apple", "iPhone XR"],
        ["Apple", "iPhone 6"],
        ["Apple", "iPhone 7"],
        ["Apple", "iPhone 8"],
        ["Apple", "iPhone 11"],
        ["Apple", "iPhone 11 Pro"],
        ["Apple", "iPhone 12"],
        ["Apple", "iPhone 12 Mini"],
        ["Apple", "iPhone 12 Pro Max"],
        ["Apple", "iPhone 13"],
        ["Apple", "iPhone 13 Mini"],
        ["Apple", "iPhone 13 Pro"],
        ["Samsung", "Galaxy Note 20 Ultra"],
        ["Samsung", "Galaxy S20 Plus"],
        ["Samsung", "Galaxy S20 FE 5G"],
        ["Samsung", "Galaxy Z FOLD 2"],
        ["Samsung", "Galaxy S12 Plus"],
        ["Samsung", "Galaxy S12"],
        ["Samsung", "Galaxy S11 Plus"],
        ["Samsung", "Galaxy S10 Plus"],
        ["Samsung", "Galaxy S10e"],
        ["Samsung", "Galaxy Z Flip"],
        ["Samsung", "Galaxy A51"],
        ["Samsung", "Galaxy S10"],
        ["Samsung", "Galaxy S10 Plus"],
        ["Samsung", "Galaxy S10e"],
        ["Samsung", "Galaxy S10 5G"],
        ["Samsung", "Galaxy A60"],
        ["Samsung", "Note 12"],
        ["Samsung", "Note 12 Plus"],
        ["Samsung", "Note 11"],
        ["Samsung", "Note 11 Plus"],
        ["Samsung", "Note 10"],
        ["Samsung", "Note 10 Plus"],
        ["Samsung", "Galaxy S22 Ultra"],
        ["Samsung", "Galaxy S21 Ultra"],
        ["Samsung", "Galaxy Note 20 Ultra"],
        ["Samsung", "Galaxy S21"],
        ["Samsung", "Galaxy S21 Plus"],
        ["Samsung", "Galaxy S20 FE"],
        ["Samsung", "Galaxy Z Fold 2"],
        ["Samsung", "Galaxy A52 5G"],
        ["Samsung", "Galaxy A71 5G"],
        ["Google", "Pixel 6 Pro"],
        ["Google", "Pixel 6"],
        ["Google", "Pixel 5"],
        ["Google", "Pixel 4a"],
        ["Google", "Pixel 4 XL"],
        ["Google", "Pixel 3 XL"],
        ["Google", "Pixel 4"],
        ["Google", "Pixel 4a 5G"],
        ["Google", "Pixel 3"],
        ["Google", "Pixel 3a"]
    ]
    randgen = random.Random(decoySeed)
    index = randgen.randint(0, len(cameras) - 1)
    serialNumber = randgen.randint(100000000000, 999999999999999999999999)
    return cameras[index][0], cameras[index][1], serialNumber


def _getCityPulse(curr_timeOfDay, decoySeed: int) -> (float, float):
    """This simulates expected average patterns of movement in a city.
    Jane or Joe average lives and works in the city, commuting in
    and out of the central district for work. They have a unique
    life pattern, which machine learning can latch onto.
    This returns a polar coordinate for the simulated city dweller:
    Distance from the city centre is in the range 0.0 - 1.0
    Angle is in radians
    """
    randgen = random.Random(decoySeed)
    variance = 3
    busyStates = (PERSON_WORK, PERSON_SHOP, PERSON_PLAY, PERSON_PARTY)
    dataDecoyState = PERSON_SLEEP
    weekday = curr_timeOfDay.weekday()
    minHour = 7 + randint(0, variance)
    maxHour = 17 + randint(0, variance)
    if curr_timeOfDay.hour > minHour:
        if curr_timeOfDay.hour <= maxHour:
            if weekday < 5:
                dataDecoyState = PERSON_WORK
            elif weekday == 5:
                dataDecoyState = PERSON_SHOP
            else:
                dataDecoyState = PERSON_PLAY
        else:
            if weekday < 5:
                dataDecoyState = PERSON_EVENING
            else:
                dataDecoyState = PERSON_PARTY
    randgen2 = random.Random(decoySeed + dataDecoyState)
    angleRadians = \
        (randgen2.randint(0, 100000) / 100000) * 2 * math.pi
    # some people are quite random, others have more predictable habits
    decoyRandomness = randgen.randint(1, 3)
    # occasionally throw in a wildcard to keep the machine learning guessing
    if randint(0, 100) < decoyRandomness:
        distanceFromCityCenter = (randint(0, 100000) / 100000)
        angleRadians = (randint(0, 100000) / 100000) * 2 * math.pi
    else:
        # what consitutes the central district is fuzzy
        centralDistrictFuzz = (randgen.randint(0, 100000) / 100000) * 0.1
        busyRadius = 0.3 + centralDistrictFuzz
        if dataDecoyState in busyStates:
            # if we are busy then we're somewhere in the city center
            distanceFromCityCenter = \
                (randgen.randint(0, 100000) / 100000) * busyRadius
        else:
            # otherwise we're in the burbs
            distanceFromCityCenter = busyRadius + \
                ((1.0 - busyRadius) * (randgen.randint(0, 100000) / 100000))
    return distanceFromCityCenter, angleRadians


def parseNogoString(nogoLine: str) -> []:
    """Parses a line from locations_nogo.txt and returns the polygon
    """
    nogoLine = nogoLine.replace('\n', '').replace('\r', '')
    polygonStr = nogoLine.split(':', 1)[1]
    if ';' in polygonStr:
        pts = polygonStr.split(';')
    else:
        pts = polygonStr.split(',')
    if len(pts) <= 4:
        return []
    polygon = []
    for index in range(int(len(pts)/2)):
        if index*2 + 1 >= len(pts):
            break
        longitudeStr = pts[index*2].strip()
        latitudeStr = pts[index*2 + 1].strip()
        if 'E' in latitudeStr or 'W' in latitudeStr:
            longitudeStr = pts[index*2 + 1].strip()
            latitudeStr = pts[index*2].strip()
        if 'E' in longitudeStr:
            longitudeStr = \
                longitudeStr.replace('E', '')
            longitude = float(longitudeStr)
        elif 'W' in longitudeStr:
            longitudeStr = \
                longitudeStr.replace('W', '')
            longitude = -float(longitudeStr)
        else:
            longitude = float(longitudeStr)
        latitude = float(latitudeStr)
        polygon.append([latitude, longitude])
    return polygon


def spoofGeolocation(base_dir: str,
                     city: str, curr_time, decoySeed: int,
                     citiesList: [],
                     nogoList: []) -> (float, float, str, str,
                                       str, str, int):
    """Given a city and the current time spoofs the location
    for an image
    returns latitude, longitude, N/S, E/W,
    camera make, camera model, camera serial number
    """
    locationsFilename = base_dir + '/custom_locations.txt'
    if not os.path.isfile(locationsFilename):
        locationsFilename = base_dir + '/locations.txt'

    nogoFilename = base_dir + '/custom_locations_nogo.txt'
    if not os.path.isfile(nogoFilename):
        nogoFilename = base_dir + '/locations_nogo.txt'

    manCityRadius = 0.1
    varianceAtLocation = 0.0004
    default_latitude = 51.8744
    default_longitude = 0.368333
    default_latdirection = 'N'
    default_longdirection = 'W'

    if citiesList:
        cities = citiesList
    else:
        if not os.path.isfile(locationsFilename):
            return (default_latitude, default_longitude,
                    default_latdirection, default_longdirection,
                    "", "", 0)
        cities = []
        try:
            with open(locationsFilename, 'r') as f:
                cities = f.readlines()
        except OSError:
            print('EX: unable to read locations ' + locationsFilename)

    nogo = []
    if nogoList:
        nogo = nogoList
    else:
        if os.path.isfile(nogoFilename):
            nogoList = []
            try:
                with open(nogoFilename, 'r') as f:
                    nogoList = f.readlines()
            except OSError:
                print('EX: unable to read ' + nogoFilename)
            for line in nogoList:
                if line.startswith(city + ':'):
                    polygon = parseNogoString(line)
                    if polygon:
                        nogo.append(polygon)

    city = city.lower()
    for cityName in cities:
        if city in cityName.lower():
            cityFields = cityName.split(':')
            latitude = cityFields[1]
            longitude = cityFields[2]
            areaKm2 = 0
            if len(cityFields) > 3:
                areaKm2 = int(cityFields[3])
            latdirection = 'N'
            longdirection = 'E'
            if 'S' in latitude:
                latdirection = 'S'
                latitude = latitude.replace('S', '')
            if 'W' in longitude:
                longdirection = 'W'
                longitude = longitude.replace('W', '')
            latitude = float(latitude)
            longitude = float(longitude)
            # get the time of day at the city
            approxTimeZone = int(longitude / 15.0)
            if longdirection == 'E':
                approxTimeZone = -approxTimeZone
            curr_timeAdjusted = curr_time - \
                datetime.timedelta(hours=approxTimeZone)
            camMake, camModel, camSerialNumber = \
                _getDecoyCamera(decoySeed)
            validCoord = False
            seedOffset = 0
            while not validCoord:
                # patterns of activity change in the city over time
                (distanceFromCityCenter, angleRadians) = \
                    _getCityPulse(curr_timeAdjusted, decoySeed + seedOffset)
                # The city radius value is in longitude and the reference
                # is Manchester. Adjust for the radius of the chosen city.
                if areaKm2 > 1:
                    manRadius = math.sqrt(1276 / math.pi)
                    radius = math.sqrt(areaKm2 / math.pi)
                    cityRadiusDeg = (radius / manRadius) * manCityRadius
                else:
                    cityRadiusDeg = manCityRadius
                # Get the position within the city, with some randomness added
                latitude += \
                    distanceFromCityCenter * cityRadiusDeg * \
                    math.cos(angleRadians)
                longitude += \
                    distanceFromCityCenter * cityRadiusDeg * \
                    math.sin(angleRadians)
                longval = longitude
                if longdirection == 'W':
                    longval = -longitude
                validCoord = not pointInNogo(nogo, latitude, longval)
                if not validCoord:
                    seedOffset += 1
                    if seedOffset > 100:
                        break
            # add a small amount of variance around the location
            fraction = randint(0, 100000) / 100000
            distanceFromLocation = fraction * fraction * varianceAtLocation
            fraction = randint(0, 100000) / 100000
            angleFromLocation = fraction * 2 * math.pi
            latitude += distanceFromLocation * math.cos(angleFromLocation)
            longitude += distanceFromLocation * math.sin(angleFromLocation)

            # gps locations aren't transcendental, so round to a fixed
            # number of decimal places
            latitude = int(latitude * 100000) / 100000.0
            longitude = int(longitude * 100000) / 100000.0
            return (latitude, longitude, latdirection, longdirection,
                    camMake, camModel, camSerialNumber)

    return (default_latitude, default_longitude,
            default_latdirection, default_longdirection,
            "", "", 0)


def getSpoofedCity(city: str, base_dir: str,
                   nickname: str, domain: str) -> str:
    """Returns the name of the city to use as a GPS spoofing location for
    image metadata
    """
    city = ''
    cityFilename = acct_dir(base_dir, nickname, domain) + '/city.txt'
    if os.path.isfile(cityFilename):
        try:
            with open(cityFilename, 'r') as fp:
                city = fp.read().replace('\n', '')
        except OSError:
            print('EX: unable to read ' + cityFilename)
    return city


def _pointInPolygon(poly: [], x: float, y: float) -> bool:
    """Returns true if the given point is inside the given polygon
    """
    n = len(poly)
    inside = False
    p2x = 0.0
    p2y = 0.0
    xints = 0.0
    p1x, p1y = poly[0]
    for i in range(n + 1):
        p2x, p2y = poly[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xints = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xints:
                        inside = not inside
        p1x, p1y = p2x, p2y

    return inside


def pointInNogo(nogo: [], latitude: float, longitude: float) -> bool:
    """Returns true of the given geolocation is within a nogo area
    """
    for polygon in nogo:
        if _pointInPolygon(polygon, latitude, longitude):
            return True
    return False
