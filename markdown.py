__filename__ = "markdown.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.3.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Web Interface"


def _markdown_get_sections(markdown: str) -> []:
    """Returns a list of sections for markdown
    """
    if '<code>' not in markdown:
        return [markdown]
    lines = markdown.split('\n')
    sections = []
    section_text = ''
    section_active = False
    ctr = 0
    for line in lines:
        if ctr > 0:
            section_text += '\n'

        if not section_active:
            if '<code>' in line:
                section_active = True
                sections.append(section_text)
                section_text = ''
        else:
            if '</code>' in line:
                section_active = False
                sections.append(section_text)
                section_text = ''

        section_text += line
        ctr += 1
    if section_text.strip():
        sections.append(section_text)
    return sections


def _markdown_emphasis_html(markdown: str) -> str:
    """Add italics and bold html markup to the given markdown
    """
    replacements = {
        ' **': ' <b>',
        '** ': '</b> ',
        '**.': '</b>.',
        '**:': '</b>:',
        '**;': '</b>;',
        '?**': '?</b>',
        '\n**': '\n<b>',
        '**,': '</b>,',
        '**\n': '</b>\n',
        '**)': '</b>)',
        '>**': '><b>',
        '**<': '</b><',
        '>*': '><i>',
        '*<': '</i><',
        ' *': ' <i>',
        '* ': '</i> ',
        '?*': '?</i>',
        '\n*': '\n<i>',
        '*.': '</i>.',
        '*:': '</i>:',
        '*;': '</i>;',
        '*)': '</i>)',
        '*,': '</i>,',
        '*\n': '</i>\n',
        ' _': ' <ul>',
        '_ ': '</ul> ',
        '_.': '</ul>.',
        '_:': '</ul>:',
        '_;': '</ul>;',
        '_,': '</ul>,',
        '_\n': '</ul>\n',
        ' `': ' <em>',
        '`.': '</em>.',
        '`:': '</em>:',
        "`'": "</em>'",
        "`)": "</em>)",
        '`;': '</em>;',
        '`,': '</em>;',
        '`\n': '</em>\n',
        '` ': '</em> '
    }

    sections = _markdown_get_sections(markdown)
    markdown = ''
    for section_text in sections:
        if '<code>' in section_text:
            markdown += section_text
            continue
        for md_str, html in replacements.items():
            section_text = section_text.replace(md_str, html)

        if section_text.startswith('**'):
            section_text = section_text[2:] + '<b>'
        elif section_text.startswith('*'):
            section_text = section_text[1:] + '<i>'
        elif section_text.startswith('_'):
            section_text = section_text[1:] + '<ul>'

        if section_text.endswith('**'):
            section_text = section_text[:len(section_text) - 2] + '</b>'
        elif section_text.endswith('*'):
            section_text = section_text[:len(section_text) - 1] + '</i>'
        elif section_text.endswith('_'):
            section_text = section_text[:len(section_text) - 1] + '</ul>'

        if section_text.strip():
            markdown += section_text
    return markdown


def _markdown_replace_quotes(markdown: str) -> str:
    """Replaces > quotes with html blockquote
    """
    if '> ' not in markdown:
        return markdown
    lines = markdown.split('\n')
    result = ''
    prev_quote_line = None
    code_section = False
    for line in lines:
        # avoid code sections
        if not code_section:
            if '<code>' in line:
                code_section = True
        else:
            if '</code>' in line:
                code_section = False
        if code_section:
            result += line + '\n'
            continue

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
        link_text = markdown_link.split(start_chars)[1].split(']')[0]
        link_text = link_text.replace('`', '')
        if not images:
            replace_links[markdown_link] = \
                '<a href="' + \
                markdown_link.split('(')[1].split(')')[0] + \
                '" target="_blank" rel="nofollow noopener noreferrer">' + \
                link_text + '</a>'
        else:
            link_text = markdown_link.split(start_chars)[1].split(']')[0]
            replace_links[markdown_link] = \
                '<img class="markdownImage" src="' + \
                markdown_link.split('(')[1].split(')')[0] + \
                '" alt="' + link_text + '" />'
        text = text.split(')', 1)[1]

    for md_link, html_link in replace_links.items():
        lines = markdown.split('\n')
        markdown = ''
        code_section = False
        ctr = 0
        for line in lines:
            if ctr > 0:
                markdown += '\n'
            # avoid code sections
            if not code_section:
                if '<code>' in line:
                    code_section = True
            else:
                if '</code>' in line:
                    code_section = False
            if code_section:
                markdown += line
                ctr += 1
                continue
            markdown += line.replace(md_link, html_link)
            ctr += 1
    return markdown


