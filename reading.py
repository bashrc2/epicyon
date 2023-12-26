__filename__ = "reading.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.4.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"


import os
from utils import get_content_from_post
from utils import has_object_dict
from utils import remove_id_ending
from utils import get_attributed_to
from utils import load_json
from utils import save_json
from utils import remove_html


def get_book_link_from_content(content: str) -> str:
    """ Returns a book link from the given content
    """
    if '/book/' not in content or \
       '://' not in content or \
       '"' not in content:
        return None
    sections = content.split('/book/')
    if '"' not in sections[0] or '"' not in sections[1]:
        return None
    previous_str = sections[0].split('"')[-1]
    if '://' not in previous_str:
        return None
    next_str = sections[1].split('"')[0]
    book_url = previous_str + '/book/' + next_str
    return book_url


def get_book_from_post(post_json_object: {}) -> {}:
    """ Returns a book details from the given post
    """
    if 'tag' not in post_json_object:
        return {}
    if not isinstance(post_json_object['tag'], list):
        return {}
    for tag_dict in post_json_object['tag']:
        if 'type' not in tag_dict:
            continue
        if not isinstance(tag_dict['type'], str):
            continue
        if tag_dict['type'] != 'Edition':
            continue
        if not tag_dict.get('href'):
            continue
        if not isinstance(tag_dict['href'], str):
            continue
        if not tag_dict.get('name'):
            continue
        if not isinstance(tag_dict['name'], str):
            continue
        tag_dict['name'] = tag_dict['name'].replace('@', '')
        return tag_dict
    return {}


def get_reading_status(post_json_object: {},
                       system_language: str,
                       languages_understood: [],
                       translate: {}) -> {}:
    """Returns any reading status from the content of a post
    """
    post_obj = post_json_object
    if has_object_dict(post_json_object):
        post_obj = post_json_object['object']

    content = get_content_from_post(post_json_object, system_language,
                                    languages_understood,
                                    "content")
    if not content:
        return {}
    book_url = get_book_link_from_content(content)
    if not book_url:
        return {}

    if not post_obj.get('id'):
        return {}
    if not isinstance(post_obj['id'], str):
        return {}

    # get the published date
    if not post_obj.get('published'):
        return {}
    if not isinstance(post_obj['published'], str):
        return {}
    published = post_obj['published']
    if post_obj.get('updated'):
        if isinstance(post_obj['updated'], str):
            published = post_obj['updated']

    if not post_obj.get('attributedTo'):
        return {}
    actor = get_attributed_to(post_obj['attributedTo'])
    if not actor:
        return {}

    # rating of a book
    if post_obj.get('rating'):
        rating = post_obj['rating']
        if isinstance(rating, (float, int)):
            translated_str = 'rated'
            if translate.get('rated'):
                translated_str = translate['rated']
            if translated_str in content or \
               'rated' in content:
                return {
                    'id': remove_id_ending(post_obj['id']),
                    'actor': actor,
                    'type': 'rated',
                    'href': book_url,
                    'rating': rating,
                    'published': published
                }

    # get the book details from a post tag
    book_dict = get_book_from_post(post_json_object)
    if not book_dict:
        return {}

    # want to read a book
    translated_str = 'wants to read'
    if translate.get('wants to read'):
        translated_str = translate['wants to read']
    if translated_str in content or \
       'wants to read' in content:
        book_dict['id'] = remove_id_ending(post_obj['id'])
        book_dict['actor'] = actor
        book_dict['type'] = 'want'
        book_dict['published'] = published
        return book_dict

    translated_str = 'finished reading'
    if translate.get('finished reading'):
        translated_str = translate['finished reading']
    if translated_str in content or \
       'finished reading' in content:
        book_dict['id'] = remove_id_ending(post_obj['id'])
        book_dict['actor'] = actor
        book_dict['type'] = 'finished'
        book_dict['published'] = published
        return book_dict

    return {}


def _add_book_to_reader(reader_books_json: {}, book_dict: {}) -> None:
    """Updates reader books
    """
    book_url = book_dict['href']
    book_event_type = book_dict['type']
    if not reader_books_json.get(book_url):
        reader_books_json[book_url] = {
            book_event_type: book_dict
        }
        return
    reader_books_json[book_url][book_event_type] = book_dict


