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


def getThemeFiles() -> []:
    return ('epicyon.css', 'login.css', 'follow.css',
            'suspended.css', 'calendar.css', 'blog.css',
            'options.css', 'search.css', 'links.css')


def getThemesList() -> []:
    """Returns the list of available themes
    Note that these should be capitalized, since they're
    also used to create the web interface dropdown list
    and to lookup function names
    """
    return ('Default', 'Blue', 'Hacker', 'Henge', 'HighVis',
            'IndymediaClassic', 'IndymediaModern',
            'LCD', 'Light', 'Night', 'Purple', 'Solidaric',
            'Starlight', 'Zen')


def setThemeInConfig(baseDir: str, name: str) -> bool:
    configFilename = baseDir + '/config.json'
    if not os.path.isfile(configFilename):
        return False
    configJson = loadJson(configFilename, 0)
    if not configJson:
        return False
    configJson['theme'] = name
    return saveJson(configJson, configFilename)


def setNewswirePublishAsIcon(baseDir: str, useIcon: bool) -> bool:
    """Shows the newswire publish action as an icon or a button
    """
    configFilename = baseDir + '/config.json'
    if not os.path.isfile(configFilename):
        return False
    configJson = loadJson(configFilename, 0)
    if not configJson:
        return False
    configJson['showPublishAsIcon'] = useIcon
    return saveJson(configJson, configFilename)


def setIconsAsButtons(baseDir: str, useButtons: bool) -> bool:
    """Whether to show icons in the header (inbox, outbox, etc)
    as buttons
    """
    configFilename = baseDir + '/config.json'
    if not os.path.isfile(configFilename):
        return False
    configJson = loadJson(configFilename, 0)
    if not configJson:
        return False
    configJson['iconsAsButtons'] = useButtons
    return saveJson(configJson, configFilename)


def setRssIconAtTop(baseDir: str, atTop: bool) -> bool:
    """Whether to show RSS icon at the top of the timeline
    """
    configFilename = baseDir + '/config.json'
    if not os.path.isfile(configFilename):
        return False
    configJson = loadJson(configFilename, 0)
    if not configJson:
        return False
    configJson['rssIconAtTop'] = atTop
    return saveJson(configJson, configFilename)


def setPublishButtonAtTop(baseDir: str, atTop: bool) -> bool:
    """Whether to show the publish button above the title image
    in the newswire column
    """
    configFilename = baseDir + '/config.json'
    if not os.path.isfile(configFilename):
        return False
    configJson = loadJson(configFilename, 0)
    if not configJson:
        return False
    configJson['publishButtonAtTop'] = atTop
    return saveJson(configJson, configFilename)


def setFullWidthTimelineButtonHeader(baseDir: str, fullWidth: bool) -> bool:
    """Shows the timeline button header containing inbox, outbox,
    calendar, etc as full width
    """
    configFilename = baseDir + '/config.json'
    if not os.path.isfile(configFilename):
        return False
    configJson = loadJson(configFilename, 0)
    if not configJson:
        return False
    configJson['fullWidthTimelineButtonHeader'] = fullWidth
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
    themeFiles = getThemeFiles()
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
    onceOnly = False
    if param.startswith('*'):
        if param.startswith('**'):
            onceOnly = True
            searchStr = param.replace('**', '') + ':'
        else:
            searchStr = param.replace('*', '') + ':'
    else:
        searchStr = '--' + param + ':'
    if searchStr not in css:
        return css
    if onceOnly:
        s = css.split(searchStr, 1)
    else:
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


def setThemeFromDict(baseDir: str, name: str,
                     themeParams: {}, bgParams: {}) -> None:
    """Uses a dictionary to set a theme
    """
    if name:
        setThemeInConfig(baseDir, name)
    themeFiles = getThemeFiles()
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
            with open(filename, 'w+') as cssfile:
                cssfile.write(css)

    if bgParams.get('login'):
        setBackgroundFormat(baseDir, name, 'login', bgParams['login'])
    if bgParams.get('follow'):
        setBackgroundFormat(baseDir, name, 'follow', bgParams['follow'])
    if bgParams.get('options'):
        setBackgroundFormat(baseDir, name, 'options', bgParams['options'])
    if bgParams.get('search'):
        setBackgroundFormat(baseDir, name, 'search', bgParams['search'])


def setBackgroundFormat(baseDir: str, name: str,
                        backgroundType: str, extension: str) -> None:
    """Sets the background file extension
    """
    if extension == 'jpg':
        return
    cssFilename = baseDir + '/' + backgroundType + '.css'
    if not os.path.isfile(cssFilename):
        return
    with open(cssFilename, 'r') as cssfile:
        css = cssfile.read()
        css = css.replace('background.jpg', 'background.' + extension)
        with open(cssFilename, 'w+') as cssfile2:
            cssfile2.write(css)


def enableGrayscale(baseDir: str) -> None:
    """Enables grayscale for the current theme
    """
    themeFiles = getThemeFiles()
    for filename in themeFiles:
        templateFilename = baseDir + '/' + filename
        if not os.path.isfile(templateFilename):
            continue
        with open(templateFilename, 'r') as cssfile:
            css = cssfile.read()
            if 'grayscale' not in css:
                css = \
                    css.replace('body, html {',
                                'body, html {\n    filter: grayscale(100%);')
                filename = baseDir + '/' + filename
                with open(filename, 'w+') as cssfile:
                    cssfile.write(css)
    grayscaleFilename = baseDir + '/accounts/.grayscale'
    if not os.path.isfile(grayscaleFilename):
        with open(grayscaleFilename, 'w+') as grayfile:
            grayfile.write(' ')


