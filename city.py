__filename__ = "city.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
import datetime
import random
import math
from random import randint

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
        ["Samsung", "Galaxy Note 20 Ultra"],
        ["Samsung", "Galaxy S20 Plus"],
        ["Samsung", "Galaxy S20 FE 5G"],
        ["Samsung", "Galaxy Z FOLD 2"],
        ["Samsung", "Galaxy S10 Plus"],
        ["Samsung", "Galaxy S10e"],
        ["Samsung", "Galaxy Z Flip"],
        ["Samsung", "Galaxy A51"],
        ["Samsung", "Galaxy S10"],
        ["Samsung", "Galaxy S10 Plus"],
        ["Samsung", "Galaxy S10e"],
        ["Samsung", "Galaxy S10 5G"],
        ["Samsung", "Galaxy A60"],
        ["Samsung", "Note 10"],
        ["Samsung", "Note 10 Plus"],
        ["Samsung", "Galaxy S21 Ultra"],
        ["Samsung", "Galaxy Note 20 Ultra"],
        ["Samsung", "Galaxy S21"],
        ["Samsung", "Galaxy S21 Plus"],
        ["Samsung", "Galaxy S20 FE"],
        ["Samsung", "Galaxy Z Fold 2"],
        ["Samsung", "Galaxy A52 5G"],
        ["Samsung", "Galaxy A71 5G"],
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


def _getCityPulse(currTimeOfDay, decoySeed: int) -> (float, float):
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
    weekday = currTimeOfDay.weekday()
    minHour = 7 + randint(0, variance)
    maxHour = 17 + randint(0, variance)
    if currTimeOfDay.hour > minHour:
        if currTimeOfDay.hour <= maxHour:
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


def spoofGeolocation(baseDir: str,
                     city: str, currTime, decoySeed: int,
                     citiesList: []) -> (float, float, str, str,
                                         str, str, int):
    """Given a city and the current time spoofs the location
    for an image
    returns latitude, longitude, N/S, E/W,
    camera make, camera model, camera serial number
    """
    locationsFilename = baseDir + '/custom_locations.txt'
    if not os.path.isfile(locationsFilename):
        locationsFilename = baseDir + '/locations.txt'
    cityRadius = 0.1
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
        with open(locationsFilename, "r") as f:
            cities = f.readlines()

    city = city.lower()
    for cityName in cities:
        if city in cityName.lower():
            latitude = cityName.split(':')[1]
            longitude = cityName.split(':')[2]
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
            currTimeAdjusted = currTime - \
                datetime.timedelta(hours=approxTimeZone)
            camMake, camModel, camSerialNumber = \
                _getDecoyCamera(decoySeed)
            # patterns of activity change in the city over time
            (distanceFromCityCenter, angleRadians) = \
                _getCityPulse(currTimeAdjusted, decoySeed)
            # Get the position within the city, with some randomness added
            latitude += \
                distanceFromCityCenter * cityRadius * math.cos(angleRadians)
            longitude += \
                distanceFromCityCenter * cityRadius * math.sin(angleRadians)
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
