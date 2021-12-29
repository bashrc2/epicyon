__filename__ = "markdown.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Web Interface"


def _markdown_emphasis_html(markdown: str) -> str:
    """Add italics and bold html markup to the given markdown
    """
    replacements = {
        ' **': ' <b>',
        '** ': '</b> ',
        '**.': '</b>.',
        '**:': '</b>:',
        '**;': '</b>;',
        '**,': '</b>,',
        '**\n': '</b>\n',
        ' *': ' <i>',
        '* ': '</i> ',
        '*.': '</i>.',
        '*:': '</i>:',
        '*;': '</i>;',
        '*,': '</i>,',
        '*\n': '</i>\n',
        ' _': ' <ul>',
        '_ ': '</ul> ',
        '_.': '</ul>.',
        '_:': '</ul>:',
        '_;': '</ul>;',
        '_,': '</ul>,',
        '_\n': '</ul>\n'
    }
    for md, html in replacements.items():
        markdown = markdown.replace(md, html)

    if markdown.startswith('**'):
        markdown = markdown[2:] + '<b>'
    elif markdown.startswith('*'):
        markdown = markdown[1:] + '<i>'
    elif markdown.startswith('_'):
        markdown = markdown[1:] + '<ul>'

    if markdown.endswith('**'):
        markdown = markdown[:len(markdown) - 2] + '</b>'
    elif markdown.endswith('*'):
        markdown = markdown[:len(markdown) - 1] + '</i>'
    elif markdown.endswith('_'):
        markdown = markdown[:len(markdown) - 1] + '</ul>'
    return markdown


def _markdown_replace_quotes(markdown: str) -> str:
    """Replaces > quotes with html blockquote
    """
    if '> ' not in markdown:
        return markdown
    lines = markdown.split('\n')
    result = ''
    prevQuoteLine = None
    for line in lines:
        if '> ' not in line:
            result += line + '\n'
            prevQuoteLine = None
            continue
        lineStr = line.strip()
        if not lineStr.startswith('> '):
            result += line + '\n'
            prevQuoteLine = None
            continue
        lineStr = lineStr.replace('> ', '', 1).strip()
        if prevQuoteLine:
            newPrevLine = prevQuoteLine.replace('</i></blockquote>\n', '')
            result = result.replace(prevQuoteLine, newPrevLine) + ' '
            lineStr += '</i></blockquote>\n'
        else:
            lineStr = '<blockquote><i>' + lineStr + '</i></blockquote>\n'
        result += lineStr
        prevQuoteLine = lineStr

    if '</blockquote>\n' in result:
        result = result.replace('</blockquote>\n', '</blockquote>')

    if result.endswith('\n') and \
       not markdown.endswith('\n'):
        result = result[:len(result) - 1]
    return result


def _markdown_replace_links(markdown: str, images: bool = False) -> str:
    """Replaces markdown links with html
    Optionally replace image links
    """
    replaceLinks = {}
    text = markdown
    startChars = '['
    if images:
        startChars = '!['
    while startChars in text:
        if ')' not in text:
            break
        text = text.split(startChars, 1)[1]
        markdownLink = startChars + text.split(')')[0] + ')'
        if ']' not in markdownLink or \
           '(' not in markdownLink:
            text = text.split(')', 1)[1]
            continue
        if not images:
            replaceLinks[markdownLink] = \
                '<a href="' + \
                markdownLink.split('(')[1].split(')')[0] + \
                '" target="_blank" rel="nofollow noopener noreferrer">' + \
                markdownLink.split(startChars)[1].split(']')[0] + \
                '</a>'
        else:
            replaceLinks[markdownLink] = \
                '<img class="markdownImage" src="' + \
                markdownLink.split('(')[1].split(')')[0] + \
                '" alt="' + \
                markdownLink.split(startChars)[1].split(']')[0] + \
                '" />'
        text = text.split(')', 1)[1]
    for mdLink, htmlLink in replaceLinks.items():
        markdown = markdown.replace(mdLink, htmlLink)
    return markdown


def markdown_to_html(markdown: str) -> str:
    """Converts markdown formatted text to html
    """
    markdown = _markdown_replace_quotes(markdown)
    markdown = _markdown_emphasis_html(markdown)
    markdown = _markdown_replace_links(markdown, True)
    markdown = _markdown_replace_links(markdown)

    # replace headers
    linesList = markdown.split('\n')
    htmlStr = ''
    ctr = 0
    titles = {
        "h5": '#####',
        "h4": '####',
        "h3": '###',
        "h2": '##',
        "h1": '#'
    }
    for line in linesList:
        if ctr > 0:
            htmlStr += '<br>'
        for h, hashes in titles.items():
            if line.startswith(hashes):
                line = line.replace(hashes, '').strip()
                line = '<' + h + '>' + line + '</' + h + '>'
                ctr = -1
                break
        htmlStr += line
        ctr += 1
    return htmlStr