def disableGrayscale(baseDir: str) -> None:
    """Disables grayscale for the current theme
    """
    themeFiles = getThemeFiles()
    for filename in themeFiles:
        templateFilename = baseDir + '/' + filename
        if not os.path.isfile(templateFilename):
            continue
        with open(templateFilename, 'r') as cssfile:
            css = cssfile.read()
            if 'grayscale' in css:
                css = \
                    css.replace('\n    filter: grayscale(100%);', '')
                filename = baseDir + '/' + filename
                with open(filename, 'w+') as cssfile:
                    cssfile.write(css)
    grayscaleFilename = baseDir + '/accounts/.grayscale'
    if os.path.isfile(grayscaleFilename):
        os.remove(grayscaleFilename)


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

    themeFiles = getThemeFiles()
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
            with open(filename, 'w+') as cssfile:
                cssfile.write(css)


def setThemeDefault(baseDir: str):
    name = 'default'
    removeTheme(baseDir)
    setThemeInConfig(baseDir, name)
    setNewswirePublishAsIcon(baseDir, True)
    setFullWidthTimelineButtonHeader(baseDir, False)
    setIconsAsButtons(baseDir, False)
    setRssIconAtTop(baseDir, True)
    setPublishButtonAtTop(baseDir, False)
    bgParams = {
        "login": "jpg",
        "follow": "jpg",
        "options": "jpg",
        "search": "jpg"
    }
    themeParams = {
        "banner-height": "20vh",
        "banner-height-mobile": "10vh",
        "search-banner-height-mobile": "15vh"
    }
    setThemeFromDict(baseDir, name, themeParams, bgParams)


def setThemeIndymediaClassic(baseDir: str):
    name = 'indymediaclassic'
    removeTheme(baseDir)
    setThemeInConfig(baseDir, name)
    setNewswirePublishAsIcon(baseDir, True)
    setFullWidthTimelineButtonHeader(baseDir, True)
    setIconsAsButtons(baseDir, False)
    setRssIconAtTop(baseDir, False)
    setPublishButtonAtTop(baseDir, False)
    bgParams = {
        "login": "jpg",
        "follow": "jpg",
        "options": "jpg",
        "search": "jpg"
    }
    themeParams = {
        "container-button-padding": "0px",
        "hashtag-background-color": "darkred",
        "font-size-newswire": "18px",
        "font-size-publish-button": "18px",
        "font-size-newswire-mobile": "40px",
        "line-spacing-newswire": "100%",
        "newswire-item-moderated-color": "white",
        "newswire-date-moderated-color": "white",
        "newswire-date-color": "white",
        "newswire-voted-background-color": "black",
        "column-left-image-width-mobile": "40vw",
        "column-right-fg-color": "#ff9900",
        "column-right-fg-color-voted-on": "red",
        "button-corner-radius": "5px",
        "timeline-border-radius": "5px",
        "focus-color": "blue",
        "font-size-button-mobile": "26px",
        "font-size": "32px",
        "font-size2": "26px",
        "font-size3": "40px",
        "font-size4": "24px",
        "font-size5": "22px",
        "main-bg-color": "black",
        "column-left-header-color": "#fff",
        "column-left-header-background": "#555",
        "column-left-header-size": "20px",
        "column-left-color": "#003366",
        "text-entry-background": "#0f0d10",
        "link-bg-color": "black",
        "main-link-color": "#ff9900",
        "main-link-color-hover": "#d09338",
        "main-visited-color": "#ffb900",
        "main-fg-color": "white",
        "column-left-fg-color": "white",
        "main-bg-color-dm": "#0b0a0a",
        "border-color": "#003366",
        "border-width": "0",
        "border-width-header": "0",
        "main-bg-color-reply": "#0f0d10",
        "main-bg-color-report": "#0f0d10",
        "hashtag-vertical-spacing3": "100px",
        "hashtag-vertical-spacing4": "150px",
        "button-background-hover": "darkblue",
        "button-text-hover": "white",
        "publish-button-background": "#ff9900",
        "publish-button-text": "#003366",
        "button-background": "#003366",
        "button-selected": "blue",
        "calendar-bg-color": "#0f0d10",
        "event-background": "#555",
        "border-color": "#003366",
        "lines-color": "#ff9900",
        "day-number": "lightblue",
        "day-number2": "white",
        "time-color": "#003366",
        "place-color": "#003366",
        "event-color": "#003366",
        "title-text": "white",
        "title-background": "#003366",
        "quote-right-margin": "0.1em",
        "column-left-width": "10vw",
        "column-center-width": "70vw",
        "column-right-width": "20vw",
        "column-right-icon-size": "11%",
        "login-button-color": "red",
        "login-button-fg-color": "white"
    }
    setThemeFromDict(baseDir, name, themeParams, bgParams)


