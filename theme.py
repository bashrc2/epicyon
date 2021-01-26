__filename__ = "theme.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
from utils import loadJson
from utils import saveJson
from utils import getImageExtensions
from shutil import copyfile
from content import dangerousCSS


def _getThemeFiles() -> []:
    return ('epicyon.css', 'login.css', 'follow.css',
            'suspended.css', 'calendar.css', 'blog.css',
            'options.css', 'search.css', 'links.css')


def getThemesList(baseDir: str) -> []:
    """Returns the list of available themes
    Note that these should be capitalized, since they're
    also used to create the web interface dropdown list
    and to lookup function names
    """
    themes = []
    for subdir, dirs, files in os.walk(baseDir + '/theme'):
        for themeName in dirs:
            if '~' not in themeName and \
               themeName != 'icons' and themeName != 'fonts':
                themes.append(themeName.title())
        break
    themes.sort()
    print('Themes available: ' + str(themes))
    return themes


def _setThemeInConfig(baseDir: str, name: str) -> bool:
    configFilename = baseDir + '/config.json'
    if not os.path.isfile(configFilename):
        return False
    configJson = loadJson(configFilename, 0)
    if not configJson:
        return False
    configJson['theme'] = name
    return saveJson(configJson, configFilename)


def _setNewswirePublishAsIcon(baseDir: str, useIcon: bool) -> bool:
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


def _setIconsAsButtons(baseDir: str, useButtons: bool) -> bool:
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


def _setRssIconAtTop(baseDir: str, atTop: bool) -> bool:
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


def _setPublishButtonAtTop(baseDir: str, atTop: bool) -> bool:
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


def _setFullWidthTimelineButtonHeader(baseDir: str, fullWidth: bool) -> bool:
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


def _removeTheme(baseDir: str):
    themeFiles = _getThemeFiles()
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
        # handle font-family which is a variable
        nextSection = sectionStr
        if ';' in nextSection:
            nextSection = nextSection.split(';')[0] + ';'
        if searchStr == 'font-family:' and "var(--" in nextSection:
            newcss += searchStr + ' ' + sectionStr
            continue

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


def _setThemeFromDict(baseDir: str, name: str,
                      themeParams: {}, bgParams: {},
                      allowLocalNetworkAccess: bool) -> None:
    """Uses a dictionary to set a theme
    """
    if name:
        _setThemeInConfig(baseDir, name)
    themeFiles = _getThemeFiles()
    for filename in themeFiles:
        # check for custom css within the theme directory
        templateFilename = baseDir + '/theme/' + name + '/epicyon-' + filename
        if filename == 'epicyon.css':
            templateFilename = \
                baseDir + '/theme/' + name + '/epicyon-profile.css'

        # Ensure that any custom CSS is mostly harmless.
        # If not then just use the defaults
        if dangerousCSS(templateFilename, allowLocalNetworkAccess) or \
           not os.path.isfile(templateFilename):
            # use default css
            templateFilename = baseDir + '/epicyon-' + filename
            if filename == 'epicyon.css':
                templateFilename = baseDir + '/epicyon-profile.css'

        if not os.path.isfile(templateFilename):
            continue

        with open(templateFilename, 'r') as cssfile:
            css = cssfile.read()
            for paramName, paramValue in themeParams.items():
                if paramName == 'newswire-publish-icon':
                    if paramValue.lower() == 'true':
                        _setNewswirePublishAsIcon(baseDir, True)
                    else:
                        _setNewswirePublishAsIcon(baseDir, False)
                    continue
                elif paramName == 'full-width-timeline-buttons':
                    if paramValue.lower() == 'true':
                        _setFullWidthTimelineButtonHeader(baseDir, True)
                    else:
                        _setFullWidthTimelineButtonHeader(baseDir, False)
                    continue
                elif paramName == 'icons-as-buttons':
                    if paramValue.lower() == 'true':
                        _setIconsAsButtons(baseDir, True)
                    else:
                        _setIconsAsButtons(baseDir, False)
                    continue
                elif paramName == 'rss-icon-at-top':
                    if paramValue.lower() == 'true':
                        _setRssIconAtTop(baseDir, True)
                    else:
                        _setRssIconAtTop(baseDir, False)
                    continue
                elif paramName == 'publish-button-at-top':
                    if paramValue.lower() == 'true':
                        _setPublishButtonAtTop(baseDir, True)
                    else:
                        _setPublishButtonAtTop(baseDir, False)
                    continue
                css = setCSSparam(css, paramName, paramValue)
            filename = baseDir + '/' + filename
            with open(filename, 'w+') as cssfile:
                cssfile.write(css)

    if bgParams.get('login'):
        _setBackgroundFormat(baseDir, name, 'login', bgParams['login'])
    if bgParams.get('follow'):
        _setBackgroundFormat(baseDir, name, 'follow', bgParams['follow'])
    if bgParams.get('options'):
        _setBackgroundFormat(baseDir, name, 'options', bgParams['options'])
    if bgParams.get('search'):
        _setBackgroundFormat(baseDir, name, 'search', bgParams['search'])


