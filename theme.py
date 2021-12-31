__filename__ = "theme.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Web Interface"

import os
from utils import is_account_dir
from utils import load_json
from utils import save_json
from utils import get_image_extensions
from utils import copytree
from utils import acct_dir
from utils import dangerous_svg
from utils import local_actor_url
from shutil import copyfile
from shutil import make_archive
from shutil import unpack_archive
from shutil import rmtree
from content import dangerous_css


def import_theme(base_dir: str, filename: str) -> bool:
    """Imports a theme
    """
    if not os.path.isfile(filename):
        return False
    tempThemeDir = base_dir + '/imports/files'
    if os.path.isdir(tempThemeDir):
        rmtree(tempThemeDir, ignore_errors=False, onerror=None)
    os.mkdir(tempThemeDir)
    unpack_archive(filename, tempThemeDir, 'zip')
    essentialThemeFiles = ('name.txt', 'theme.json')
    for themeFile in essentialThemeFiles:
        if not os.path.isfile(tempThemeDir + '/' + themeFile):
            print('WARN: ' + themeFile +
                  ' missing from imported theme')
            return False
    newThemeName = None
    with open(tempThemeDir + '/name.txt', 'r') as fp:
        newThemeName = fp.read().replace('\n', '').replace('\r', '')
        if len(newThemeName) > 20:
            print('WARN: Imported theme name is too long')
            return False
        if len(newThemeName) < 2:
            print('WARN: Imported theme name is too short')
            return False
        newThemeName = newThemeName.lower()
        forbiddenChars = (
            ' ', ';', '/', '\\', '?', '!', '#', '@',
            ':', '%', '&', '"', '+', '<', '>', '$'
        )
        for ch in forbiddenChars:
            if ch in newThemeName:
                print('WARN: theme name contains forbidden character')
                return False
    if not newThemeName:
        return False

    # if the theme name in the default themes list?
    defaultThemesFilename = base_dir + '/defaultthemes.txt'
    if os.path.isfile(defaultThemesFilename):
        if newThemeName.title() + '\n' in open(defaultThemesFilename).read():
            newThemeName = newThemeName + '2'

    themeDir = base_dir + '/theme/' + newThemeName
    if not os.path.isdir(themeDir):
        os.mkdir(themeDir)
    copytree(tempThemeDir, themeDir)
    if os.path.isdir(tempThemeDir):
        rmtree(tempThemeDir, ignore_errors=False, onerror=None)
    if scan_themes_for_scripts(themeDir):
        rmtree(themeDir, ignore_errors=False, onerror=None)
        return False
    return os.path.isfile(themeDir + '/theme.json')


def export_theme(base_dir: str, theme: str) -> bool:
    """Exports a theme as a zip file
    """
    themeDir = base_dir + '/theme/' + theme
    if not os.path.isfile(themeDir + '/theme.json'):
        return False
    if not os.path.isdir(base_dir + '/exports'):
        os.mkdir(base_dir + '/exports')
    exportFilename = base_dir + '/exports/' + theme + '.zip'
    if os.path.isfile(exportFilename):
        try:
            os.remove(exportFilename)
        except OSError:
            print('EX: export_theme unable to delete ' + str(exportFilename))
    try:
        make_archive(base_dir + '/exports/' + theme, 'zip', themeDir)
    except BaseException:
        print('EX: export_theme unable to archive ' +
              base_dir + '/exports/' + str(theme))
        pass
    return os.path.isfile(exportFilename)


def _get_theme_files() -> []:
    """Gets the list of theme style sheets
    """
    return ('epicyon.css', 'login.css', 'follow.css',
            'suspended.css', 'calendar.css', 'blog.css',
            'options.css', 'search.css', 'links.css',
            'welcome.css', 'graph.css')


def is_news_theme_name(base_dir: str, theme_name: str) -> bool:
    """Returns true if the given theme is a news instance
    """
    themeDir = base_dir + '/theme/' + theme_name
    if os.path.isfile(themeDir + '/is_news_instance'):
        return True
    return False


