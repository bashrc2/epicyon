__filename__ = "theme.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
from utils import loadJson
from utils import saveJson
from shutil import copyfile


def getThemesList() -> []:
    """Returns the list of available themes
    Note that these should be capitalized, since they're
    also used to create the web interface dropdown list
    and to lookup function names
    """
    return ('Default', 'Blue', 'Hacker', 'HighVis',
            'LCD', 'Light', 'Purple')


def setThemeInConfig(baseDir: str, name: str) -> bool:
    configFilename = baseDir + '/config.json'
    if not os.path.isfile(configFilename):
        return False
    configJson = loadJson(configFilename, 0)
    if not configJson:
        return False
    configJson['theme'] = name
    return saveJson(configJson, configFilename)


def getTheme(baseDir: str) -> str:
    configFilename = baseDir + '/config.json'
    if os.path.isfile(configFilename):
        configJson = loadJson(configFilename, 0)
        if configJson:
            if configJson.get('theme'):
                return configJson['theme']
    return 'default'


def removeTheme(baseDir: str):
    themeFiles = ('epicyon.css', 'login.css', 'follow.css',
                  'suspended.css', 'calendar.css', 'blog.css')
    for filename in themeFiles:
        if os.path.isfile(baseDir + '/' + filename):
            os.remove(baseDir + '/' + filename)


def setCSSparam(css: str, param: str, value: str) -> str:
    """Sets a CSS parameter to a given value
    """
    # is this just a simple string replacement?
    if ';' in param:
        return css.replace(param, value)
    # color replacement
    if param.startswith('rgba('):
        return css.replace(param, value)
    # if the parameter begins with * then don't prepend --
    if param.startswith('*'):
        searchStr = param.replace('*', '') + ':'
    else:
        searchStr = '--' + param + ':'
    if searchStr not in css:
        return css
    s = css.split(searchStr)
    newcss = ''
    for sectionStr in s:
        if not newcss:
            if sectionStr:
                newcss = sectionStr
            else:
                newcss = ' '
        else:
            if ';' in sectionStr:
                newcss += \
                    searchStr + ' ' + value + ';' + sectionStr.split(';', 1)[1]
            else:
                newcss += searchStr + ' ' + sectionStr
    return newcss.strip()


def setThemeFromDict(baseDir: str, name: str, themeParams: {}) -> None:
    """Uses a dictionary to set a theme
    """
    setThemeInConfig(baseDir, name)
    themeFiles = ('epicyon.css', 'login.css', 'follow.css',
                  'suspended.css', 'calendar.css', 'blog.css')
    for filename in themeFiles:
        templateFilename = baseDir + '/epicyon-' + filename
        if filename == 'epicyon.css':
            templateFilename = baseDir + '/epicyon-profile.css'
        if not os.path.isfile(templateFilename):
            continue
        with open(templateFilename, 'r') as cssfile:
            css = cssfile.read()
            for paramName, paramValue in themeParams.items():
                css = setCSSparam(css, paramName, paramValue)
            filename = baseDir + '/' + filename
            with open(filename, 'w') as cssfile:
                cssfile.write(css)


def setCustomFont(baseDir: str):
    """Uses a dictionary to set a theme
    """
    customFontExt = None
    customFontType = None
    fontExtension = {
        'woff': 'woff',
        'woff2': 'woff2',
        'otf': 'opentype',
        'ttf': 'truetype'
    }
    for ext, extType in fontExtension.items():
        filename = baseDir + '/fonts/custom.' + ext
        if os.path.isfile(filename):
            customFontExt = ext
            customFontType = extType
    if not customFontExt:
        return

    themeFiles = ('epicyon.css', 'login.css', 'follow.css',
                  'suspended.css', 'calendar.css', 'blog.css')
    for filename in themeFiles:
        templateFilename = baseDir + '/' + filename
        if not os.path.isfile(templateFilename):
            continue
        with open(templateFilename, 'r') as cssfile:
            css = cssfile.read()
            css = \
                setCSSparam(css, "*src",
                            "url('./fonts/custom." +
                            customFontExt +
                            "') format('" +
                            customFontType + "')")
            css = setCSSparam(css, "*font-family", "'CustomFont'")
            filename = baseDir + '/' + filename
            with open(filename, 'w') as cssfile:
                cssfile.write(css)


def setThemeDefault(baseDir: str):
    removeTheme(baseDir)
    setThemeInConfig(baseDir, 'default')
    themeParams = {
        "dummyValue": "1234"
    }
    setThemeFromDict(baseDir, 'default', themeParams)


