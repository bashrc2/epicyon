__filename__ = "markdown.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.3.0"
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
    for md_str, html in replacements.items():
        markdown = markdown.replace(md_str, html)

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
    prev_quote_line = None
    for line in lines:
        if '> ' not in line:
            result += line + '\n'
            prev_quote_line = None
            continue
        line_str = line.strip()
        if not line_str.startswith('> '):
            result += line + '\n'
            prev_quote_line = None
            continue
        line_str = line_str.replace('> ', '', 1).strip()
        if prev_quote_line:
            new_prev_line = prev_quote_line.replace('</i></blockquote>\n', '')
            result = result.replace(prev_quote_line, new_prev_line) + ' '
            line_str += '</i></blockquote>\n'
        else:
            line_str = '<blockquote><i>' + line_str + '</i></blockquote>\n'
        result += line_str
        prev_quote_line = line_str

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
    replace_links = {}
    text = markdown
    start_chars = '['
    if images:
        start_chars = '!['
    while start_chars in text:
        if ')' not in text:
            break
        text = text.split(start_chars, 1)[1]
        markdown_link = start_chars + text.split(')')[0] + ')'
        if ']' not in markdown_link or \
           '(' not in markdown_link:
            text = text.split(')', 1)[1]
            continue
        if not images:
            replace_links[markdown_link] = \
                '<a href="' + \
                markdown_link.split('(')[1].split(')')[0] + \
                '" target="_blank" rel="nofollow noopener noreferrer">' + \
                markdown_link.split(start_chars)[1].split(']')[0] + \
                '</a>'
        else:
            replace_links[markdown_link] = \
                '<img class="markdownImage" src="' + \
                markdown_link.split('(')[1].split(')')[0] + \
                '" alt="' + \
                markdown_link.split(start_chars)[1].split(']')[0] + \
                '" />'
        text = text.split(')', 1)[1]
    for md_link, html_link in replace_links.items():
        markdown = markdown.replace(md_link, html_link)
    return markdown


def markdown_to_html(markdown: str) -> str:
    """Converts markdown formatted text to html
    """
    markdown = _markdown_replace_quotes(markdown)
    markdown = _markdown_emphasis_html(markdown)
    markdown = _markdown_replace_links(markdown, True)
    markdown = _markdown_replace_links(markdown)

    # replace headers
    lines_list = markdown.split('\n')
    html_str = ''
    ctr = 0
    titles = {
        "h5": '#####',
        "h4": '####',
        "h3": '###',
        "h2": '##',
        "h1": '#'
    }
    for line in lines_list:
        if ctr > 0:
            html_str += '<br>'
        for hsh, hashes in titles.items():
            if line.startswith(hashes):
                line = line.replace(hashes, '').strip()
                line = '<' + hsh + '>' + line + '</' + hsh + '>'
                ctr = -1
                break
        html_str += line
        ctr += 1
    return html_str