def get_themes_list(base_dir: str) -> []:
    """Returns the list of available themes
    Note that these should be capitalized, since they're
    also used to create the web interface dropdown list
    and to lookup function names
    """
    themes = []
    for subdir, dirs, files in os.walk(base_dir + '/theme'):
        for theme_name in dirs:
            if '~' not in theme_name and \
               theme_name != 'icons' and theme_name != 'fonts':
                themes.append(theme_name.title())
        break
    themes.sort()
    print('Themes available: ' + str(themes))
    return themes


def _copy_theme_help_files(base_dir: str, theme_name: str,
                           system_language: str) -> None:
    """Copies any theme specific help files from the welcome subdirectory
    """
    if not system_language:
        system_language = 'en'
    themeDir = base_dir + '/theme/' + theme_name + '/welcome'
    if not os.path.isdir(themeDir):
        themeDir = base_dir + '/defaultwelcome'
    for subdir, dirs, files in os.walk(themeDir):
        for helpMarkdownFile in files:
            if not helpMarkdownFile.endswith('_' + system_language + '.md'):
                continue
            destHelpMarkdownFile = \
                helpMarkdownFile.replace('_' + system_language + '.md', '.md')
            if destHelpMarkdownFile == 'profile.md' or \
               destHelpMarkdownFile == 'final.md':
                destHelpMarkdownFile = 'welcome_' + destHelpMarkdownFile
            if os.path.isdir(base_dir + '/accounts'):
                copyfile(themeDir + '/' + helpMarkdownFile,
                         base_dir + '/accounts/' + destHelpMarkdownFile)
        break


def _set_theme_in_config(base_dir: str, name: str) -> bool:
    """Sets the theme with the given name within config.json
    """
    config_filename = base_dir + '/config.json'
    if not os.path.isfile(config_filename):
        return False
    configJson = load_json(config_filename, 0)
    if not configJson:
        return False
    configJson['theme'] = name
    return save_json(configJson, config_filename)


def _set_newswire_publish_as_icon(base_dir: str, useIcon: bool) -> bool:
    """Shows the newswire publish action as an icon or a button
    """
    config_filename = base_dir + '/config.json'
    if not os.path.isfile(config_filename):
        return False
    configJson = load_json(config_filename, 0)
    if not configJson:
        return False
    configJson['show_publish_as_icon'] = useIcon
    return save_json(configJson, config_filename)


def _set_icons_as_buttons(base_dir: str, useButtons: bool) -> bool:
    """Whether to show icons in the header (inbox, outbox, etc)
    as buttons
    """
    config_filename = base_dir + '/config.json'
    if not os.path.isfile(config_filename):
        return False
    configJson = load_json(config_filename, 0)
    if not configJson:
        return False
    configJson['icons_as_buttons'] = useButtons
    return save_json(configJson, config_filename)


def _set_rss_icon_at_top(base_dir: str, atTop: bool) -> bool:
    """Whether to show RSS icon at the top of the timeline
    """
    config_filename = base_dir + '/config.json'
    if not os.path.isfile(config_filename):
        return False
    configJson = load_json(config_filename, 0)
    if not configJson:
        return False
    configJson['rss_icon_at_top'] = atTop
    return save_json(configJson, config_filename)


def _set_publish_button_at_top(base_dir: str, atTop: bool) -> bool:
    """Whether to show the publish button above the title image
    in the newswire column
    """
    config_filename = base_dir + '/config.json'
    if not os.path.isfile(config_filename):
        return False
    configJson = load_json(config_filename, 0)
    if not configJson:
        return False
    configJson['publish_button_at_top'] = atTop
    return save_json(configJson, config_filename)


def _set_full_width_timeline_button_header(base_dir: str,
                                           fullWidth: bool) -> bool:
    """Shows the timeline button header containing inbox, outbox,
    calendar, etc as full width
    """
    config_filename = base_dir + '/config.json'
    if not os.path.isfile(config_filename):
        return False
    configJson = load_json(config_filename, 0)
    if not configJson:
        return False
    configJson['full_width_tl_button_header'] = fullWidth
    return save_json(configJson, config_filename)


