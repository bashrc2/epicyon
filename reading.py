__filename__ = "reading.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.4.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"


import os
from collections import OrderedDict
from utils import get_content_from_post
from utils import has_object_dict
from utils import remove_id_ending
from utils import get_attributed_to
from utils import load_json
from utils import save_json
from utils import remove_html
from utils import get_image_extensions
from utils import date_epoch
from utils import date_from_string_format


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


def _get_book_image_from_post(post_json_object: {}) -> str:
    """ Returns a book image from the given post
    """
    if 'attachment' not in post_json_object:
        return ''
    if not isinstance(post_json_object['attachment'], list):
        return ''
    extensions = get_image_extensions()
    for attach_dict in post_json_object['attachment']:
        if not isinstance(attach_dict, dict):
            continue
        if 'url' not in attach_dict:
            continue
        if not isinstance(attach_dict['url'], str):
            continue
        for ext in extensions:
            if attach_dict['url'].endswith('.' + ext):
                return attach_dict['url']
    return ''


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

    book_image_url = _get_book_image_from_post(post_obj)

    # rating of a book
    if post_obj.get('rating'):
        rating = post_obj['rating']
        if isinstance(rating, (float, int)):
            translated_str = 'rated'
            if translate.get('rated'):
                translated_str = translate['rated']
            if translated_str in content or \
               'rated' in content:
                book_dict = {
                    'id': remove_id_ending(post_obj['id']),
                    'actor': actor,
                    'type': 'rated',
                    'href': book_url,
                    'rating': rating,
                    'published': published
                }
                if book_image_url:
                    book_dict['image_url'] = book_image_url
                return book_dict

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
        if book_image_url:
            book_dict['image_url'] = book_image_url
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
        if book_image_url:
            book_dict['image_url'] = book_image_url
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
    if not book_dict.get('published'):
        return
    if 'timeline' not in reader_books_json:
        reader_books_json['timeline'] = {}
    published = book_dict['published']
    if book_dict.get('updated'):
        published = book_dict['updated']
    post_time_object = \
        date_from_string_format(published, ["%Y-%m-%dT%H:%M:%S%z"])
    if post_time_object:
        baseline_time = date_epoch()
        days_diff = post_time_object - baseline_time
        post_days_since_epoch = days_diff.days
        reader_books_json['timeline'][post_days_since_epoch] = book_url


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


def _update_recent_books_list(base_dir: str, book_id: str,
                              debug: bool) -> None:
    """prepend a book to the recent books list
    """
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


def _deduplicate_recent_books_list(base_dir: str,
                                   max_recent_books: int) -> None:
    """ Deduplicate and limit the length of the recent books list
    """
    recent_books_filename = base_dir + '/accounts/recent_books.txt'
    if not os.path.isfile(recent_books_filename):
        return

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
        result = ''
        for line in recent_lines:
            result += line + '\n'
        try:
            with open(recent_books_filename, 'w+',
                      encoding='utf-8') as recent_file:
                recent_file.write(result)
        except OSError:
            print('EX: unable to deduplicate recent books ' +
                  recent_books_filename)

    # remove excess lines from the list
    if len(recent_lines) > max_recent_books:
        result = ''
        for ctr in range(max_recent_books):
            result += recent_lines[ctr] + '\n'
        try:
            with open(recent_books_filename, 'w+',
                      encoding='utf-8') as recent_file:
                recent_file.write(result)
        except OSError:
            print('EX: unable to trim recent books ' +
                  recent_books_filename)


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

    _update_recent_books_list(base_dir, book_id, debug)
    _deduplicate_recent_books_list(base_dir, max_recent_books)

    return True


def html_profile_book_list(base_dir: str, actor: str, no_of_books: int,
                           translate: {}) -> str:
    """Returns html for displaying a list of books on a profile screen
    """
    reading_path = base_dir + '/accounts/reading'
    readers_path = reading_path + '/readers'
    reader_books_filename = \
        readers_path + '/' + actor.replace('/', '#') + '.json'
    reader_books_json = {}
    if not os.path.isfile(reader_books_filename):
        return ''
    reader_books_json = load_json(reader_books_filename)
    if not reader_books_json.get('timeline'):
        return ''
    # sort the timeline in descending order
    recent_books_json = \
        OrderedDict(sorted(reader_books_json['timeline'].items(),
                           reverse=True))
    html_str = '<div class="book_list_section">\n'
    html_str += '  <ul class="book_list">\n'
    ctr = 0
    for _, book_url in recent_books_json.items():
        if not reader_books_json.get(book_url):
            continue
        book_rating = None
        book_wanted = False
        book_finished = False
        for event_type in ('want', 'finished', 'rated'):
            if not reader_books_json[book_url].get(event_type):
                continue
            book_dict = reader_books_json[book_url][event_type]
            if book_dict.get('name'):
                book_title = book_dict['name']
            if book_dict.get('image_url'):
                book_image_url = book_dict['image_url']
            if event_type == 'rated':
                book_rating = book_dict['rating']
            elif event_type == 'want':
                book_wanted = True
            elif event_type == 'finished':
                book_finished = True
        if book_title and book_image_url:
            book_title = remove_html(book_title)
            html_str += '    <li class="book_event">\n'
            html_str += '      <span class="book_span">\n'
            html_str += '        <div class="book_span_div">\n'

            # book image
            html_str += '          <a href="' + book_url + \
                '" target="_blank" rel="nofollow noopener noreferrer">\n'
            html_str += '            <div class="book_image_div">\n'
            html_str += '              <img src="' + book_image_url + '" ' + \
                'alt="' + book_title + '">\n'
            html_str += '            </div>\n'
            html_str += '          </a>\n'

            # book details
            html_str += '          <div class="book_details_div">\n'
            html_str += '            <a href="' + book_url + \
                '" target="_blank" rel="nofollow noopener noreferrer">\n'
            html_str += '              <b>' + book_title.title() + '</b></a>\n'
            if book_finished:
                html_str += '            <br>' + \
                    translate['finished reading'].title() + '\n'
            if book_wanted:
                html_str += '            <br>' + \
                    translate['Wanted'] + '\n'
            if book_rating is not None:
                html_str += '            <br>'
                for _ in range(int(book_rating)):
                    html_str += '⭐'
                html_str += ' (' + str(book_rating) + ')'
            html_str += '          </div>\n'

            html_str += '        </div>\n'
            html_str += '      </span>\n'
            html_str += '    </li>\n'
        ctr += 1
        if ctr >= no_of_books:
            break
    html_str += '  </ul>\n'
    html_str += '</div>\n'
    return html_str
