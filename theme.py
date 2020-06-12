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
    return ('Default', 'Blue', 'Hacker', 'Henge', 'HighVis',
            'LCD', 'Light', 'Night', 'Purple', 'Starlight', 'Zen')


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
        "hashtag-vertical-spacing3": "100px",
        "hashtag-vertical-spacing4": "150px",
        "time-vertical-align": "-10px",
        "*font-family": "'Domestic_Manners'",
        "*src": "url('./fonts/Domestic_Manners.ttf') format('truetype')"
    }
    setThemeFromDict(baseDir, 'blue', themeParams)


def setThemeNight(baseDir: str):
    removeTheme(baseDir)
    setThemeInConfig(baseDir, 'night')
    fontStr = \
        "url('./fonts/CheGuevaraTextSans-Regular.ttf') format('truetype')"
    themeParams = {
        "font-size-button-mobile": "36px",
        "font-size": "32px",
        "font-size2": "26px",
        "font-size3": "40px",
        "font-size4": "24px",
        "font-size5": "22px",
        "cw-glow-radius1": "5px",
        "cw-glow-radius2": "6px",
        "cw-glow-radius3": "7px",
        "cw-glow-radius4": "8px",
        "cw-glow-radius5": "9px",
        "cw-glow-color1": "#7961ab",
        "cw-glow-color2": "#7961ab",
        "cw-glow-color3": "#7961ab",
        "cw-glow-color4": "#7961ab",
        "cw-glow-color5": "#7961ab",
        "cw-background": "black",
        "main-bg-color": "#0f0d10",
        "text-entry-background": "#0f0d10",
        "link-bg-color": "#0f0d10",
        "main-fg-color": "#7961ab",
        "main-bg-color-dm": "#0b0a0a",
        "border-color": "#7961ab",
        "main-bg-color-reply": "#0f0d10",
        "main-bg-color-report": "#0f0d10",
        "hashtag-vertical-spacing3": "100px",
        "hashtag-vertical-spacing4": "150px",
        "button-background": "#7961ab",
        "button-selected": "#86579d",
        "calendar-bg-color": "#0f0d10",
        "lines-color": "#7961ab",
        "day-number": "#7961ab",
        "day-number2": "#555",
        "event-background": "#111",
        "*font-family": "'CheGuevaraTextSans-Regular'",
        "*src": fontStr
    }
    setThemeFromDict(baseDir, 'night', themeParams)


def setThemeStarlight(baseDir: str):
    removeTheme(baseDir)
    setThemeInConfig(baseDir, 'starlight')
    themeParams = {
        "font-size-button-mobile": "36px",
        "font-size": "32px",
        "font-size2": "26px",
        "font-size3": "40px",
        "font-size4": "24px",
        "font-size5": "22px",
        "main-bg-color": "#0f0d10",
        "text-entry-background": "#0f0d10",
        "link-bg-color": "#0f0d10",
        "main-link-color": "#ffc4bc",
        "main-visited-color": "#e1c4bc",
        "main-fg-color": "#ffc4bc",
        "main-bg-color-dm": "#0b0a0a",
        "border-color": "#69282c",
        "border-width": "3px",
        "main-bg-color-reply": "#0f0d10",
        "main-bg-color-report": "#0f0d10",
        "hashtag-vertical-spacing3": "100px",
        "hashtag-vertical-spacing4": "150px",
        "button-background": "#69282c",
        "button-selected": "#a34046",
        "calendar-bg-color": "#0f0d10",
        "title-text": "#ffc4bc",
        "title-background": "#69282c",
        "lines-color": "#ffc4bc",
        "day-number": "#ffc4bc",
        "day-number2": "#aaa",
        "event-background": "#111",
        "cw-glow-radius1": "30px",
        "cw-glow-radius2": "40px",
        "cw-glow-radius3": "50px",
        "cw-glow-radius4": "60px",
        "cw-glow-radius5": "70px",
        "cw-glow-color1": "#a3d5f0",
        "cw-glow-color2": "#a3d5f0",
        "cw-glow-color3": "#a3d5f0",
        "cw-glow-color4": "#a3d5f0",
        "cw-glow-color5": "#a3d5f0",
        "cw-background": "black",
        "timeline-border-radius": "20px",
        "image-corners": "2%",
        "*font-family": "'bgrove'",
        "*src": "url('fonts/bgrove.ttf') format('truetype')"
    }
    setThemeFromDict(baseDir, 'starlight', themeParams)


