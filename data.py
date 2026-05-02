__filename__ = "data.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.7.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"

import os


def _store_base(text: str, filename: str, exception_text: str,
                mode: str) -> bool:
    """Saves a string to file
    """
    try:
        with open(filename, mode, encoding='utf-8') as fp:
            fp.write(text)
            return True
    except OSError as exc:
        if '[ex]' in exception_text:
            exception_text = exception_text.replace('[ex]', str(exc))
        print(exception_text)
    except UnicodeEncodeError as exc:
        if '[ex]' in exception_text:
            exception_text = exception_text.replace('[ex]', str(exc))
        print(exception_text)
    return False


def load_string(filename: str, exception_text: str) -> str:
    """Loads a string from file
    """
    try:
        with open(filename, 'r', encoding='utf-8') as fp:
            text: str = fp.read()
            return text
    except OSError as exc:
        if '[ex]' in exception_text:
            exception_text = exception_text.replace('[ex]', str(exc))
        print(exception_text)
    except UnicodeEncodeError as exc:
        if '[ex]' in exception_text:
            exception_text = exception_text.replace('[ex]', str(exc))
        print(exception_text)
    return None


def load_binary(filename: str, exception_text: str) -> str:
    """Loads a binary from file
    """
    try:
        with open(filename, 'rb') as fp:
            binary = fp.read()
            return binary
    except OSError as exc:
        if '[ex]' in exception_text:
            exception_text = exception_text.replace('[ex]', str(exc))
        print(exception_text)
    return None


def load_line(filename: str, exception_text: str) -> str:
    """Loads a line of text from file
    """
    try:
        with open(filename, 'r', encoding='utf-8') as fp:
            text: str = fp.readline()
            return text
    except OSError as exc:
        if '[ex]' in exception_text:
            exception_text = exception_text.replace('[ex]', str(exc))
        print(exception_text)
    except UnicodeEncodeError as exc:
        if '[ex]' in exception_text:
            exception_text = exception_text.replace('[ex]', str(exc))
        print(exception_text)
    return None


def load_list(filename: str, exception_text: str) -> str:
    """Loads a list from file
    This is used to replace readlines
    """
    lines: list[str] = []
    lines_str: str = load_string(filename, exception_text)
    if lines_str is None:
        return None
    if lines_str:
        lines2 = lines_str.split('\n')
        for line in lines2:
            if not line:
                continue
            lines.append(line + '\n')
    return lines


def save_string(text: str, filename: str, exception_text: str) -> bool:
    """Saves a string to file
    """
    return _store_base(text, filename, exception_text, 'w+')


def save_flag_file(filename: str, exception_text: str) -> bool:
    """Saves a flag file
    This creates a file containing a single character, and the presence
    or absence of the file is used to implement the checkbox profile
    options
    """
    return _store_base('\n', filename, exception_text, 'w+')


def save_binary(text: str, filename: str, exception_text: str) -> bool:
    """Saves a binary to file
    """
    try:
        with open(filename, 'wb') as fp:
            fp.write(text)
            return True
    except OSError as exc:
        if '[ex]' in exception_text:
            exception_text = exception_text.replace('[ex]', str(exc))
        print(exception_text)
    return False


def append_string(text: str, filename: str, exception_text: str) -> bool:
    """Appends a string to file
    """
    return _store_base(text, filename, exception_text, 'a+')


def prepend_string(text: str, filename: str, exception_text: str) -> bool:
    """Prepends a string to a file
    """
    try:
        with open(filename, 'r+', encoding='utf-8') as fp:
            content: str = fp.read()
            if text + '\n' not in content:
                fp.seek(0, 0)
                fp.write(text + '\n' + content)
            return True
    except OSError as exc:
        if '[ex]' in exception_text:
            exception_text = exception_text.replace('[ex]', str(exc))
        print(exception_text)
    except UnicodeEncodeError as exc:
        if '[ex]' in exception_text:
            exception_text = exception_text.replace('[ex]', str(exc))
        print(exception_text)
    return False


def erase_file(filename: str, exception_text: str) -> bool:
    """Deletes a file
    """
    try:
        os.remove(filename)
        return True
    except OSError as exc:
        if '[ex]' in exception_text:
            exception_text = exception_text.replace('[ex]', str(exc))
        print(exception_text)
    return False


def move_file(old_filename: str, new_filename: str,
              exception_text: str) -> bool:
    """Moves/overwrites a file
    """
    try:
        os.rename(old_filename, new_filename)
        return True
    except OSError as exc:
        if '[ex]' in exception_text:
            exception_text = exception_text.replace('[ex]', str(exc))
        print(exception_text)
    return False


def is_a_file(filename: str) -> bool:
    """Returns true if the given filename exists
    """
    return os.path.isfile(filename)


def is_a_dir(directory: str) -> bool:
    """Returns true if the given directory exists
    """
    return os.path.isdir(directory)