def setThemeBlue(baseDir: str):
    name = 'blue'
    removeTheme(baseDir)
    setThemeInConfig(baseDir, name)
    setNewswirePublishAsIcon(baseDir, True)
    setFullWidthTimelineButtonHeader(baseDir, False)
    setIconsAsButtons(baseDir, False)
    setRssIconAtTop(baseDir, True)
    setPublishButtonAtTop(baseDir, False)
    themeParams = {
        "banner-height": "20vh",
        "banner-height-mobile": "10vh",
        "newswire-date-color": "blue",
        "font-size-header": "22px",
        "font-size-header-mobile": "32px",
        "font-size": "45px",
        "font-size2": "45px",
        "font-size3": "45px",
        "font-size4": "35px",
        "font-size5": "29px",
        "gallery-font-size": "35px",
        "gallery-font-size-mobile": "55px",
        "main-bg-color": "#002365",
        "column-left-color": "#002365",
        "text-entry-background": "#002365",
        "link-bg-color": "#002365",
        "main-bg-color-reply": "#002365",
        "main-bg-color-report": "#002365",
        "day-number2": "#002365",
        "hashtag-vertical-spacing3": "100px",
        "hashtag-vertical-spacing4": "150px",
        "time-vertical-align": "-10px",
        "*font-family": "'Domestic_Manners'",
        "*src": "url('./fonts/Domestic_Manners.woff2') format('woff2')"
    }
    bgParams = {
        "login": "jpg",
        "follow": "jpg",
        "options": "jpg",
        "search": "jpg"
    }
    setThemeFromDict(baseDir, name, themeParams, bgParams)


def setThemeNight(baseDir: str):
    name = 'night'
    removeTheme(baseDir)
    setThemeInConfig(baseDir, name)
    setNewswirePublishAsIcon(baseDir, True)
    setFullWidthTimelineButtonHeader(baseDir, False)
    setIconsAsButtons(baseDir, False)
    setRssIconAtTop(baseDir, True)
    setPublishButtonAtTop(baseDir, False)
    fontStr = \
        "url('./fonts/solidaric.woff2') format('woff2')"
    fontStrItalic = \
        "url('./fonts/solidaric-italic.woff2') format('woff2')"
    themeParams = {
        "main-visited-color": "#0481f5",
        "post-separator-margin-top": "9%",
        "post-separator-margin-bottom": "9%",
        "post-separator-width": "80%",
        "post-separator-height": "10%",
        "column-left-header-background": "#07447c",
        "banner-height": "15vh",
        "banner-height-mobile": "10vh",
        "focus-color": "blue",
        "font-size-button-mobile": "26px",
        "font-size": "32px",
        "font-size2": "26px",
        "font-size3": "40px",
        "font-size4": "24px",
        "font-size5": "22px",
        "main-bg-color": "#0f0d10",
        "column-left-color": "#0f0d10",
        "text-entry-background": "#0f0d10",
        "link-bg-color": "#0f0d10",
        "main-link-color": "#6481f5",
        "main-link-color-hover": "#d09338",
        "main-fg-color": "#0481f5",
        "column-left-fg-color": "#0481f5",
        "main-bg-color-dm": "#0b0a0a",
        "border-color": "#606984",
        "main-bg-color-reply": "#0f0d10",
        "main-bg-color-report": "#0f0d10",
        "hashtag-vertical-spacing3": "100px",
        "hashtag-vertical-spacing4": "150px",
        "button-background-hover": "#0481f5",
        "button-text-hover": "#0f0d10",
        "publish-button-background": "#07447c",
        "button-background": "#07447c",
        "button-selected": "#0481f5",
        "calendar-bg-color": "#0f0d10",
        "lines-color": "#a961ab",
        "day-number": "#a961ab",
        "day-number2": "#555",
        "time-color": "#a961ab",
        "time-vertical-align": "-4px",
        "time-vertical-align-mobile": "15px",
        "place-color": "#a961ab",
        "event-color": "#a961ab",
        "event-background": "#333",
        "quote-right-margin": "0",
        "line-spacing": "150%",
        "*font-family": "'solidaric'",
        "*src": fontStr,
        "**src": fontStrItalic
    }
    bgParams = {
        "login": "jpg",
        "follow": "jpg",
        "options": "jpg",
        "search": "jpg"
    }
    setThemeFromDict(baseDir, name, themeParams, bgParams)


def setThemeStarlight(baseDir: str):
    name = 'starlight'
    removeTheme(baseDir)
    setThemeInConfig(baseDir, name)
    setNewswirePublishAsIcon(baseDir, True)
    setFullWidthTimelineButtonHeader(baseDir, False)
    setIconsAsButtons(baseDir, False)
    setRssIconAtTop(baseDir, True)
    setPublishButtonAtTop(baseDir, False)
    themeParams = {
        "search-banner-height-mobile": "15vh",
        "column-left-header-background": "#69282c",
        "column-left-image-width-mobile": "40vw",
        "line-spacing-newswire": "120%",
        "focus-color": "darkred",
        "font-size-button-mobile": "26px",
        "font-size": "32px",
        "font-size2": "26px",
        "font-size3": "40px",
        "font-size4": "24px",
        "font-size5": "22px",
        "main-bg-color": "#0f0d10",
        "column-left-color": "#0f0d10",
        "text-entry-background": "#0f0d10",
        "link-bg-color": "#0f0d10",
        "main-link-color": "#ffc4bc",
        "main-link-color-hover": "white",
        "title-color": "#ffc4bc",
        "main-visited-color": "#e1c4bc",
        "main-fg-color": "#ffc4bc",
        "column-left-fg-color": "#ffc4bc",
        "main-bg-color-dm": "#0b0a0a",
        "border-color": "#69282c",
        "border-width": "3px",
        "border-width-header": "3px",
        "main-bg-color-reply": "#0f0d10",
        "main-bg-color-report": "#0f0d10",
        "hashtag-vertical-spacing3": "100px",
        "hashtag-vertical-spacing4": "150px",
        "button-background-hover": "#a9282c",
        "button-text-hover": "#ffc4bc",
        "publish-button-background": "#69282c",
        "button-background": "#69282c",
        "button-small-background": "darkblue",
        "button-selected": "#a34046",
        "button-highlighted": "#12435f",
        "button-fg-highlighted": "white",
        "button-selected-highlighted": "#12435f",
        "button-approve": "#12435f",
        "calendar-bg-color": "#0f0d10",
        "title-text": "#ffc4bc",
        "title-background": "#69282c",
        "lines-color": "#ffc4bc",
        "day-number": "#ffc4bc",
        "day-number2": "#aaa",
        "event-background": "#12435f",
        "timeline-border-radius": "20px",
        "time-color": "#ffc4bc",
        "place-color": "#ffc4bc",
        "event-color": "#ffc4bc",
        "image-corners": "2%",
        "quote-right-margin": "0.1em",
        "*font-family": "'bgrove'",
        "*src": "url('fonts/bgrove.woff2') format('woff2')"
    }
    bgParams = {
        "login": "jpg",
        "follow": "jpg",
        "options": "jpg",
        "search": "jpg"
    }
    setThemeFromDict(baseDir, name, themeParams, bgParams)