def get_theme(base_dir: str) -> str:
    """Gets the current theme name from config.json
    """
    config_filename = base_dir + '/config.json'
    if os.path.isfile(config_filename):
        configJson = load_json(config_filename, 0)
        if configJson:
            if configJson.get('theme'):
                return configJson['theme']
    return 'default'


def _remove_theme(base_dir: str):
    """Removes the current theme style sheets
    """
    themeFiles = _get_theme_files()
    for filename in themeFiles:
        if not os.path.isfile(base_dir + '/' + filename):
            continue
        try:
            os.remove(base_dir + '/' + filename)
        except OSError:
            print('EX: _remove_theme unable to delete ' +
                  base_dir + '/' + filename)


def set_cs_sparam(css: str, param: str, value: str) -> str:
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


def _set_theme_from_dict(base_dir: str, name: str,
                         themeParams: {}, bgParams: {},
                         allow_local_network_access: bool) -> None:
    """Uses a dictionary to set a theme
    """
    if name:
        _set_theme_in_config(base_dir, name)
    themeFiles = _get_theme_files()
    for filename in themeFiles:
        # check for custom css within the theme directory
        templateFilename = base_dir + '/theme/' + name + '/epicyon-' + filename
        if filename == 'epicyon.css':
            templateFilename = \
                base_dir + '/theme/' + name + '/epicyon-profile.css'

        # Ensure that any custom CSS is mostly harmless.
        # If not then just use the defaults
        if dangerous_css(templateFilename, allow_local_network_access) or \
           not os.path.isfile(templateFilename):
            # use default css
            templateFilename = base_dir + '/epicyon-' + filename
            if filename == 'epicyon.css':
                templateFilename = base_dir + '/epicyon-profile.css'

        if not os.path.isfile(templateFilename):
            continue

        with open(templateFilename, 'r') as cssfile:
            css = cssfile.read()
            for paramName, paramValue in themeParams.items():
                if paramName == 'newswire-publish-icon':
                    if paramValue.lower() == 'true':
                        _set_newswire_publish_as_icon(base_dir, True)
                    else:
                        _set_newswire_publish_as_icon(base_dir, False)
                    continue
                elif paramName == 'full-width-timeline-buttons':
                    if paramValue.lower() == 'true':
                        _set_full_width_timeline_button_header(base_dir, True)
                    else:
                        _set_full_width_timeline_button_header(base_dir, False)
                    continue
                elif paramName == 'icons-as-buttons':
                    if paramValue.lower() == 'true':
                        _set_icons_as_buttons(base_dir, True)
                    else:
                        _set_icons_as_buttons(base_dir, False)
                    continue
                elif paramName == 'rss-icon-at-top':
                    if paramValue.lower() == 'true':
                        _set_rss_icon_at_top(base_dir, True)
                    else:
                        _set_rss_icon_at_top(base_dir, False)
                    continue
                elif paramName == 'publish-button-at-top':
                    if paramValue.lower() == 'true':
                        _set_publish_button_at_top(base_dir, True)
                    else:
                        _set_publish_button_at_top(base_dir, False)
                    continue
                css = set_cs_sparam(css, paramName, paramValue)
            filename = base_dir + '/' + filename
            with open(filename, 'w+') as cssfile:
                cssfile.write(css)

    screenName = (
        'login', 'follow', 'options', 'search', 'welcome'
    )
    for s in screenName:
        if bgParams.get(s):
            _set_background_format(base_dir, name, s, bgParams[s])


def _set_background_format(base_dir: str, name: str,
                           backgroundType: str, extension: str) -> None:
    """Sets the background file extension
    """
    if extension == 'jpg':
        return
    css_filename = base_dir + '/' + backgroundType + '.css'
    if not os.path.isfile(css_filename):
        return
    with open(css_filename, 'r') as cssfile:
        css = cssfile.read()
        css = css.replace('background.jpg', 'background.' + extension)
        with open(css_filename, 'w+') as cssfile2:
            cssfile2.write(css)


