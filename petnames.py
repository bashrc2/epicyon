__filename__ = "petnames.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.7.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"

import os
from utils import acct_dir
from data import load_string
from data import save_string
from data import append_string


def set_pet_name(base_dir: str, nickname: str, domain: str,
                 handle: str, petname: str) -> bool:
    """Adds a new petname
    """
    if '@' not in handle:
        return False
    if ' ' in petname:
        petname = petname.replace(' ', '_')
    if handle.startswith('@'):
        handle = handle[1:]
    if petname.startswith('@'):
        petname = petname[1:]
    petnames_filename = acct_dir(base_dir, nickname, domain) + '/petnames.txt'
    entry = petname + ' ' + handle + '\n'

    # does this entry already exist?
    if os.path.isfile(petnames_filename):
        petnames_str: str = \
            load_string(petnames_filename,
                        'EX: set_pet_name unable to read ' + petnames_filename)
        if petnames_str is None:
            petnames_str = ''
        if entry in petnames_str:
            return True
        if ' ' + handle + '\n' in petnames_str:
            petnames_list = petnames_str.split('\n')
            new_petnames_str = ''
            for pet in petnames_list:
                if not pet.endswith(' ' + handle):
                    new_petnames_str += pet + '\n'
                else:
                    new_petnames_str += entry
            # save the updated petnames file
            if not save_string(new_petnames_str, petnames_filename,
                               'EX: set_pet_name unable to save ' +
                               petnames_filename):
                return False
            return True
        # entry does not exist in the petnames file
        if not append_string(entry, petnames_filename,
                             'EX: set_pet_name unable to append ' +
                             petnames_filename):
            return False
        return True

    # first entry
    if not save_string(entry, petnames_filename,
                       'EX: set_pet_name unable to write ' +
                       petnames_filename):
        return False
    return True


def get_pet_name(base_dir: str, nickname: str, domain: str,
                 handle: str) -> str:
    """Given a handle returns the petname
    """
    if '@' not in handle:
        return ''
    if handle.startswith('@'):
        handle = handle[1:]
    petnames_filename = acct_dir(base_dir, nickname, domain) + '/petnames.txt'

    if not os.path.isfile(petnames_filename):
        return ''
    petnames_str: str = \
        load_string(petnames_filename,
                    'EX: get_pet_name unable to read ' + petnames_filename)
    if petnames_str is None:
        petnames_str = ''
    if ' ' + handle + '\n' in petnames_str:
        petnames_list = petnames_str.split('\n')
        for pet in petnames_list:
            if pet.endswith(' ' + handle):
                return pet.replace(' ' + handle, '').strip()
    elif ' ' + handle.lower() + '\n' in petnames_str.lower():
        petnames_list = petnames_str.split('\n')
        handle = handle.lower()
        for pet in petnames_list:
            if pet.lower().endswith(' ' + handle):
                handle2 = pet.split(' ')[-1]
                return pet.replace(' ' + handle2, '').strip()
    return ''


def _get_pet_name_handle(base_dir: str, nickname: str, domain: str,
                         petname: str) -> str:
    """Given a petname returns the handle
    """
    if petname.startswith('@'):
        petname = petname[1:]
    petnames_filename = acct_dir(base_dir, nickname, domain) + '/petnames.txt'

    if not os.path.isfile(petnames_filename):
        return ''
    petnames_str: str = \
        load_string(petnames_filename,
                    'EX: _get_pet_name_handle unable to read ' +
                    petnames_filename)
    if petnames_str is None:
        petnames_str = ''
    if petname + ' ' in petnames_str:
        petnames_list = petnames_str.split('\n')
        for pet in petnames_list:
            if pet.startswith(petname + ' '):
                handle = pet.replace(petname + ' ', '').strip()
                return handle
    return ''


def resolve_petnames(base_dir: str, nickname: str, domain: str,
                     content: str) -> str:
    """Replaces petnames with their full handles
    """
    if not content:
        return content
    if ' ' not in content:
        return content
    words = content.strip().split(' ')
    for wrd in words:
        # check initial words beginning with @
        if not wrd.startswith('@'):
            break
        # does a petname handle exist for this?
        handle = _get_pet_name_handle(base_dir, nickname, domain, wrd)
        if not handle:
            continue
        # replace the petname with the handle
        content = content.replace(wrd + ' ', '@' + handle + ' ')
    return content