def _markdown_replace_bullet_points(markdown: str) -> str:
    """Replaces bullet points
    """
    lines = markdown.split('\n')
    bullet_style = ('* ', ' * ', '- ', ' - ')
    bullet_matched = ''
    start_line = -1
    line_ctr = 0
    changed = False
    code_section = False
    for line in lines:
        if not line.strip():
            # skip blank lines
            line_ctr += 1
            continue

        # skip over code sections
        if not code_section:
            if '<code>' in line:
                code_section = True
        else:
            if '</code>' in line:
                code_section = False
        if code_section:
            line_ctr += 1
            continue

        if not bullet_matched:
            for test_str in bullet_style:
                if line.startswith(test_str):
                    bullet_matched = test_str
                    start_line = line_ctr
                    break
        else:
            if not line.startswith(bullet_matched):
                for index in range(start_line, line_ctr):
                    line_text = lines[index].replace(bullet_matched, '', 1)
                    if index == start_line:
                        lines[index] = '<ul>\n<li>' + line_text + '</li>'
                    elif index == line_ctr - 1:
                        lines[index] = '<li>' + line_text + '</li>\n</ul>'
                    else:
                        lines[index] = '<li>' + line_text + '</li>'
                changed = True
                start_line = -1
                bullet_matched = ''
        line_ctr += 1

    if not changed:
        return markdown

    markdown = ''
    for line in lines:
        markdown += line + '\n'
    return markdown


def _markdown_replace_code(markdown: str) -> str:
    """Replaces code sections within markdown
    """
    lines = markdown.split('\n')
    start_line = -1
    line_ctr = 0
    changed = False
    section_active = False
    for line in lines:
        if not line.strip():
            # skip blank lines
            line_ctr += 1
            continue
        if line.startswith('```'):
            if not section_active:
                start_line = line_ctr
                section_active = True
            else:
                lines[start_line] = '<code>'
                lines[line_ctr] = '</code>'
                section_active = False
                changed = True
        line_ctr += 1

    if not changed:
        return markdown

    markdown = ''
    for line in lines:
        markdown += line + '\n'
    return markdown


def markdown_to_html(markdown: str) -> str:
    """Converts markdown formatted text to html
    """
    markdown = _markdown_replace_code(markdown)
    markdown = _markdown_replace_bullet_points(markdown)
    markdown = _markdown_replace_quotes(markdown)
    markdown = _markdown_emphasis_html(markdown)
    markdown = _markdown_replace_links(markdown, True)
    markdown = _markdown_replace_links(markdown)

    # replace headers
    lines_list = markdown.split('\n')
    html_str = ''
    ctr = 0
    code_section = False
    titles = {
        "h5": '#####',
        "h4": '####',
        "h3": '###',
        "h2": '##',
        "h1": '#'
    }
    for line in lines_list:
        if ctr > 0:
            html_str += '<br>\n'

        # avoid code sections
        if not code_section:
            if '<code>' in line:
                code_section = True
        else:
            if '</code>' in line:
                code_section = False
        if code_section:
            html_str += line
            ctr += 1
            continue

        for hsh, hashes in titles.items():
            if line.startswith(hashes):
                line = line.replace(hashes, '').strip()
                line = '<' + hsh + '>' + line + '</' + hsh + '>\n'
                ctr = -1
                break
        html_str += line
        ctr += 1

    html_str = html_str.replace('<code><br>', '<code>')
    html_str = html_str.replace('</code><br>', '</code>')

    return html_str
