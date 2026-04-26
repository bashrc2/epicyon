__filename__ = "data.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.7.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"


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
    return False


def load_string(filename: str, exception_text: str) -> str:
    """Loads a string from file
    """
    try:
        with open(filename, 'r', encoding='utf-8') as fp:
            text = fp.read()
            return text
    except OSError as exc:
        if '[ex]' in exception_text:
            exception_text = exception_text.replace('[ex]', str(exc))
        print(exception_text)
    return None


def save_string(text: str, filename: str, exception_text: str) -> bool:
    """Saves a string to file
    """
    return _store_base(text, filename, exception_text, 'w+')


def append_string(text: str, filename: str, exception_text: str) -> bool:
    """Appends a string to file
    """
    return _store_base(text, filename, exception_text, 'a+')