def setThemeHenge(baseDir: str):
    name = 'henge'
    removeTheme(baseDir)
    setThemeInConfig(baseDir, name)
    setNewswirePublishAsIcon(baseDir, True)
    setFullWidthTimelineButtonHeader(baseDir, False)
    setIconsAsButtons(baseDir, False)
    setRssIconAtTop(baseDir, True)
    setPublishButtonAtTop(baseDir, False)
    themeParams = {
        "banner-height": "25vh",
        "column-left-image-width-mobile": "40vw",
        "column-right-image-width-mobile": "40vw",
        "font-size-button-mobile": "26px",
        "font-size": "32px",
        "font-size2": "26px",
        "font-size3": "40px",
        "font-size4": "24px",
        "font-size5": "22px",
        "main-bg-color": "#383335",
        "column-left-color": "#383335",
        "text-entry-background": "#383335",
        "link-bg-color": "#383335",
        "main-link-color": "white",
        "main-link-color-hover": "#ddd",
        "title-color": "white",
        "main-visited-color": "#e1c4bc",
        "main-fg-color": "white",
        "column-left-fg-color": "white",
        "main-bg-color-dm": "#343335",
        "border-color": "#222",
        "border-width": "5px",
        "border-width-header": "5px",
        "main-bg-color-reply": "#383335",
        "main-bg-color-report": "#383335",
        "hashtag-vertical-spacing3": "100px",
        "hashtag-vertical-spacing4": "150px",
        "button-background-hover": "#444",
        "button-text-hover": "white",
        "publish-button-background": "#222",
        "button-background": "#222",
        "button-selected": "black",
        "dropdown-fg-color": "#dddddd",
        "dropdown-bg-color": "#444",
        "dropdown-bg-color-hover": "#555",
        "dropdown-fg-color-hover": "#dddddd",
        "calendar-bg-color": "#383335",
        "title-text": "#c5d2b9",
        "title-background": "#444",
        "lines-color": "#c5d2b9",
        "day-number": "#c5d2b9",
        "day-number2": "#ccc",
        "event-background": "#333",
        "timeline-border-radius": "20px",
        "image-corners": "8%",
        "quote-right-margin": "0.1em",
        "*font-family": "'bgrove'",
        "*src": "url('fonts/bgrove.woff2') format('woff2')"
    }
    bgParams = {
        "login": "jpg",
        "follow": "jpg",
        "options": "jpg",
        "search": "jpg"
    }
    setThemeFromDict(baseDir, name, themeParams, bgParams)


def setThemeZen(baseDir: str):
    name = 'zen'
    removeTheme(baseDir)
    setThemeInConfig(baseDir, name)
    setNewswirePublishAsIcon(baseDir, True)
    setFullWidthTimelineButtonHeader(baseDir, False)
    setIconsAsButtons(baseDir, False)
    setRssIconAtTop(baseDir, True)
    setPublishButtonAtTop(baseDir, False)
    themeParams = {
        "banner-height": "25vh",
        "banner-height-mobile": "10vh",
        "newswire-date-color": "yellow",
        "main-bg-color": "#5c4e41",
        "column-left-color": "#5c4e41",
        "text-entry-background": "#5c4e41",
        "link-bg-color": "#5c4e41",
        "main-bg-color-reply": "#5c4e41",
        "main-bg-color-report": "#5c4e41",
        "day-number2": "#5c4e41",
        "border-color": "#463b35",
        "border-width": "7px",
        "border-width-header": "7px",
        "main-link-color": "#dddddd",
        "main-link-color-hover": "white",
        "title-color": "#dddddd",
        "main-visited-color": "#dddddd",
        "button-background-hover": "#a63b35",
        "publish-button-background": "#463b35",
        "button-background": "#463b35",
        "button-selected": "#26201d",
        "main-bg-color-dm": "#5c4a40",
        "main-header-color-roles": "#5c4e41",
        "dropdown-bg-color": "#504e41",
        "dropdown-bg-color-hover": "#444"
    }
    bgParams = {
        "login": "jpg",
        "follow": "jpg",
        "options": "jpg",
        "search": "jpg"
    }
    setThemeFromDict(baseDir, name, themeParams, bgParams)