def enable_grayscale(base_dir: str) -> None:
    """Enables grayscale for the current theme
    """
    themeFiles = _get_theme_files()
    for filename in themeFiles:
        templateFilename = base_dir + '/' + filename
        if not os.path.isfile(templateFilename):
            continue
        with open(templateFilename, 'r') as cssfile:
            css = cssfile.read()
            if 'grayscale' not in css:
                css = \
                    css.replace('body, html {',
                                'body, html {\n    filter: grayscale(100%);')
                filename = base_dir + '/' + filename
                with open(filename, 'w+') as cssfile:
                    cssfile.write(css)
    grayscaleFilename = base_dir + '/accounts/.grayscale'
    if not os.path.isfile(grayscaleFilename):
        with open(grayscaleFilename, 'w+') as grayfile:
            grayfile.write(' ')


def disable_grayscale(base_dir: str) -> None:
    """Disables grayscale for the current theme
    """
    themeFiles = _get_theme_files()
    for filename in themeFiles:
        templateFilename = base_dir + '/' + filename
        if not os.path.isfile(templateFilename):
            continue
        with open(templateFilename, 'r') as cssfile:
            css = cssfile.read()
            if 'grayscale' in css:
                css = \
                    css.replace('\n    filter: grayscale(100%);', '')
                filename = base_dir + '/' + filename
                with open(filename, 'w+') as cssfile:
                    cssfile.write(css)
    grayscaleFilename = base_dir + '/accounts/.grayscale'
    if os.path.isfile(grayscaleFilename):
        try:
            os.remove(grayscaleFilename)
        except OSError:
            print('EX: disable_grayscale unable to delete ' +
                  grayscaleFilename)


def _set_custom_font(base_dir: str):
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
        filename = base_dir + '/fonts/custom.' + ext
        if os.path.isfile(filename):
            customFontExt = ext
            customFontType = extType
    if not customFontExt:
        return

    themeFiles = _get_theme_files()
    for filename in themeFiles:
        templateFilename = base_dir + '/' + filename
        if not os.path.isfile(templateFilename):
            continue
        with open(templateFilename, 'r') as cssfile:
            css = cssfile.read()
            css = \
                set_cs_sparam(css, "*src",
                              "url('./fonts/custom." +
                              customFontExt +
                              "') format('" +
                              customFontType + "')")
            css = set_cs_sparam(css, "*font-family", "'CustomFont'")
            filename = base_dir + '/' + filename
            with open(filename, 'w+') as cssfile:
                cssfile.write(css)


def set_theme_from_designer(base_dir: str, theme_name: str, domain: str,
                            themeParams: {},
                            allow_local_network_access: bool,
                            system_language: str):
    customThemeFilename = base_dir + '/accounts/theme.json'
    save_json(themeParams, customThemeFilename)
    set_theme(base_dir, theme_name, domain,
              allow_local_network_access, system_language)


def reset_theme_designer_settings(base_dir: str, theme_name: str, domain: str,
                                  allow_local_network_access: bool,
                                  system_language: str) -> None:
    """Resets the theme designer settings
    """
    customVariablesFile = base_dir + '/accounts/theme.json'
    if os.path.isfile(customVariablesFile):
        try:
            os.remove(customVariablesFile)
        except OSError:
            print('EX: unable to remove theme designer settings on reset')


def _read_variables_file(base_dir: str, theme_name: str,
                         variablesFile: str,
                         allow_local_network_access: bool) -> None:
    """Reads variables from a file in the theme directory
    """
    themeParams = load_json(variablesFile, 0)
    if not themeParams:
        return

    # set custom theme parameters
    customVariablesFile = base_dir + '/accounts/theme.json'
    if os.path.isfile(customVariablesFile):
        customThemeParams = load_json(customVariablesFile, 0)
        if customThemeParams:
            for variableName, value in customThemeParams.items():
                themeParams[variableName] = value

    bgParams = {
        "login": "jpg",
        "follow": "jpg",
        "options": "jpg",
        "search": "jpg"
    }
    _set_theme_from_dict(base_dir, theme_name, themeParams, bgParams,
                         allow_local_network_access)


