__filename__ = "webapp_theme_designer.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Web Interface"

import os
from utils import load_json
from utils import get_config_param
from webapp_utils import html_header_with_external_style
from webapp_utils import html_footer
from webapp_utils import get_banner_file


color_to_hex = {
    "aliceblue": "#f0f8ff",
    "antiquewhite": "#faebd7",
    "aqua": "#00ffff",
    "aquamarine": "#7fffd4",
    "azure": "#f0ffff",
    "beige": "#f5f5dc",
    "bisque": "#ffe4c4",
    "black": "#000000",
    "blanchedalmond": "#ffebcd",
    "blue": "#0000ff",
    "blueviolet": "#8a2be2",
    "brown": "#a52a2a",
    "burlywood": "#deb887",
    "cadetblue": "#5f9ea0",
    "chartreuse": "#7fff00",
    "chocolate": "#d2691e",
    "coral": "#ff7f50",
    "cornflowerblue": "#6495ed",
    "cornsilk": "#fff8dc",
    "crimson": "#dc143c",
    "cyan": "#00ffff",
    "darkblue": "#00008b",
    "darkcyan": "#008b8b",
    "darkgoldenrod": "#b8860b",
    "darkgray": "#a9a9a9",
    "darkgrey": "#a9a9a9",
    "darkgreen": "#006400",
    "darkkhaki": "#bdb76b",
    "darkmagenta": "#8b008b",
    "darkolivegreen": "#556b2f",
    "darkorange": "#ff8c00",
    "darkorchid": "#9932cc",
    "darkred": "#8b0000",
    "darksalmon": "#e9967a",
    "darkseagreen": "#8fbc8f",
    "darkslateblue": "#483d8b",
    "darkslategray": "#2f4f4f",
    "darkslategrey": "#2f4f4f",
    "darkturquoise": "#00ced1",
    "darkviolet": "#9400d3",
    "deeppink": "#ff1493",
    "deepskyblue": "#00bfff",
    "dimgray": "#696969",
    "dimgrey": "#696969",
    "dodgerblue": "#1e90ff",
    "firebrick": "#b22222",
    "floralwhite": "#fffaf0",
    "forestgreen": "#228b22",
    "fuchsia": "#ff00ff",
    "gainsboro": "#dcdcdc",
    "ghostwhite": "#f8f8ff",
    "gold": "#ffd700",
    "goldenrod": "#daa520",
    "gray": "#808080",
    "grey": "#808080",
    "green": "#008000",
    "greenyellow": "#adff2f",
    "honeydew": "#f0fff0",
    "hotpink": "#ff69b4",
    "indianred": "#cd5c5c",
    "indigo": "#4b0082",
    "ivory": "#fffff0",
    "khaki": "#f0e68c",
    "lavender": "#e6e6fa",
    "lavenderblush": "#fff0f5",
    "lawngreen": "#7cfc00",
    "lemonchiffon": "#fffacd",
    "lightblue": "#add8e6",
    "lightcoral": "#f08080",
    "lightcyan": "#e0ffff",
    "lightgoldenrodyellow": "#fafad2",
    "lightgray": "#d3d3d3",
    "lightgrey": "#d3d3d3",
    "lightgreen": "#90ee90",
    "lightpink": "#ffb6c1",
    "lightsalmon": "#ffa07a",
    "lightseagreen": "#20b2aa",
    "lightskyblue": "#87cefa",
    "lightslategray": "#778899",
    "lightslategrey": "#778899",
    "lightsteelblue": "#b0c4de",
    "lightyellow": "#ffffe0",
    "lime": "#00ff00",
    "limegreen": "#32cd32",
    "linen": "#faf0e6",
    "magenta": "#ff00ff",
    "maroon": "#800000",
    "mediumaquamarine": "#66cdaa",
    "mediumblue": "#0000cd",
    "mediumorchid": "#ba55d3",
    "mediumpurple": "#9370db",
    "mediumseagreen": "#3cb371",
    "mediumslateblue": "#7b68ee",
    "mediumspringgreen": "#00fa9a",
    "mediumturquoise": "#48d1cc",
    "mediumvioletred": "#c71585",
    "midnightblue": "#191970",
    "mintcream": "#f5fffa",
    "mistyrose": "#ffe4e1",
    "moccasin": "#ffe4b5",
    "navajowhite": "#ffdead",
    "navy": "#000080",
    "oldlace": "#fdf5e6",
    "olive": "#808000",
    "olivedrab": "#6b8e23",
    "orange": "#ffa500",
    "orangered": "#ff4500",
    "orchid": "#da70d6",
    "palegoldenrod": "#eee8aa",
    "palegreen": "#98fb98",
    "paleturquoise": "#afeeee",
    "palevioletred": "#db7093",
    "papayawhip": "#ffefd5",
    "peachpuff": "#ffdab9",
    "peru": "#cd853f",
    "pink": "#ffc0cb",
    "plum": "#dda0dd",
    "powderblue": "#b0e0e6",
    "purple": "#800080",
    "red": "#ff0000",
    "rosybrown": "#bc8f8f",
    "royalblue": "#4169e1",
    "saddlebrown": "#8b4513",
    "salmon": "#fa8072",
    "sandybrown": "#f4a460",
    "seagreen": "#2e8b57",
    "seashell": "#fff5ee",
    "sienna": "#a0522d",
    "silver": "#c0c0c0",
    "skyblue": "#87ceeb",
    "slateblue": "#6a5acd",
    "slategray": "#708090",
    "slategrey": "#708090",
    "snow": "#fffafa",
    "springgreen": "#00ff7f",
    "steelblue": "#4682b4",
    "tan": "#d2b48c",
    "teal": "#008080",
    "thistle": "#d8bfd8",
    "tomato": "#ff6347",
    "turquoise": "#40e0d0",
    "violet": "#ee82ee",
    "wheat": "#f5deb3",
    "white": "#ffffff",
    "whitesmoke": "#f5f5f5",
    "yellow": "#ffff00",
    "yellowgreen": "#9acd32",
}