def setThemeBlue(baseDir: str):
    removeTheme(baseDir)
    setThemeInConfig(baseDir, 'blue')
    themeParams = {
        "font-size-header": "22px",
        "font-size": "45px",
        "font-size2": "45px",
        "font-size3": "45px",
        "font-size4": "35px",
        "font-size5": "29px",
        "gallery-font-size": "35px",
        "gallery-font-size-mobile": "55px",
        "main-bg-color": "#002365",
        "text-entry-background": "#002365",
        "link-bg-color": "#002365",
        "main-bg-color-reply": "#002365",
        "main-bg-color-report": "#002365",
        "day-number2": "#002365",
        "*font-family": "'Domestic_Manners'",
        "*src": "url('./fonts/Domestic_Manners.ttf') format('truetype')"
    }
    setThemeFromDict(baseDir, 'blue', themeParams)


def setThemeHighVis(baseDir: str):
    themeParams = {
        "font-size-header": "22px",
        "font-size": "45px",
        "font-size2": "45px",
        "font-size3": "45px",
        "font-size4": "35px",
        "font-size5": "29px",
        "gallery-font-size": "35px",
        "gallery-font-size-mobile": "55px",
        "*font-family": "'LinBiolinum_Rah'",
        "*src": "url('./fonts/LinBiolinum_Rah.ttf') format('truetype')"
    }
    setThemeFromDict(baseDir, 'highvis', themeParams)


def setThemeLCD(baseDir: str):
    themeParams = {
        "main-bg-color": "#9fb42b",
        "link-bg-color": "#33390d",
        "cw-background": "#13390d",
        "text-entry-foreground": "#33390d",
        "text-entry-background": "#9fb42b",
        "main-bg-color-reply": "#9fb42b",
        "main-bg-color-report": "#9fb42b",
        "main-bg-color-dm": "#5fb42b",
        "main-header-color-roles": "#9fb42b",
        "main-fg-color": "#33390d",
        "border-color": "#33390d",
        "border-width": "5px",
        "main-link-color": "#9fb42b",
        "main-visited-color": "#9fb42b",
        "button-selected": "black",
        "button-highlighted": "green",
        "button-background": "#33390d",
        "button-text": "#9fb42b",
        "color: #FFFFFE;": "color: #9fb42b;",
        "calendar-bg-color": "#eee",
        "day-number": "#3f2145",
        "day-number2": "#9fb42b",
        "time-color": "#9fb42b",
        "place-color": "black",
        "event-color": "#282c37",
        "today-foreground": "white",
        "today-circle": "red",
        "event-background": "yellow",
        "event-foreground": "white",
        "title-text": "white",
        "gallery-text-color": "#33390d",
        "font-size-header": "22px",
        "font-size": "45px",
        "font-size2": "45px",
        "font-size3": "45px",
        "font-size4": "35px",
        "font-size5": "29px",
        "gallery-font-size": "35px",
        "gallery-font-size-mobile": "55px",
        "button-corner-radius": "1px",
        "timeline-border-radius": "1px",
        "dropdown-bg-color": "#33390d",
        "dropdown-bg-color-hover": "#7fb42b",
        "dropdown-fg-color-hover": "black",
        "dropdown-fg-color": "#9fb42b",
        "font-color-header": "#9fb42b",
        "lines-color": "#33390d",
        "title-background": "#33390d",
        "*font-family": "'LcdSolid'",
        "*src": "url('./fonts/LcdSolid.ttf') format('truetype')"
    }
    setThemeFromDict(baseDir, 'lcd', themeParams)


def setThemePurple(baseDir: str):
    fontStr = \
        "url('./fonts/CheGuevaraTextSans-Regular.ttf') format('truetype')"
    themeParams = {
        "main-bg-color": "#1f152d",
        "link-bg-color": "#1f152d",
        "main-bg-color-reply": "#1a142d",
        "main-bg-color-report": "#12152d",
        "main-header-color-roles": "#1f192d",
        "main-fg-color": "#f98bb0",
        "border-color": "#3f2145",
        "main-link-color": "#ff42a0",
        "main-visited-color": "#f93bb0",
        "button-selected": "#c042a0",
        "button-background": "#ff42a0",
        "button-text": "white",
        "cw-background": "#ff42a0",
        "color: #FFFFFE;": "color: #1f152d;",
        "calendar-bg-color": "#eee",
        "lines-color": "#ff42a0",
        "day-number": "#3f2145",
        "day-number2": "#1f152d",
        "time-color": "#ff42a0",
        "place-color": "black",
        "event-color": "#282c37",
        "today-foreground": "white",
        "today-circle": "red",
        "event-background": "yellow",
        "event-foreground": "white",
        "title-text": "white",
        "title-background": "#ff42a0",
        "gallery-text-color": "#ccc",
        "*font-family": "'CheGuevaraTextSans-Regular'",
        "*src": fontStr
    }
    setThemeFromDict(baseDir, 'purple', themeParams)