def _set_theme_default(base_dir: str, allow_local_network_access: bool):
    name = 'default'
    _remove_theme(base_dir)
    _set_theme_in_config(base_dir, name)
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
    _set_theme_from_dict(base_dir, name, themeParams, bgParams,
                         allow_local_network_access)


def _set_theme_fonts(base_dir: str, theme_name: str) -> None:
    """Adds custom theme fonts
    """
    theme_name_lower = theme_name.lower()
    fontsDir = base_dir + '/fonts'
    themeFontsDir = \
        base_dir + '/theme/' + theme_name_lower + '/fonts'
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


def get_text_mode_banner(base_dir: str) -> str:
    """Returns the banner used for shell browsers, like Lynx
    """
    text_mode_banner_filename = base_dir + '/accounts/banner.txt'
    if os.path.isfile(text_mode_banner_filename):
        with open(text_mode_banner_filename, 'r') as fp:
            bannerStr = fp.read()
            if bannerStr:
                return bannerStr.replace('\n', '<br>')
    return None


def get_text_mode_logo(base_dir: str) -> str:
    """Returns the login screen logo used for shell browsers, like Lynx
    """
    textModeLogoFilename = base_dir + '/accounts/logo.txt'
    if not os.path.isfile(textModeLogoFilename):
        textModeLogoFilename = base_dir + '/img/logo.txt'

    with open(textModeLogoFilename, 'r') as fp:
        logoStr = fp.read()
        if logoStr:
            return logoStr.replace('\n', '<br>')
    return None


def _set_text_mode_theme(base_dir: str, name: str) -> None:
    # set the text mode logo which appears on the login screen
    # in browsers such as Lynx
    textModeLogoFilename = \
        base_dir + '/theme/' + name + '/logo.txt'
    if os.path.isfile(textModeLogoFilename):
        try:
            copyfile(textModeLogoFilename,
                     base_dir + '/accounts/logo.txt')
        except OSError:
            print('EX: _set_text_mode_theme unable to copy ' +
                  textModeLogoFilename + ' ' +
                  base_dir + '/accounts/logo.txt')
    else:
        try:
            copyfile(base_dir + '/img/logo.txt',
                     base_dir + '/accounts/logo.txt')
        except OSError:
            print('EX: _set_text_mode_theme unable to copy ' +
                  base_dir + '/img/logo.txt ' +
                  base_dir + '/accounts/logo.txt')

    # set the text mode banner which appears in browsers such as Lynx
    text_mode_banner_filename = \
        base_dir + '/theme/' + name + '/banner.txt'
    if os.path.isfile(base_dir + '/accounts/banner.txt'):
        try:
            os.remove(base_dir + '/accounts/banner.txt')
        except OSError:
            print('EX: _set_text_mode_theme unable to delete ' +
                  base_dir + '/accounts/banner.txt')
    if os.path.isfile(text_mode_banner_filename):
        try:
            copyfile(text_mode_banner_filename,
                     base_dir + '/accounts/banner.txt')
        except OSError:
            print('EX: _set_text_mode_theme unable to copy ' +
                  text_mode_banner_filename + ' ' +
                  base_dir + '/accounts/banner.txt')


