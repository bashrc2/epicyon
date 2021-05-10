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


def _getCityPulse(currTimeOfDay, decoySeed: int) -> (float, float):
    """The data decoy
    This simulates expected average patterns of movement in a city.
    Jane or Joe average lives and works in the city, commuting in
    and out of the central district for work. They have a unique
    life pattern, which machine learning can latch onto.
    This returns a polar coordinate:
    Distance from the city centre is in the range 0.0 - 1.0
    Angle is in radians
    """
    randgen = random.Random(decoySeed)
    variance = 3
    busyStates = ("work", "shop", "play", "party")
    dataDecoyState = "sleep"
    dataDecoyIndex = 0
    weekday = currTimeOfDay.weekday()
    minHour = 7 + randint(0, variance)
    maxHour = 17 + randint(0, variance)
    if currTimeOfDay.hour > minHour:
        if currTimeOfDay.hour <= maxHour:
            if weekday < 5:
                dataDecoyState = "work"
                dataDecoyIndex = 1
            elif weekday == 5:
                dataDecoyState = "shop"
                dataDecoyIndex = 2
            else:
                dataDecoyState = "play"
                dataDecoyIndex = 3
        else:
            if weekday < 5:
                dataDecoyState = "evening"
                dataDecoyIndex = 4
            else:
                dataDecoyState = "party"
                dataDecoyIndex = 5
    randgen2 = random.Random(decoySeed + dataDecoyIndex)
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
                     citiesList: []) -> (float, float, str, str):
    """Given a city and the current time spoofs the location
    for an image
    returns latitude, longitude, N/S, E/W
    """
    locationsFilename = baseDir + '/custom_locations.txt'
    if not os.path.isfile(locationsFilename):
        locationsFilename = baseDir + '/locations.txt'
    cityRadius = 0.1
    variance = 0.001
    default_latitude = 51.8744
    default_longitude = 0.368333
    default_latdirection = 'N'
    default_longdirection = 'W'

    if citiesList:
        cities = citiesList
    else:
        if not os.path.isfile(locationsFilename):
            return (default_latitude, default_longitude,
                    default_latdirection, default_longdirection)
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
            # patterns of activity change in the city over time
            (distanceFromCityCenter, angleRadians) = \
                _getCityPulse(currTimeAdjusted, decoySeed)
            # Get the position within the city, with some randomness added
            latitude += \
                distanceFromCityCenter * cityRadius * math.cos(angleRadians)
            # add a small amount of variance around the location
            fraction = randint(0, 100000) / 100000
            latitude += (fraction * fraction * variance) - (variance / 2.0)

            longitude += \
                distanceFromCityCenter * cityRadius * math.sin(angleRadians)
            # add a small amount of variance around the location
            fraction = randint(0, 100000) / 100000
            longitude += (fraction * fraction * variance) - (variance / 2.0)

            # gps locations aren't transcendental, so round to a fixed
            # number of decimal places
            latitude = int(latitude * 10000) / 10000.0
            longitude = int(longitude * 10000) / 10000.0
            return latitude, longitude, latdirection, longdirection

    return (default_latitude, default_longitude,
            default_latdirection, default_longdirection)