def _setBackgroundFormat(baseDir: str, name: str,
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
    themeFiles = _getThemeFiles()
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
    themeFiles = _getThemeFiles()
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


def _setCustomFont(baseDir: str):
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

    themeFiles = _getThemeFiles()
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


def _readVariablesFile(baseDir: str, themeName: str,
                       variablesFile: str,
                       allowLocalNetworkAccess: bool) -> None:
    """Reads variables from a file in the theme directory
    """
    themeParams = loadJson(variablesFile, 0)
    if not themeParams:
        return
    bgParams = {
        "login": "jpg",
        "follow": "jpg",
        "options": "jpg",
        "search": "jpg"
    }
    _setThemeFromDict(baseDir, themeName, themeParams, bgParams,
                      allowLocalNetworkAccess)


def _setThemeDefault(baseDir: str, allowLocalNetworkAccess: bool):
    name = 'default'
    _removeTheme(baseDir)
    _setThemeInConfig(baseDir, name)
    bgParams = {
        "login": "jpg",
        "follow": "jpg",
        "options": "jpg",
        "search": "jpg"
    }
    themeParams = {
        "newswire-publish-icon": True,
        "full-width-timeline-buttons": False,
        "icons-as-buttons": False,
        "rss-icon-at-top": True,
        "publish-button-at-top": False,
        "banner-height": "20vh",
        "banner-height-mobile": "10vh",
        "search-banner-height-mobile": "15vh"
    }
    _setThemeFromDict(baseDir, name, themeParams, bgParams,
                      allowLocalNetworkAccess)


def _setThemeFonts(baseDir: str, themeName: str) -> None:
    """Adds custom theme fonts
    """
    themeNameLower = themeName.lower()
    fontsDir = baseDir + '/fonts'
    themeFontsDir = \
        baseDir + '/theme/' + themeNameLower + '/fonts'
    if not os.path.isdir(themeFontsDir):
        return
    for subdir, dirs, files in os.walk(themeFontsDir):
        for filename in files:
            if filename.endswith('.woff2') or \
               filename.endswith('.woff') or \
               filename.endswith('.ttf') or \
               filename.endswith('.otf'):
                destFilename = fontsDir + '/' + filename
                if os.path.isfile(destFilename):
                    # font already exists in the destination location
                    continue
                copyfile(themeFontsDir + '/' + filename,
                         destFilename)
        break


def _setThemeImages(baseDir: str, name: str) -> None:
    """Changes the profile background image
    and banner to the defaults
    """
    themeNameLower = name.lower()

    profileImageFilename = \
        baseDir + '/theme/' + themeNameLower + '/image.png'
    bannerFilename = \
        baseDir + '/theme/' + themeNameLower + '/banner.png'
    searchBannerFilename = \
        baseDir + '/theme/' + themeNameLower + '/search_banner.png'
    leftColImageFilename = \
        baseDir + '/theme/' + themeNameLower + '/left_col_image.png'
    rightColImageFilename = \
        baseDir + '/theme/' + themeNameLower + '/right_col_image.png'

    backgroundNames = ('login', 'shares', 'delete', 'follow',
                       'options', 'block', 'search', 'calendar')
    extensions = getImageExtensions()

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
                            baseDir + '/theme/default/' + \
                            backgroundType + '_background.' + ext
                    else:
                        backgroundImageFilename = \
                            baseDir + '/theme/' + themeNameLower + '/' + \
                            backgroundType + '_background' + '.' + ext

                    if os.path.isfile(backgroundImageFilename):
                        try:
                            copyfile(backgroundImageFilename,
                                     baseDir + '/accounts/' +
                                     backgroundType + '-background.' + ext)
                            continue
                        except BaseException:
                            pass
                    # background image was not found
                    # so remove any existing file
                    if os.path.isfile(baseDir + '/accounts/' +
                                      backgroundType + '-background.' + ext):
                        try:
                            os.remove(baseDir + '/accounts/' +
                                      backgroundType + '-background.' + ext)
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
        break


def setNewsAvatar(baseDir: str, name: str,
                  httpPrefix: str,
                  domain: str, domainFull: str) -> None:
    """Sets the avatar for the news account
    """
    nickname = 'news'
    newFilename = baseDir + '/theme/' + name + '/icons/avatar_news.png'
    if not os.path.isfile(newFilename):
        newFilename = baseDir + '/theme/default/icons/avatar_news.png'
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


def setTheme(baseDir: str, name: str, domain: str,
             allowLocalNetworkAccess: bool) -> bool:
    result = False

    prevThemeName = getTheme(baseDir)
    _removeTheme(baseDir)

    themes = getThemesList(baseDir)
    for themeName in themes:
        themeNameLower = themeName.lower()
        if name == themeNameLower:
            try:
                globals()['setTheme' + themeName](baseDir,
                                                  allowLocalNetworkAccess)
            except BaseException:
                pass

            if prevThemeName:
                if prevThemeName.lower() != themeNameLower:
                    # change the banner and profile image
                    # to the default for the theme
                    _setThemeImages(baseDir, name)
                    _setThemeFonts(baseDir, name)
            result = True

    if not result:
        # default
        _setThemeDefault(baseDir, allowLocalNetworkAccess)
        result = True

    variablesFile = baseDir + '/theme/' + name + '/theme.json'
    if os.path.isfile(variablesFile):
        _readVariablesFile(baseDir, name, variablesFile,
                           allowLocalNetworkAccess)

    _setCustomFont(baseDir)

    # set the news avatar
    newsAvatarThemeFilename = \
        baseDir + '/theme/' + name + '/icons/avatar_news.png'
    if os.path.isdir(baseDir + '/accounts/news@' + domain):
        if os.path.isfile(newsAvatarThemeFilename):
            newsAvatarFilename = \
                baseDir + '/accounts/news@' + domain + '/avatar.png'
            copyfile(newsAvatarThemeFilename, newsAvatarFilename)

    grayscaleFilename = baseDir + '/accounts/.grayscale'
    if os.path.isfile(grayscaleFilename):
        enableGrayscale(baseDir)
    else:
        disableGrayscale(baseDir)

    _setThemeInConfig(baseDir, name)
    return result