def _set_theme_images(base_dir: str, name: str) -> None:
    """Changes the profile background image
    and banner to the defaults
    """
    theme_name_lower = name.lower()

    profileImageFilename = \
        base_dir + '/theme/' + theme_name_lower + '/image.png'
    banner_filename = \
        base_dir + '/theme/' + theme_name_lower + '/banner.png'
    searchBannerFilename = \
        base_dir + '/theme/' + theme_name_lower + '/search_banner.png'
    leftColImageFilename = \
        base_dir + '/theme/' + theme_name_lower + '/left_col_image.png'
    rightColImageFilename = \
        base_dir + '/theme/' + theme_name_lower + '/right_col_image.png'

    _set_text_mode_theme(base_dir, theme_name_lower)

    backgroundNames = ('login', 'shares', 'delete', 'follow',
                       'options', 'block', 'search', 'calendar',
                       'welcome')
    extensions = get_image_extensions()

    for subdir, dirs, files in os.walk(base_dir + '/accounts'):
        for acct in dirs:
            if not is_account_dir(acct):
                continue
            accountDir = os.path.join(base_dir + '/accounts', acct)

            for backgroundType in backgroundNames:
                for ext in extensions:
                    if theme_name_lower == 'default':
                        backgroundImageFilename = \
                            base_dir + '/theme/default/' + \
                            backgroundType + '_background.' + ext
                    else:
                        backgroundImageFilename = \
                            base_dir + '/theme/' + theme_name_lower + '/' + \
                            backgroundType + '_background' + '.' + ext

                    if os.path.isfile(backgroundImageFilename):
                        try:
                            copyfile(backgroundImageFilename,
                                     base_dir + '/accounts/' +
                                     backgroundType + '-background.' + ext)
                            continue
                        except OSError:
                            print('EX: _set_theme_images unable to copy ' +
                                  backgroundImageFilename)
                    # background image was not found
                    # so remove any existing file
                    if os.path.isfile(base_dir + '/accounts/' +
                                      backgroundType + '-background.' + ext):
                        try:
                            os.remove(base_dir + '/accounts/' +
                                      backgroundType + '-background.' + ext)
                        except OSError:
                            print('EX: _set_theme_images unable to delete ' +
                                  base_dir + '/accounts/' +
                                  backgroundType + '-background.' + ext)

            if os.path.isfile(profileImageFilename) and \
               os.path.isfile(banner_filename):
                try:
                    copyfile(profileImageFilename,
                             accountDir + '/image.png')
                except OSError:
                    print('EX: _set_theme_images unable to copy ' +
                          profileImageFilename)

                try:
                    copyfile(banner_filename,
                             accountDir + '/banner.png')
                except OSError:
                    print('EX: _set_theme_images unable to copy ' +
                          banner_filename)

                try:
                    if os.path.isfile(searchBannerFilename):
                        copyfile(searchBannerFilename,
                                 accountDir + '/search_banner.png')
                except OSError:
                    print('EX: _set_theme_images unable to copy ' +
                          searchBannerFilename)

                try:
                    if os.path.isfile(leftColImageFilename):
                        copyfile(leftColImageFilename,
                                 accountDir + '/left_col_image.png')
                    elif os.path.isfile(accountDir +
                                        '/left_col_image.png'):
                        try:
                            os.remove(accountDir + '/left_col_image.png')
                        except OSError:
                            print('EX: _set_theme_images unable to delete ' +
                                  accountDir + '/left_col_image.png')
                except OSError:
                    print('EX: _set_theme_images unable to copy ' +
                          leftColImageFilename)

                try:
                    if os.path.isfile(rightColImageFilename):
                        copyfile(rightColImageFilename,
                                 accountDir + '/right_col_image.png')
                    else:
                        if os.path.isfile(accountDir +
                                          '/right_col_image.png'):
                            try:
                                os.remove(accountDir + '/right_col_image.png')
                            except OSError:
                                print('EX: _set_theme_images ' +
                                      'unable to delete ' +
                                      accountDir + '/right_col_image.png')
                except OSError:
                    print('EX: _set_theme_images unable to copy ' +
                          rightColImageFilename)
        break


def set_news_avatar(base_dir: str, name: str,
                    http_prefix: str,
                    domain: str, domain_full: str) -> None:
    """Sets the avatar for the news account
    """
    nickname = 'news'
    newFilename = base_dir + '/theme/' + name + '/icons/avatar_news.png'
    if not os.path.isfile(newFilename):
        newFilename = base_dir + '/theme/default/icons/avatar_news.png'
    if not os.path.isfile(newFilename):
        return
    avatarFilename = \
        local_actor_url(http_prefix, domain_full, nickname) + '.png'
    avatarFilename = avatarFilename.replace('/', '-')
    filename = base_dir + '/cache/avatars/' + avatarFilename

    if os.path.isfile(filename):
        try:
            os.remove(filename)
        except OSError:
            print('EX: set_news_avatar unable to delete ' + filename)
    if os.path.isdir(base_dir + '/cache/avatars'):
        copyfile(newFilename, filename)
    accountDir = acct_dir(base_dir, nickname, domain)
    copyfile(newFilename, accountDir + '/avatar.png')