def html_theme_designer(css_cache: {}, base_dir: str,
                        nickname: str, domain: str,
                        translate: {}, defaultTimeline: str,
                        theme_name: str, accessKeys: {}) -> str:
    """Edit theme settings
    """
    themeFilename = base_dir + '/theme/' + theme_name + '/theme.json'
    themeJson = {}
    if os.path.isfile(themeFilename):
        themeJson = load_json(themeFilename)

    # set custom theme parameters
    customVariablesFile = base_dir + '/accounts/theme.json'
    if os.path.isfile(customVariablesFile):
        customThemeParams = load_json(customVariablesFile, 0)
        if customThemeParams:
            for variableName, value in customThemeParams.items():
                themeJson[variableName] = value

    themeForm = ''
    cssFilename = base_dir + '/epicyon-profile.css'
    if os.path.isfile(base_dir + '/epicyon.css'):
        cssFilename = base_dir + '/epicyon.css'

    instanceTitle = \
        get_config_param(base_dir, 'instanceTitle')
    themeForm = \
        html_header_with_external_style(cssFilename, instanceTitle, None)
    bannerFile, bannerFilename = \
        get_banner_file(base_dir, nickname, domain, theme_name)
    themeForm += \
        '<a href="/users/' + nickname + '/' + defaultTimeline + '" ' + \
        'accesskey="' + accessKeys['menuTimeline'] + '">' + \
        '<img loading="lazy" class="timeline-banner" ' + \
        'title="' + translate['Switch to timeline view'] + '" ' + \
        'alt="' + translate['Switch to timeline view'] + '" ' + \
        'src="/users/' + nickname + '/' + bannerFile + '" /></a>\n'
    themeForm += '<div class="container">\n'

    themeForm += \
        '    <h1>' + translate['Theme Designer'] + '</h1>\n'

    themeForm += '  <form method="POST" action="' + \
        '/users/' + nickname + '/changeThemeSettings">\n'

    resetKey = accessKeys['menuLogout']
    submitKey = accessKeys['submitButton']
    themeForm += \
        '    <center>\n' + \
        '    <button type="submit" class="button" ' + \
        'name="submitThemeDesignerReset" ' + \
        'accesskey="' + resetKey + '">' + \
        translate['Reset'] + '</button>\n' + \
        '    <button type="submit" class="button" ' + \
        'name="submitThemeDesigner" accesskey="' + submitKey + '">' + \
        translate['Submit'] + '</button>\n    </center>\n'

    tableStr = '    <table class="accesskeys">\n'
    tableStr += '      <colgroup>\n'
    tableStr += '        <col span="1" class="accesskeys-left">\n'
    tableStr += '        <col span="1" class="accesskeys-center">\n'
    tableStr += '      </colgroup>\n'
    tableStr += '      <tbody>\n'

    fontStr = '    <div class="container">\n' + tableStr
    colorStr = '    <div class="container">\n' + tableStr
    dimensionStr = '    <div class="container">\n' + tableStr
    switchStr = '    <div class="container">\n' + tableStr
    for variableName, value in themeJson.items():
        if 'font-size' in variableName:
            variableNameStr = variableName.replace('-', ' ')
            variableNameStr = variableNameStr.title()
            fontStr += \
                '      <tr><td><label class="labels">' + \
                variableNameStr + '</label></td>'
            fontStr += \
                '<td><input type="text" name="themeSetting_' + \
                variableName + '" value="' + str(value) + \
                '" title="' + variableNameStr + '"></td></tr>\n'
        elif ('-color' in variableName or
              '-background' in variableName or
              variableName.endswith('-text') or
              value.startswith('#') or
              color_to_hex.get(value)):
            # only use colors defined as hex
            if not value.startswith('#'):
                if color_to_hex.get(value):
                    value = color_to_hex[value]
                else:
                    continue
            variableNameStr = variableName.replace('-', ' ')
            if ' color' in variableNameStr:
                variableNameStr = variableNameStr.replace(' color', '')
            if ' bg' in variableNameStr:
                variableNameStr = variableNameStr.replace(' bg', ' background')
            elif ' fg' in variableNameStr:
                variableNameStr = variableNameStr.replace(' fg', ' foreground')
            if variableNameStr == 'cw':
                variableNameStr = 'content warning'
            variableNameStr = variableNameStr.title()
            colorStr += \
                '      <tr><td><label class="labels">' + \
                variableNameStr + '</label></td>'
            colorStr += \
                '<td><input type="color" name="themeSetting_' + \
                variableName + '" value="' + str(value) + \
                '" title="' + variableNameStr + '"></td></tr>\n'
        elif (('-width' in variableName or
               '-height' in variableName or
               '-spacing' in variableName or
               '-margin' in variableName or
               '-vertical' in variableName) and
              (value.lower() != 'true' and value.lower() != 'false')):
            variableNameStr = variableName.replace('-', ' ')
            variableNameStr = variableNameStr.title()
            dimensionStr += \
                '      <tr><td><label class="labels">' + \
                variableNameStr + '</label></td>'
            dimensionStr += \
                '<td><input type="text" name="themeSetting_' + \
                variableName + '" value="' + str(value) + \
                '" title="' + variableNameStr + '"></td></tr>\n'
        elif value.title() == 'True' or value.title() == 'False':
            variableNameStr = variableName.replace('-', ' ')
            variableNameStr = variableNameStr.title()
            switchStr += \
                '      <tr><td><label class="labels">' + \
                variableNameStr + '</label></td>'
            checkedStr = ''
            if value.title() == 'True':
                checkedStr = ' checked'
            switchStr += \
                '<td><input type="checkbox" class="profilecheckbox" ' + \
                'name="themeSetting_' + variableName + '"' + \
                checkedStr + '></td></tr>\n'

    colorStr += '    </table>\n    </div>\n'
    fontStr += '    </table>\n    </div>\n'
    dimensionStr += '    </table>\n    </div>\n'
    switchStr += '    </table>\n    </div>\n'

    themeFormats = '.zip, .gz'
    exportImportStr = '    <div class="container">\n'
    exportImportStr += \
        '      <label class="labels">' + \
        translate['Import Theme'] + '</label>\n'
    exportImportStr += '      <input type="file" id="import_theme" '
    exportImportStr += 'name="submitImportTheme" '
    exportImportStr += 'accept="' + themeFormats + '">\n'
    exportImportStr += \
        '      <label class="labels">' + \
        translate['Export Theme'] + '</label><br>\n'
    exportImportStr += \
        '      <button type="submit" class="button" ' + \
        'name="submitExportTheme">➤</button><br>\n'
    exportImportStr += '    </div>\n'

    themeForm += colorStr + fontStr + dimensionStr
    themeForm += switchStr + exportImportStr
    themeForm += '  </form>\n'
    themeForm += '</div>\n'
    themeForm += html_footer()
    return themeForm
