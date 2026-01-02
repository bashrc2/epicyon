__filename__ = "unicodetext.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.7.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"

# functions which deal with fancy unicode text characters.
# Such text is "clever", but fucks up screen readers and accessibility
# in general


def uninvert_text(text: str) -> str:
    """uninverts inverted text
    """
    if len(text) < 4:
        return text

    flip_table = {
        '\u0021': '\u00A1',
        '\u0022': '\u201E',
        '\u0026': '\u214B',
        '\u002E': '\u02D9',
        '\u0033': '\u0190',
        '\u0034': '\u152D',
        '\u0037': '\u2C62',
        '\u003B': '\u061B',
        '\u003F': '\u00BF',
        '\u0041': '\u2200',
        '\u0042': '\u10412',
        '\u0043': '\u2183',
        '\u0044': '\u25D6',
        '\u0045': '\u018E',
        '\u0046': '\u2132',
        '\u0047': '\u2141',
        '\u004A': '\u017F',
        '\u004B': '\u22CA',
        '\u004C': '\u2142',
        '\u004D': '\u0057',
        '\u004E': '\u1D0E',
        '\u0050': '\u0500',
        '\u0051': '\u038C',
        '\u0052': '\u1D1A',
        '\u0054': '\u22A5',
        '\u0055': '\u2229',
        '\u0056': '\u1D27',
        '\u0059': '\u2144',
        '\u005F': '\u203E',
        '\u0061': '\u0250',
        '\u0062': '\u0071',
        '\u0063': '\u0254',
        '\u0064': '\u0070',
        '\u0065': '\u01DD',
        '\u0066': '\u025F',
        '\u0067': '\u0183',
        '\u0068': '\u0265',
        '\u0069': '\u0131',
        '\u006A': '\u027E',
        '\u006B': '\u029E',
        '\u006C': '\u0283',
        '\u006D': '\u026F',
        '\u006E': '\u0075',
        '\u0072': '\u0279',
        '\u0074': '\u0287',
        '\u0076': '\u028C',
        '\u0077': '\u028D',
        '\u0079': '\u028E',
        '\u203F': '\u2040',
        '\u2234': '\u2235'
    }

    matches = 0
    possible_result = ''
    for ch_test in text:
        ch_result = ch_test
        for ch1, ch_inv in flip_table.items():
            if ch_test == ch_inv:
                matches += 1
                ch_result = ch1
                break
        possible_result = ch_result + possible_result

    result = text
    if matches > len(text)/2:
        result = possible_result
        new_result = ''
        extra_replace = {
            '[': ']',
            ']': '[',
            '(': ')',
            ')': '(',
            '<': '>',
            '>': '<',
            '9': '6',
            '6': '9'
        }
        for ch1 in result:
            ch_result = ch1
            for ch2, rep in extra_replace.items():
                if ch1 == ch2:
                    ch_result = rep
                    break
            new_result += ch_result
        result = new_result
    return result


def remove_inverted_text(text: str, system_language: str) -> str:
    """Removes any inverted text from the given string
    """
    if system_language != 'en':
        return text

    text = uninvert_text(text)

    inverted_lower = [*"_ʎ_ʍʌ_ʇ_ɹ____ɯʃʞɾıɥƃɟǝ_ɔ_ɐ"]
    inverted_upper = [*"_⅄__ᴧ∩⊥_ᴚΌԀ_ᴎ_⅂⋊ſ__⅁ℲƎ◖Ↄ𐐒∀"]

    start_separator = ''
    separator = '\n'
    if '</p>' in text:
        text = text.replace('<p>', '')
        start_separator = '<p>'
        separator = '</p>'
    paragraphs = text.split(separator)
    new_text = ''
    inverted_list = (inverted_lower, inverted_upper)
    z_value = (ord('z'), ord('Z'))
    for para in paragraphs:
        replaced_chars = 0

        for idx in range(2):
            index = 0
            for test_ch in inverted_list[idx]:
                if test_ch == '_':
                    index += 1
                    continue
                if test_ch in para:
                    para = para.replace(test_ch, chr(z_value[idx] - index))
                    replaced_chars += 1
                index += 1

        if replaced_chars > 2:
            para = para[::-1]
        if para:
            new_text += start_separator + para
            if separator in text:
                new_text += separator

    return new_text


def remove_square_capitals(text: str, system_language: str) -> str:
    """Removes any square capital text from the given string
    """
    if system_language != 'en':
        return text
    offset = ord('A')
    start_value = ord('🅰')
    end_value = start_value + 26
    result = ''
    for text_ch in text:
        text_value = ord(text_ch)
        if text_value < start_value or text_value > end_value:
            result += text_ch
        else:
            result += chr(offset + text_value - start_value)
    return result


def _standardize_text_range(text: str,
                            range_start: int, range_end: int,
                            offset: str) -> str:
    """Convert any fancy characters within the given range into ordinary ones
    """
    offset = ord(offset)
    ctr = 0
    text = list(text)
    while ctr < len(text):
        val = ord(text[ctr])
        if val in range(range_start, range_end):
            text[ctr] = chr(val - range_start + offset)
        ctr += 1
    return "".join(text)


def standardize_text(text: str) -> str:
    """Converts fancy unicode text to ordinary letters
    """
    if not text:
        return text

    char_ranges = (
        [65345, 'a'],
        [119886, 'a'],
        [119990, 'a'],
        [120042, 'a'],
        [120094, 'a'],
        [120146, 'a'],
        [120198, 'a'],
        [120302, 'a'],
        [120354, 'a'],
        [120406, 'a'],
        [65313, 'A'],
        [119912, 'A'],
        [119964, 'A'],
        [120016, 'A'],
        [120068, 'A'],
        [120120, 'A'],
        [120172, 'A'],
        [120224, 'A'],
        [120328, 'A'],
        [120380, 'A'],
        [120432, 'A'],
        [127344, 'A'],
        [127312, 'A'],
        [127280, 'A'],
        [127248, 'A'],
        [120276, 'A'],
        [120812, '0']
    )
    for char_range in char_ranges:
        range_start = char_range[0]
        if char_range[1] == '0':
            range_end = range_start + 10
        else:
            range_end = range_start + 26
        offset = char_range[1]
        text = _standardize_text_range(text, range_start, range_end, offset)

    return uninvert_text(text)