def setThemeHenge(baseDir: str):
    removeTheme(baseDir)
    setThemeInConfig(baseDir, 'henge')
    themeParams = {
        "font-size-button-mobile": "36px",
        "font-size": "32px",
        "font-size2": "26px",
        "font-size3": "40px",
        "font-size4": "24px",
        "font-size5": "22px",
        "main-bg-color": "#20260e",
        "text-entry-background": "#20260e",
        "link-bg-color": "#20260e",
        "main-link-color": "#ffc4bc",
        "main-visited-color": "#e1c4bc",
        "main-fg-color": "#ffc4bc",
        "main-bg-color-dm": "#0b0a0a",
        "border-color": "#69282c",
        "border-width": "3px",
        "main-bg-color-reply": "#20260e",
        "main-bg-color-report": "#20260e",
        "hashtag-vertical-spacing3": "100px",
        "hashtag-vertical-spacing4": "150px",
        "button-background": "#69282c",
        "button-selected": "#a34046",
        "calendar-bg-color": "#20260e",
        "title-text": "#ffc4bc",
        "title-background": "#69282c",
        "lines-color": "#ffc4bc",
        "day-number": "#ffc4bc",
        "day-number2": "#aaa",
        "event-background": "#111",
        "cw-glow-radius1": "30px",
        "cw-glow-radius2": "40px",
        "cw-glow-radius3": "50px",
        "cw-glow-radius4": "60px",
        "cw-glow-radius5": "70px",
        "cw-glow-color1": "#a3d5f0",
        "cw-glow-color2": "#a3d5f0",
        "cw-glow-color3": "#a3d5f0",
        "cw-glow-color4": "#a3d5f0",
        "cw-glow-color5": "#a3d5f0",
        "cw-background": "#20260e",
        "timeline-border-radius": "20px",
        "image-corners": "8%",
        "*font-family": "'bgrove'",
        "*src": "url('fonts/bgrove.ttf') format('truetype')"
    }
    setThemeFromDict(baseDir, 'henge', themeParams)


def setThemeZen(baseDir: str):
    removeTheme(baseDir)
    setThemeInConfig(baseDir, 'zen')
    themeParams = {
        "main-bg-color": "#5c4e41",
        "text-entry-background": "#5c4e41",
        "link-bg-color": "#5c4e41",
        "main-bg-color-reply": "#5c4e41",
        "main-bg-color-report": "#5c4e41",
        "day-number2": "#5c4e41",
        "border-color": "#463b35",
        "border-width": "7px",
        "main-link-color": "#dddddd",
        "main-visited-color": "#dddddd",
        "button-background": "#463b35",
        "button-selected": "#26201d",
        "main-bg-color-dm": "#5c4a40",
        "main-header-color-roles": "#5c4e41",
        "cw-background": "#463b35",
        "dropdown-bg-color": "#504e41",
        "dropdown-bg-color-hover": "#444"
    }
    setThemeFromDict(baseDir, 'zen', themeParams)


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
        "hashtag-vertical-spacing3": "100px",
        "hashtag-vertical-spacing4": "150px",
        "time-vertical-align": "-10px",
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
        "font-size-button-mobile": "36px",
        "font-size": "32px",
        "font-size2": "26px",
        "font-size3": "40px",
        "font-size4": "24px",
        "font-size5": "22px",
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
        "main-bg-color-dm": "#0b0a0a",
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
        "gallery-text-color": "green",
        "image-corners": "0%"
    }
    setThemeFromDict(baseDir, 'hacker', themeParams)


def setThemeLight(baseDir: str):
    themeParams = {
        "font-size-button-mobile": "36px",
        "font-size": "32px",
        "font-size2": "26px",
        "font-size3": "40px",
        "font-size4": "24px",
        "font-size5": "22px",
        "rgba(0, 0, 0, 0.5)": "rgba(0, 0, 0, 0.0)",
        "main-bg-color": "#e6ebf0",
        "main-bg-color-dm": "#e3dbf0",
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
        "dropdown-fg-color": "#222",
        "dropdown-fg-color-hover": "#222",
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
        searchBannerFilename = \
            baseDir + '/img/search_banner.png'
    else:
        profileImageFilename = \
            baseDir + '/img/image_' + themeNameLower + '.png'
        bannerFilename = \
            baseDir + '/img/banner_' + themeNameLower + '.png'
        searchBannerFilename = \
            baseDir + '/img/search_banner_' + themeNameLower + '.png'
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
                except BaseException:
                    pass

                try:
                    copyfile(bannerFilename,
                             accountDir + '/banner.png')
                except BaseException:
                    pass

                try:
                    if os.path.isfile(searchBannerFilename):
                        copyfile(searchBannerFilename,
                                 accountDir + '/search_banner.png')
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