def setThemeHacker(baseDir: str):
    themeParams = {
        "main-bg-color": "black",
        "link-bg-color": "black",
        "main-bg-color-reply": "#030202",
        "main-bg-color-report": "#050202",
        "main-header-color-roles": "#1f192d",
        "main-fg-color": "#00ff00",
        "border-color": "#035103",
        "main-link-color": "#2fff2f",
        "main-visited-color": "#3c8234",
        "button-selected": "#063200",
        "button-background": "#062200",
        "button-text": "#00ff00",
        "button-corner-radius": "4px",
        "timeline-border-radius": "4px",
        "*font-family": "'Bedstead'",
        "*src": "url('./fonts/bedstead.otf') format('opentype')",
        "cw-background": "#062200",
        "color: #FFFFFE;": "color: green;",
        "calendar-bg-color": "black",
        "lines-color": "green",
        "day-number": "green",
        "day-number2": "darkgreen",
        "time-color": "darkgreen",
        "place-color": "green",
        "event-color": "green",
        "today-foreground": "white",
        "today-circle": "red",
        "event-background": "lightgreen",
        "event-foreground": "black",
        "title-text": "black",
        "title-background": "darkgreen",
        "gallery-text-color": "green"
    }
    setThemeFromDict(baseDir, 'hacker', themeParams)


def setThemeLight(baseDir: str):
    themeParams = {
        "rgba(0, 0, 0, 0.5)": "rgba(0, 0, 0, 0.0)",
        "main-bg-color": "#e6ebf0",
        "link-bg-color": "#e6ebf0",
        "main-bg-color-reply": "#e0dbf0",
        "main-bg-color-report": "#e3dbf0",
        "main-header-color-roles": "#ebebf0",
        "main-fg-color": "#2d2c37",
        "border-color": "#c0cdd9",
        "main-link-color": "#2a2c37",
        "main-visited-color": "#232c37",
        "text-entry-foreground": "#111",
        "text-entry-background": "white",
        "font-color-header": "black",
        "dropdown-bg-color": "white",
        "dropdown-bg-color-hover": "lightgrey",
        "cw-background": "white",
        "color: #FFFFFE;": "color: black;",
        "calendar-bg-color": "#e6ebf0",
        "lines-color": "darkblue",
        "day-number": "black",
        "day-number2": "#282c37",
        "place-color": "black",
        "event-color": "#282c37",
        "today-foreground": "white",
        "today-circle": "red",
        "event-background": "lightblue",
        "event-foreground": "white",
        "title-text": "#282c37",
        "title-background": "#ccc",
        "gallery-text-color": "black",
        "*font-family": "'ElectrumADFExp-Regular'",
        "*src": "url('./fonts/ElectrumADFExp-Regular.otf') format('opentype')"
    }
    setThemeFromDict(baseDir, 'light', themeParams)


def setThemeImages(baseDir: str, name: str) -> None:
    """Changes the profile background image
    and banner to the defaults
    """
    themeNameLower = name.lower()

    if themeNameLower == 'default':
        profileImageFilename = \
            baseDir + '/img/image.png'
        bannerFilename = \
            baseDir + '/img/banner.png'
    else:
        profileImageFilename = \
            baseDir + '/img/image_' + themeNameLower + '.png'
        bannerFilename = \
            baseDir + '/img/banner_' + themeNameLower + '.png'
    if os.path.isfile(profileImageFilename) and \
       os.path.isfile(bannerFilename):
        for subdir, dirs, files in os.walk(baseDir +
                                           '/accounts'):
            for acct in dirs:
                if '@' not in acct:
                    continue
                if 'inbox@' in acct:
                    continue
                accountDir = \
                    os.path.join(baseDir + '/accounts', acct)
                try:
                    copyfile(profileImageFilename,
                             accountDir + '/image.png')
                    copyfile(bannerFilename,
                             accountDir + '/banner.png')
                except BaseException:
                    pass


def setTheme(baseDir: str, name: str) -> bool:
    result = False

    prevThemeName = getTheme(baseDir)

    themes = getThemesList()
    for themeName in themes:
        themeNameLower = themeName.lower()
        if name == themeNameLower:
            globals()['setTheme' + themeName](baseDir)
            if prevThemeName:
                if prevThemeName.lower() != themeNameLower:
                    # change the banner and profile image
                    # to the default for the theme
                    setThemeImages(baseDir, name)
            result = True

    if not result:
        # default
        setThemeDefault(baseDir)
        result = True

    setCustomFont(baseDir)
    return result