def setThemeHighVis(baseDir: str):
    name = 'highvis'
    themeParams = {
        "font-size-header": "22px",
        "font-size-header-mobile": "32px",
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
        "*src": "url('./fonts/LinBiolinum_Rah.woff2') format('woff2')"
    }
    bgParams = {
        "login": "jpg",
        "follow": "jpg",
        "options": "jpg",
        "search": "jpg"
    }
    setThemeFromDict(baseDir, name, themeParams, bgParams)
    setNewswirePublishAsIcon(baseDir, True)
    setFullWidthTimelineButtonHeader(baseDir, False)
    setIconsAsButtons(baseDir, False)
    setRssIconAtTop(baseDir, True)
    setPublishButtonAtTop(baseDir, False)


def setThemeLCD(baseDir: str):
    name = 'lcd'
    themeParams = {
        "newswire-date-color": "#cfb42b",
        "column-left-header-background": "#9fb42b",
        "column-left-header-color": "#33390d",
        "main-bg-color": "#9fb42b",
        "column-left-color": "#33390d",
        "column-left-fg-color": "#9fb42b",
        "link-bg-color": "#33390d",
        "text-entry-foreground": "#33390d",
        "text-entry-background": "#9fb42b",
        "main-bg-color-reply": "#9fb42b",
        "main-bg-color-report": "#9fb42b",
        "main-bg-color-dm": "#5fb42b",
        "main-header-color-roles": "#9fb42b",
        "main-fg-color": "#33390d",
        "border-color": "#33390d",
        "border-width": "5px",
        "border-width-header": "5px",
        "main-link-color": "#9fb42b",
        "main-link-color-hover": "#cfb42b",
        "title-color": "#9fb42b",
        "main-visited-color": "#9fb42b",
        "button-selected": "black",
        "button-highlighted": "green",
        "button-background-hover": "#a3390d",
        "button-text-hover": "#33390d",
        "publish-button-background": "#33390d",
        "button-background": "#33390d",
        "button-small-background": "#33390d",
        "button-text": "#9fb42b",
        "button-selected-text": "#9fb42b",
        "publish-button-text": "#9fb42b",
        "button-small-text": "#9fb42b",
        "color: #FFFFFE;": "color: #9fb42b;",
        "calendar-bg-color": "#eee",
        "day-number": "#3f2145",
        "day-number2": "#9fb42b",
        "today-foreground": "white",
        "today-circle": "red",
        "event-background": "yellow",
        "event-foreground": "white",
        "title-text": "white",
        "gallery-text-color": "#33390d",
        "font-size-header": "22px",
        "font-size-header-mobile": "32px",
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
        "time-color": "#33390d",
        "place-color": "#33390d",
        "event-color": "#33390d",
        "*font-family": "'LcdSolid'",
        "*src": "url('./fonts/LcdSolid.woff2') format('woff2')"
    }
    bgParams = {
        "login": "jpg",
        "follow": "jpg",
        "options": "jpg",
        "search": "jpg"
    }
    setThemeFromDict(baseDir, name, themeParams, bgParams)
    setNewswirePublishAsIcon(baseDir, True)
    setFullWidthTimelineButtonHeader(baseDir, False)
    setIconsAsButtons(baseDir, False)
    setRssIconAtTop(baseDir, True)
    setPublishButtonAtTop(baseDir, False)


def setThemePurple(baseDir: str):
    name = 'purple'
    fontStr = \
        "url('./fonts/CheGuevaraTextSans-Regular.woff2') format('woff2')"
    themeParams = {
        "font-size-button-mobile": "26px",
        "font-size": "32px",
        "font-size2": "26px",
        "font-size3": "40px",
        "font-size4": "24px",
        "font-size5": "22px",
        "main-bg-color": "#1f152d",
        "column-left-color": "#1f152d",
        "link-bg-color": "#1f152d",
        "main-bg-color-reply": "#1a142d",
        "main-bg-color-report": "#12152d",
        "main-header-color-roles": "#1f192d",
        "main-fg-color": "#f98bb0",
        "column-left-fg-color": "#f98bb0",
        "border-color": "#3f2145",
        "main-link-color": "#ff42a0",
        "main-link-color-hover": "white",
        "title-color": "white",
        "main-visited-color": "#f93bb0",
        "button-selected": "#c042a0",
        "button-background-hover": "#af42a0",
        "button-text-hover": "#f98bb0",
        "publish-button-background": "#ff42a0",
        "button-background": "#ff42a0",
        "button-small-background": "#ff42a0",
        "button-text": "white",
        "button-selected-text": "white",
        "publish-button-text": "white",
        "button-small-text": "white",
        "color: #FFFFFE;": "color: #1f152d;",
        "calendar-bg-color": "#eee",
        "lines-color": "#ff42a0",
        "day-number": "#3f2145",
        "day-number2": "#1f152d",
        "today-foreground": "white",
        "today-circle": "red",
        "event-background": "yellow",
        "event-foreground": "white",
        "title-text": "white",
        "title-background": "#ff42a0",
        "gallery-text-color": "#ccc",
        "time-color": "#f98bb0",
        "place-color": "#f98bb0",
        "event-color": "#f98bb0",
        "*font-family": "'CheGuevaraTextSans-Regular'",
        "*src": fontStr
    }
    bgParams = {
        "login": "jpg",
        "follow": "jpg",
        "options": "jpg",
        "search": "jpg"
    }
    setThemeFromDict(baseDir, name, themeParams, bgParams)
    setNewswirePublishAsIcon(baseDir, True)
    setFullWidthTimelineButtonHeader(baseDir, False)
    setIconsAsButtons(baseDir, False)
    setRssIconAtTop(baseDir, True)
    setPublishButtonAtTop(baseDir, False)