def _set_clear_cache_flag(base_dir: str) -> None:
    """Sets a flag which can be used by an external system
    (eg. a script in a cron job) to clear the browser cache
    """
    if not os.path.isdir(base_dir + '/accounts'):
        return
    flagFilename = base_dir + '/accounts/.clear_cache'
    with open(flagFilename, 'w+') as flagFile:
        flagFile.write('\n')


def set_theme(base_dir: str, name: str, domain: str,
              allow_local_network_access: bool, system_language: str) -> bool:
    """Sets the theme with the given name as the current theme
    """
    result = False

    prevThemeName = get_theme(base_dir)

    # if the theme has changed then remove any custom settings
    if prevThemeName != name:
        reset_theme_designer_settings(base_dir, name, domain,
                                      allow_local_network_access,
                                      system_language)

    _remove_theme(base_dir)

    themes = get_themes_list(base_dir)
    for theme_name in themes:
        theme_name_lower = theme_name.lower()
        if name == theme_name_lower:
            allow_access = allow_local_network_access
            try:
                globals()['set_theme' + theme_name](base_dir, allow_access)
            except BaseException:
                print('EX: set_theme unable to set theme ' + theme_name)

            if prevThemeName:
                if prevThemeName.lower() != theme_name_lower:
                    # change the banner and profile image
                    # to the default for the theme
                    _set_theme_images(base_dir, name)
                    _set_theme_fonts(base_dir, name)
            result = True

    if not result:
        # default
        _set_theme_default(base_dir, allow_local_network_access)
        result = True

    variablesFile = base_dir + '/theme/' + name + '/theme.json'
    if os.path.isfile(variablesFile):
        _read_variables_file(base_dir, name, variablesFile,
                             allow_local_network_access)

    _set_custom_font(base_dir)

    # set the news avatar
    newsAvatarThemeFilename = \
        base_dir + '/theme/' + name + '/icons/avatar_news.png'
    if os.path.isdir(base_dir + '/accounts/news@' + domain):
        if os.path.isfile(newsAvatarThemeFilename):
            newsAvatarFilename = \
                base_dir + '/accounts/news@' + domain + '/avatar.png'
            copyfile(newsAvatarThemeFilename, newsAvatarFilename)

    grayscaleFilename = base_dir + '/accounts/.grayscale'
    if os.path.isfile(grayscaleFilename):
        enable_grayscale(base_dir)
    else:
        disable_grayscale(base_dir)

    _copy_theme_help_files(base_dir, name, system_language)
    _set_theme_in_config(base_dir, name)
    _set_clear_cache_flag(base_dir)
    return result


def update_default_themes_list(base_dir: str) -> None:
    """Recreates the list of default themes
    """
    theme_names = get_themes_list(base_dir)
    defaultThemesFilename = base_dir + '/defaultthemes.txt'
    with open(defaultThemesFilename, 'w+') as defaultThemesFile:
        for name in theme_names:
            defaultThemesFile.write(name + '\n')


def scan_themes_for_scripts(base_dir: str) -> bool:
    """Scans the theme directory for any svg files containing scripts
    """
    for subdir, dirs, files in os.walk(base_dir + '/theme'):
        for f in files:
            if not f.endswith('.svg'):
                continue
            svgFilename = os.path.join(subdir, f)
            content = ''
            with open(svgFilename, 'r') as fp:
                content = fp.read()
            svgDangerous = dangerous_svg(content, False)
            if svgDangerous:
                print('svg file contains script: ' + svgFilename)
                return True
        # deliberately no break - should resursively scan
    return False