def _add_reader_to_book(book_json: {}, book_dict: {}) -> None:
    """Updates book with a new reader
    """
    book_event_type = book_dict['type']
    actor = book_dict['actor']
    if not book_json.get(actor):
        book_json[actor] = {
            book_event_type: book_dict
        }
        if book_dict.get('name'):
            book_json['title'] = remove_html(book_dict['name'])
        return
    book_json[actor][book_event_type] = book_dict
    if book_dict.get('name'):
        book_json['title'] = remove_html(book_dict['name'])


def store_book_events(base_dir: str,
                      post_json_object: {},
                      system_language: str,
                      languages_understood: [],
                      translate: {},
                      debug: bool,
                      max_recent_books: int) -> bool:
    """Saves book events to file under accounts/reading/books
    and accounts/reading/readers
    """
    book_dict = get_reading_status(post_json_object,
                                   system_language,
                                   languages_understood,
                                   translate)
    if not book_dict:
        return False
    reading_path = base_dir + '/accounts/reading'
    if not os.path.isdir(reading_path):
        os.mkdir(reading_path)
    books_path = reading_path + '/books'
    if not os.path.isdir(books_path):
        os.mkdir(books_path)
    readers_path = reading_path + '/readers'
    if not os.path.isdir(readers_path):
        os.mkdir(readers_path)

    actor = book_dict['actor']
    book_url = remove_id_ending(book_dict['href'])

    reader_books_filename = \
        readers_path + '/' + actor.replace('/', '#') + '.json'
    reader_books_json = {}
    if os.path.isfile(reader_books_filename):
        reader_books_json = load_json(reader_books_filename)
    _add_book_to_reader(reader_books_json, book_dict)
    if not save_json(reader_books_json, reader_books_filename):
        return False

    book_id = book_url.replace('/', '#')
    book_filename = books_path + '/' + book_id + '.json'
    book_json = {}
    if os.path.isfile(book_filename):
        book_json = load_json(book_filename)
    _add_reader_to_book(book_json, book_dict)
    if not save_json(book_json, book_filename):
        return False

    # prepend to the recent books list
    recent_books_filename = base_dir + '/accounts/recent_books.txt'
    if os.path.isfile(recent_books_filename):
        try:
            with open(recent_books_filename, 'r+',
                      encoding='utf-8') as recent_file:
                content = recent_file.read()
                if book_id + '\n' not in content:
                    recent_file.seek(0, 0)
                    recent_file.write(book_id + '\n' + content)
                    if debug:
                        print('DEBUG: recent book added')
        except OSError as ex:
            print('WARN: Failed to write entry to recent books ' +
                  recent_books_filename + ' ' + str(ex))
    else:
        try:
            with open(recent_books_filename, 'w+',
                      encoding='utf-8') as recent_file:
                recent_file.write(book_id + '\n')
        except OSError:
            print('EX: unable to write recent books ' +
                  recent_books_filename)

    # deduplicate and limit the length of the recent books list
    if os.path.isfile(recent_books_filename):
        # load recent books as a list
        recent_lines = []
        try:
            with open(recent_books_filename, 'r',
                      encoding='utf-8') as recent_file:
                recent_lines = recent_file.read().split('\n')
        except OSError as ex:
            print('WARN: Failed to read recent books trim ' +
                  recent_books_filename + ' ' + str(ex))

        # deduplicate the list
        new_recent_lines = []
        for line in recent_lines:
            if line not in new_recent_lines:
                new_recent_lines.append(line)
        if len(new_recent_lines) < len(recent_lines):
            recent_lines = new_recent_lines
            try:
                with open(recent_books_filename, 'w+',
                          encoding='utf-8') as recent_file:
                    for line in recent_lines:
                        recent_file.write(line + '\n')
            except OSError:
                print('EX: unable to deduplicate recent books ' +
                      recent_books_filename)

        # remove excess lines from the list
        if len(recent_lines) > max_recent_books:
            try:
                with open(recent_books_filename, 'w+',
                          encoding='utf-8') as recent_file:
                    for ctr in range(max_recent_books):
                        recent_file.write(recent_lines[ctr] + '\n')
            except OSError:
                print('EX: unable to trim recent books ' +
                      recent_books_filename)
    return True