def setThemeHacker(baseDir: str):
    name = 'hacker'
    themeParams = {
        "focus-color": "green",
        "main-bg-color": "black",
        "column-left-color": "black",
        "link-bg-color": "black",
        "main-bg-color-dm": "#0b0a0a",
        "main-bg-color-reply": "#030202",
        "main-bg-color-report": "#050202",
        "main-header-color-roles": "#1f192d",
        "main-fg-color": "#00ff00",
        "column-left-fg-color": "#00ff00",
        "border-color": "#035103",
        "main-link-color": "#2fff2f",
        "main-link-color-hover": "#afff2f",
        "title-color": "#2fff2f",
        "main-visited-color": "#3c8234",
        "button-selected": "#063200",
        "button-background-hover": "#a62200",
        "button-text-hover": "#00ff00",
        "publish-button-background": "#062200",
        "button-background": "#062200",
        "button-small-background": "#062200",
        "button-text": "#00ff00",
        "button-selected-text": "#00ff00",
        "publish-button-text": "#00ff00",
        "button-small-text": "#00ff00",
        "button-corner-radius": "4px",
        "timeline-border-radius": "4px",
        "*font-family": "'Bedstead'",
        "*src": "url('./fonts/bedstead.otf') format('opentype')",
        "color: #FFFFFE;": "color: green;",
        "calendar-bg-color": "black",
        "lines-color": "green",
        "day-number": "green",
        "day-number2": "darkgreen",
        "today-foreground": "white",
        "today-circle": "red",
        "event-background": "lightgreen",
        "event-foreground": "black",
        "title-text": "black",
        "title-background": "darkgreen",
        "gallery-text-color": "green",
        "time-color": "#00ff00",
        "place-color": "#00ff00",
        "event-color": "#00ff00",
        "image-corners": "0%"
    }
    bgParams = {
        "login": "jpg",
        "follow": "jpg",
        "options": "jpg",
        "search": "jpg"
    }
    setThemeFromDict(baseDir, name, themeParams, bgParams)
    setNewswirePublishAsIcon(baseDir, True)
    setFullWidthTimelineButtonHeader(baseDir, False)
    setIconsAsButtons(baseDir, False)
    setRssIconAtTop(baseDir, True)
    setPublishButtonAtTop(baseDir, False)


def setThemeLight(baseDir: str):
    name = 'light'
    themeParams = {
        "banner-height": "20vh",
        "banner-height-mobile": "10vh",
        "hashtag-background-color": "lightblue",
        "focus-color": "grey",
        "font-size-button-mobile": "26px",
        "font-size": "32px",
        "font-size2": "26px",
        "font-size3": "40px",
        "font-size4": "24px",
        "font-size5": "22px",
        "rgba(0, 0, 0, 0.5)": "rgba(0, 0, 0, 0.0)",
        "column-left-color": "#e6ebf0",
        "main-bg-color": "#e6ebf0",
        "main-bg-color-dm": "#e3dbf0",
        "link-bg-color": "#e6ebf0",
        "main-bg-color-reply": "#e0dbf0",
        "main-bg-color-report": "#e3dbf0",
        "main-header-color-roles": "#ebebf0",
        "main-fg-color": "#2d2c37",
        "column-left-fg-color": "#2d2c37",
        "border-color": "#c0cdd9",
        "main-link-color": "#2a2c37",
        "main-link-color-hover": "#aa2c37",
        "title-color": "#2a2c37",
        "main-visited-color": "#232c37",
        "text-entry-foreground": "#111",
        "text-entry-background": "white",
        "font-color-header": "black",
        "dropdown-fg-color": "#222",
        "dropdown-fg-color-hover": "#222",
        "dropdown-bg-color": "white",
        "dropdown-bg-color-hover": "lightgrey",
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
    bgParams = {
        "login": "jpg",
        "follow": "jpg",
        "options": "jpg",
        "search": "jpg"
    }
    setThemeFromDict(baseDir, name, themeParams, bgParams)
    setNewswirePublishAsIcon(baseDir, True)
    setFullWidthTimelineButtonHeader(baseDir, False)
    setIconsAsButtons(baseDir, False)
    setRssIconAtTop(baseDir, True)
    setPublishButtonAtTop(baseDir, False)


def setThemeIndymediaModern(baseDir: str):
    name = 'indymediamodern'
    fontStr = \
        "url('./fonts/NimbusSanL.otf') format('opentype')"
    fontStrItalic = \
        "url('./fonts/NimbusSanL-italic.otf') format('opentype')"
    themeParams = {
        "follow-text-size1": "14px",
        "follow-text-size2": "30px",
        "hashtag-size1": "20px",
        "hashtag-size2": "30px",
        "font-size-calendar-header": "2rem",
        "font-size-calendar-cell": "2rem",
        "calendar-horizontal-padding": "20%",
        "time-vertical-align": "10px",
        "header-vertical-offset": "-10%",
        "publish-button-vertical-offset": "0",
        "vertical-between-posts-header": "0 0",
        "header-button-padding": "0 0",
        "containericons-horizontal-spacing": "0%",
        "font-size-header": "14px",
        "font-size": "22px",
        "font-size2": "16px",
        "font-size3": "30px",
        "font-size4": "14px",
        "font-size5": "12px",
        "font-size-likes": "10px",
        "font-size-links": "12px",
        "font-size-newswire": "12px",
        "font-size-newswire-mobile": "30px",
        "font-size-dropdown-header": "30px",
        "post-separator-margin-top": "1%",
        "post-separator-margin-bottom": "1%",
        "post-separator-width": "95%",
        "post-separator-height": "1px",
        "column-left-border-width": "1px",
        "column-right-border-width": "0px",
        "column-left-border-color": "black",
        "column-left-header-color": "black",
        "column-left-header-background": "white",
        "column-left-header-style": "none",
        "search-banner-height": "15vh",
        "search-banner-height-mobile": "10vh",
        "container-button-padding": "0px",
        "container-button-margin": "0px",
        "column-left-icon-size": "15%",
        "column-right-icon-size": "15%",
        "button-height-padding": "5px",
        "icon-brightness-change": "70%",
        "border-width": "0px",
        "border-width-header": "0px",
        "tab-border-width": "3px",
        "tab-border-color": "grey",
        "button-corner-radius": "0px",
        "login-button-color": "#25408f",
        "login-button-fg-color": "white",
        "column-left-width": "10vw",
        "column-center-width": "80vw",
        "column-right-width": "10vw",
        "column-right-fg-color": "#25408f",
        "column-right-fg-color-voted-on": "red",
        "newswire-item-moderated-color": "red",
        "newswire-date-moderated-color": "red",
        "newswire-date-color": "grey",
        "timeline-border-radius": "0px",
        "button-background": "#767674",
        "button-background-hover": "#555",
        "button-text-hover": "white",
        "button-selected": "white",
        "button-selected-text": "black",
        "button-text": "white",
        "hashtag-fg-color": "white",
        "publish-button-background": "#25408f",
        "publish-button-text": "white",
        "hashtag-background-color": "#b2b2b2",
        "focus-color": "grey",
        "font-size-button-mobile": "26px",
        "font-size-publish-button": "14px",
        "rgba(0, 0, 0, 0.5)": "rgba(0, 0, 0, 0.0)",
        "column-left-color": "white",
        "main-bg-color": "white",
        "main-bg-color-dm": "white",
        "link-bg-color": "white",
        "main-bg-color-reply": "white",
        "main-bg-color-report": "white",
        "main-header-color-roles": "#ebebf0",
        "main-fg-color": "black",
        "column-left-fg-color": "#25408f",
        "border-color": "#c0cdd9",
        "main-link-color": "#25408f",
        "main-link-color-hover": "#10408f",
        "title-color": "#2a2c37",
        "main-visited-color": "#25408f",
        "text-entry-foreground": "#111",
        "text-entry-background": "white",
        "font-color-header": "black",
        "dropdown-fg-color": "#222",
        "dropdown-fg-color-hover": "#222",
        "dropdown-bg-color": "#e6ebf0",
        "dropdown-bg-color-hover": "lightblue",
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
        "*font-family": "'NimbusSanL'",
        "*src": fontStr,
        "**src": fontStrItalic
    }
    bgParams = {
        "login": "jpg",
        "follow": "jpg",
        "options": "jpg",
        "search": "jpg"
    }
    setThemeFromDict(baseDir, name, themeParams, bgParams)
    setNewswirePublishAsIcon(baseDir, False)
    setFullWidthTimelineButtonHeader(baseDir, False)
    setIconsAsButtons(baseDir, True)
    setRssIconAtTop(baseDir, False)
    setPublishButtonAtTop(baseDir, True)


def setThemeSolidaric(baseDir: str):
    name = 'solidaric'
    themeParams = {
        "font-size-pgp-key2": "18px",
        "button-corner-radius": "5px",
        "column-left-icons-margin": "15px",
        "post-separator-width": "96.5%",
        "post-separator-height": "40px",
        "border-width-header": "0",
        "border-width": "0",
        "banner-height": "35vh",
        "banner-height-mobile": "15vh",
        "search-banner-height-mobile": "15vh",
        "time-vertical-align": "-4px",
        "time-vertical-align-mobile": "15px",
        "hashtag-background-color": "lightred",
        "button-highlighted": "darkred",
        "button-selected-highlighted": "darkred",
        "newswire-date-color": "grey",
        "focus-color": "grey",
        "font-size-button-mobile": "26px",
        "font-size": "32px",
        "font-size2": "26px",
        "font-size3": "40px",
        "font-size4": "24px",
        "font-size5": "22px",
        "rgba(0, 0, 0, 0.5)": "rgba(0, 0, 0, 0.0)",
        "main-bg-color": "white",
        "column-left-color": "white",
        "main-bg-color-dm": "white",
        "link-bg-color": "white",
        "main-bg-color-reply": "white",
        "main-bg-color-report": "white",
        "main-header-color-roles": "#ebebf0",
        "main-fg-color": "#2d2c37",
        "column-left-fg-color": "#2d2c37",
        "border-color": "#c0cdd9",
        "main-link-color": "#2a2c37",
        "main-link-color-hover": "#aa2c37",
        "title-color": "#2a2c37",
        "main-visited-color": "#232c37",
        "text-entry-foreground": "#111",
        "text-entry-background": "white",
        "font-color-header": "black",
        "dropdown-fg-color": "#222",
        "dropdown-fg-color-hover": "#222",
        "dropdown-bg-color": "white",
        "dropdown-bg-color-hover": "lightgrey",
        "color: #FFFFFE;": "color: black;",
        "calendar-bg-color": "white",
        "lines-color": "black",
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
        "quote-right-margin": "0",
        "line-spacing": "150%",
        "*font-family": "'solidaric'",
        "*src": "url('./fonts/solidaric.woff2') format('woff2')",
        "**src": "url('./fonts/solidaric-italic.woff2') format('woff2')"
    }
    bgParams = {
        "login": "jpg",
        "follow": "jpg",
        "options": "jpg",
        "search": "jpg"
    }
    setThemeFromDict(baseDir, name, themeParams, bgParams)
    setNewswirePublishAsIcon(baseDir, True)
    setFullWidthTimelineButtonHeader(baseDir, False)
    setIconsAsButtons(baseDir, False)
    setRssIconAtTop(baseDir, True)
    setPublishButtonAtTop(baseDir, False)


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
        leftColImageFilename = \
            baseDir + '/img/left_col_image.png'
        rightColImageFilename = \
            baseDir + '/img/right_col_image.png'
    else:
        profileImageFilename = \
            baseDir + '/img/image_' + themeNameLower + '.png'
        bannerFilename = \
            baseDir + '/img/banner_' + themeNameLower + '.png'
        searchBannerFilename = \
            baseDir + '/img/search_banner_' + themeNameLower + '.png'
        leftColImageFilename = \
            baseDir + '/img/left_col_image_' + themeNameLower + '.png'
        rightColImageFilename = \
            baseDir + '/img/right_col_image_' + themeNameLower + '.png'

    backgroundNames = ('login', 'shares', 'delete', 'follow',
                       'options', 'block', 'search', 'calendar')
    extensions = ('webp', 'gif', 'jpg', 'png', 'avif')

    for subdir, dirs, files in os.walk(baseDir + '/accounts'):
        for acct in dirs:
            if '@' not in acct:
                continue
            if 'inbox@' in acct:
                continue
            accountDir = \
                os.path.join(baseDir + '/accounts', acct)

            for backgroundType in backgroundNames:
                for ext in extensions:
                    if themeNameLower == 'default':
                        backgroundImageFilename = \
                            baseDir + '/img/' + backgroundType + \
                            '-background.' + ext
                    else:
                        backgroundImageFilename = \
                            baseDir + '/img/' + backgroundType + \
                            '_background_' + themeNameLower + '.' + ext

                    if os.path.isfile(backgroundImageFilename):
                        try:
                            copyfile(backgroundImageFilename,
                                     baseDir + '/accounts/' + backgroundType +
                                     '-background.' + ext)
                            continue
                        except BaseException:
                            pass
                    # background image was not found
                    # so remove any existing file
                    if os.path.isfile(baseDir + '/accounts/' +
                                      backgroundType +
                                      '-background.' + ext):
                        try:
                            os.remove(baseDir + '/accounts/' +
                                      backgroundType +
                                      '-background.' + ext)
                        except BaseException:
                            pass

            if os.path.isfile(profileImageFilename) and \
               os.path.isfile(bannerFilename):
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

                try:
                    if os.path.isfile(leftColImageFilename):
                        copyfile(leftColImageFilename,
                                 accountDir + '/left_col_image.png')
                    else:
                        if os.path.isfile(accountDir +
                                          '/left_col_image.png'):
                            os.remove(accountDir + '/left_col_image.png')

                except BaseException:
                    pass

                try:
                    if os.path.isfile(rightColImageFilename):
                        copyfile(rightColImageFilename,
                                 accountDir + '/right_col_image.png')
                    else:
                        if os.path.isfile(accountDir +
                                          '/right_col_image.png'):
                            os.remove(accountDir + '/right_col_image.png')
                except BaseException:
                    pass


def setNewsAvatar(baseDir: str, name: str,
                  httpPrefix: str,
                  domain: str, domainFull: str) -> None:
    """Sets the avatar for the news account
    """
    nickname = 'news'
    newFilename = baseDir + '/img/icons/' + name + '/avatar_news.png'
    if not os.path.isfile(newFilename):
        newFilename = baseDir + '/img/icons/avatar_news.png'
    if not os.path.isfile(newFilename):
        return
    avatarFilename = \
        httpPrefix + '://' + domainFull + '/users/' + nickname + '.png'
    avatarFilename = avatarFilename.replace('/', '-')
    filename = baseDir + '/cache/avatars/' + avatarFilename

    if os.path.isfile(filename):
        os.remove(filename)
    if os.path.isdir(baseDir + '/cache/avatars'):
        copyfile(newFilename, filename)
    copyfile(newFilename,
             baseDir + '/accounts/' +
             nickname + '@' + domain + '/avatar.png')


def setTheme(baseDir: str, name: str, domain: str) -> bool:
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

    # set the news avatar
    newsAvatarThemeFilename = \
        baseDir + '/img/icons/' + name + '/avatar_news.png'
    if os.path.isfile(newsAvatarThemeFilename):
        newsAvatarFilename = \
            baseDir + '/accounts/news@' + domain + '/avatar.png'
        copyfile(newsAvatarThemeFilename, newsAvatarFilename)

    grayscaleFilename = baseDir + '/accounts/.grayscale'
    if os.path.isfile(grayscaleFilename):
        enableGrayscale(baseDir)
    else:
        disableGrayscale(baseDir)
    return result
