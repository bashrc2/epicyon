__filename__ = "newswire.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.3.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Web Interface Columns"

import os
import json
import requests
import random
from socket import error as SocketError
import errno
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from collections import OrderedDict
from utils import valid_post_date
from categories import set_hashtag_category
from utils import get_domain_from_actor
from utils import valid_hash_tag
from utils import dangerous_svg
from utils import get_fav_filename_from_url
from utils import get_base_content_from_post
from utils import has_object_dict
from utils import first_paragraph_from_string
from utils import is_public_post
from utils import locate_post
from utils import load_json
from utils import save_json
from utils import is_suspended
from utils import contains_invalid_chars
from utils import remove_html
from utils import is_account_dir
from utils import acct_dir
from utils import local_actor_url
from blocking import is_blocked_domain
from blocking import is_blocked_hashtag
from filters import is_filtered
from session import download_image_any_mime_type


def _remove_cdata(text: str) -> str:
    """Removes any CDATA from the given text
    """
    if 'CDATA[' in text:
        text = text.split('CDATA[')[1]
        if ']' in text:
            text = text.split(']')[0]
    return text


def rss2header(http_prefix: str,
               nickname: str, domain_full: str,
               title: str, translate: {}) -> str:
    """Header for an RSS 2.0 feed
    """
    rss_str = \
        "<?xml version=\"1.0\" encoding=\"UTF-8\" ?>" + \
        "<rss version=\"2.0\">" + \
        '<channel>'

    if title.startswith('News'):
        rss_str += \
            '    <title>Newswire</title>' + \
            '    <link>' + http_prefix + '://' + domain_full + \
            '/newswire.xml' + '</link>'
    elif title.startswith('Site'):
        rss_str += \
            '    <title>' + domain_full + '</title>' + \
            '    <link>' + http_prefix + '://' + domain_full + \
            '/blog/rss.xml' + '</link>'
    else:
        rss_str += \
            '    <title>' + translate[title] + '</title>' + \
            '    <link>' + \
            local_actor_url(http_prefix, nickname, domain_full) + \
            '/rss.xml' + '</link>'
    return rss_str


def rss2footer() -> str:
    """Footer for an RSS 2.0 feed
    """
    rss_str = '</channel></rss>'
    return rss_str


def get_newswire_tags(text: str, max_tags: int) -> []:
    """Returns a list of hashtags found in the given text
    """
    if '#' not in text:
        return []
    if ' ' not in text:
        return []
    text_simplified = \
        text.replace(',', ' ').replace(';', ' ').replace('- ', ' ')
    text_simplified = text_simplified.replace('. ', ' ').strip()
    if text_simplified.endswith('.'):
        text_simplified = text_simplified[:len(text_simplified)-1]
    words = text_simplified.split(' ')
    tags = []
    for wrd in words:
        if not wrd.startswith('#'):
            continue
        if len(wrd) <= 1:
            continue
        if wrd in tags:
            continue
        tags.append(wrd)
        if len(tags) >= max_tags:
            break
    return tags


def limit_word_lengths(text: str, maxWordLength: int) -> str:
    """Limits the maximum length of words so that the newswire
    column cannot become too wide
    """
    if ' ' not in text:
        return text
    words = text.split(' ')
    result = ''
    for wrd in words:
        if len(wrd) > maxWordLength:
            wrd = wrd[:maxWordLength]
        if result:
            result += ' '
        result += wrd
    return result


def get_newswire_favicon_url(url: str) -> str:
    """Returns a favicon url from the given article link
    """
    if '://' not in url:
        return '/newswire_favicon.ico'
    if url.startswith('http://'):
        if not (url.endswith('.onion') or url.endswith('.i2p')):
            return '/newswire_favicon.ico'
    domain = url.split('://')[1]
    if '/' not in domain:
        return url + '/favicon.ico'
    domain = domain.split('/')[0]
    return url.split('://')[0] + '://' + domain + '/favicon.ico'


def _download_newswire_feed_favicon(session, base_dir: str,
                                    link: str, debug: bool) -> bool:
    """Downloads the favicon for the given feed link
    """
    fav_url = get_newswire_favicon_url(link)
    if '://' not in link:
        return False
    timeout_sec = 10
    image_data, mime_type = \
        download_image_any_mime_type(session, fav_url, timeout_sec, debug)
    if not image_data or not mime_type:
        return False

    # update the favicon url
    extensions_to_mime = {
        'ico': 'x-icon',
        'png': 'png',
        'jpg': 'jpeg',
        'jxl': 'jxl',
        'gif': 'gif',
        'avif': 'avif',
        'svg': 'svg+xml',
        'webp': 'webp'
    }
    for ext, mime_ext in extensions_to_mime.items():
        if 'image/' + mime_ext in mime_type:
            fav_url = fav_url.replace('.ico', '.' + ext)
            break

    # create cached favicons directory if needed
    if not os.path.isdir(base_dir + '/favicons'):
        os.mkdir(base_dir + '/favicons')

    # check svg for dubious scripts
    if fav_url.endswith('.svg'):
        image_data_str = str(image_data)
        if dangerous_svg(image_data_str, False):
            return False

    # save to the cache
    fav_filename = get_fav_filename_from_url(base_dir, fav_url)
    if os.path.isfile(fav_filename):
        return True
    try:
        with open(fav_filename, 'wb+') as fp_fav:
            fp_fav.write(image_data)
    except OSError:
        print('EX: failed writing favicon ' + fav_filename)
        return False

    return True


def _add_newswire_dict_entry(base_dir: str, domain: str,
                             newswire: {}, date_str: str,
                             title: str, link: str,
                             votes_status: str, post_filename: str,
                             description: str, moderated: bool,
                             mirrored: bool,
                             tags: [],
                             max_tags: int, session, debug: bool,
                             podcast_properties: {}) -> None:
    """Update the newswire dictionary
    """
    # remove any markup
    title = remove_html(title)
    description = remove_html(description)

    all_text = title + ' ' + description

    # check that none of the text is filtered against
    if is_filtered(base_dir, None, None, all_text):
        return

    title = limit_word_lengths(title, 13)

    if tags is None:
        tags = []

    # extract hashtags from the text of the feed post
    post_tags = get_newswire_tags(all_text, max_tags)

    # Include tags from podcast categories
    if podcast_properties:
        if podcast_properties.get('explicit'):
            if '#nsfw' not in post_tags:
                post_tags.append('#nsfw')

        post_tags += podcast_properties['categories']

    # combine the tags into a single list
    for tag in tags:
        if tag in post_tags:
            continue
        if len(post_tags) < max_tags:
            post_tags.append(tag)

    # check that no tags are blocked
    for tag in post_tags:
        if is_blocked_hashtag(base_dir, tag):
            return

    _download_newswire_feed_favicon(session, base_dir, link, debug)

    newswire[date_str] = [
        title,
        link,
        votes_status,
        post_filename,
        description,
        moderated,
        post_tags,
        mirrored,
        podcast_properties
    ]


def _valid_feed_date(pub_date: str, debug: bool = False) -> bool:
    # convert from YY-MM-DD HH:MM:SS+00:00 to
    # YY-MM-DDTHH:MM:SSZ
    post_date = pub_date.replace(' ', 'T').replace('+00:00', 'Z')
    return valid_post_date(post_date, 90, debug)


def parse_feed_date(pub_date: str, unique_string_identifier: str) -> str:
    """Returns a UTC date string based on the given date string
    This tries a number of formats to see which work
    """

    if ':00:00' in pub_date:
        # If this was published exactly on the hour then assign a
        # random minute and second to make this item relatively unique
        randgen = random.Random(unique_string_identifier)
        rand_min = randgen.randint(0, 59)
        rand_sec = randgen.randint(0, 59)
        replace_time_str = \
            ':' + str(rand_min).zfill(2) + ':' + str(rand_sec).zfill(2)
        pub_date = pub_date.replace(':00:00', replace_time_str)

    formats = ("%a, %d %b %Y %H:%M:%S %z",
               "%a, %d %b %Y %H:%M:%S Z",
               "%a, %d %b %Y %H:%M:%S GMT",
               "%a, %d %b %Y %H:%M:%S EST",
               "%a, %d %b %Y %H:%M:%S PST",
               "%a, %d %b %Y %H:%M:%S AST",
               "%a, %d %b %Y %H:%M:%S CST",
               "%a, %d %b %Y %H:%M:%S MST",
               "%a, %d %b %Y %H:%M:%S AKST",
               "%a, %d %b %Y %H:%M:%S HST",
               "%a, %d %b %Y %H:%M:%S UT",
<<<<<<< HEAD
               "%a, %d %b %Y %H:%M:%S Z",
               "%a, %d %b %Y %H:%M:%S GMT",
=======
>>>>>>> 619663a3c83d30b8856862a8b9b035b4513decc2
               "%Y-%m-%dT%H:%M:%SZ",
               "%Y-%m-%dT%H:%M:%S%z")
    published_date = None
    for date_format in formats:
        if ',' in pub_date and ',' not in date_format:
            continue
        if ',' not in pub_date and ',' in date_format:
            continue
        if 'Z' in pub_date and 'Z' not in date_format:
            continue
        if 'Z' not in pub_date and 'Z' in date_format:
            continue
        if 'EST' not in pub_date and 'EST' in date_format:
            continue
        if 'GMT' not in pub_date and 'GMT' in date_format:
            continue
        if 'EST' in pub_date and 'EST' not in date_format:
            continue
        if 'UT' not in pub_date and 'UT' in date_format:
            continue
        if 'UT' in pub_date and 'UT' not in date_format:
            continue

        try:
            published_date = datetime.strptime(pub_date, date_format)
        except BaseException:
            continue

        if published_date:
            if pub_date.endswith(' EST'):
                hours_added = timedelta(hours=5)
                published_date = published_date + hours_added
            break

    pub_date_str = None
    if published_date:
        offset = published_date.utcoffset()
        if offset:
            published_date = published_date - offset
        # convert local date to UTC
        published_date = published_date.replace(tzinfo=timezone.utc)
        pub_date_str = str(published_date)
        if not pub_date_str.endswith('+00:00'):
            pub_date_str += '+00:00'
    else:
        print('WARN: unrecognized date format: ' + pub_date)

    return pub_date_str


def load_hashtag_categories(base_dir: str, language: str) -> None:
    """Loads an rss file containing hashtag categories
    """
    hashtag_categories_filename = base_dir + '/categories.xml'
    if not os.path.isfile(hashtag_categories_filename):
        hashtag_categories_filename = \
            base_dir + '/defaultcategories/' + language + '.xml'
        if not os.path.isfile(hashtag_categories_filename):
            return

    with open(hashtag_categories_filename, 'r') as fp_cat:
        xml_str = fp_cat.read()
        _xml2str_to_hashtag_categories(base_dir, xml_str, 1024, True)


def _xml2str_to_hashtag_categories(base_dir: str, xml_str: str,
                                   max_categories_feedItem_size_kb: int,
                                   force: bool = False) -> None:
    """Updates hashtag categories based upon an rss feed
    """
    rss_items = xml_str.split('<item>')
    max_bytes = max_categories_feedItem_size_kb * 1024
    for rss_item in rss_items:
        if not rss_item:
            continue
        if len(rss_item) > max_bytes:
            print('WARN: rss categories feed item is too big')
            continue
        if '<title>' not in rss_item:
            continue
        if '</title>' not in rss_item:
            continue
        if '<description>' not in rss_item:
            continue
        if '</description>' not in rss_item:
            continue
        category_str = rss_item.split('<title>')[1]
        category_str = category_str.split('</title>')[0].strip()
        if not category_str:
            continue
        if 'CDATA' in category_str:
            continue
        hashtag_list_str = rss_item.split('<description>')[1]
        hashtag_list_str = hashtag_list_str.split('</description>')[0].strip()
        if not hashtag_list_str:
            continue
        if 'CDATA' in hashtag_list_str:
            continue
        hashtag_list = hashtag_list_str.split(' ')
        if not is_blocked_hashtag(base_dir, category_str):
            for hashtag in hashtag_list:
                set_hashtag_category(base_dir, hashtag, category_str,
                                     False, force)


def _get_podcast_categories(xml_item: str, xml_str: str) -> str:
    """ get podcast categories if they exist. These can be turned into hashtags
    """
    podcast_categories = []
    episode_category_tags = ['<itunes:category', '<category']

    for category_tag in episode_category_tags:
        item_str = xml_item
        if category_tag not in xml_item:
            if category_tag not in xml_str:
                continue
            item_str = xml_str

        category_list = item_str.split(category_tag)
        first_category = True
        for episode_category in category_list:
            if first_category:
                first_category = False
                continue

            if 'text="' in episode_category:
                episode_category = episode_category.split('text="')[1]
                if '"' in episode_category:
                    episode_category = episode_category.split('"')[0]
                    episode_category = \
                        episode_category.lower().replace(' ', '')
                    episode_category = episode_category.replace('#', '')
                    if episode_category not in podcast_categories:
                        if valid_hash_tag(episode_category):
                            podcast_categories.append('#' + episode_category)
                continue

            if '>' in episode_category:
                episode_category = episode_category.split('>')[1]
                if '<' in episode_category:
                    episode_category = episode_category.split('<')[0]
                    episode_category = \
                        episode_category.lower().replace(' ', '')
                    episode_category = episode_category.replace('#', '')
                    if episode_category not in podcast_categories:
                        if valid_hash_tag(episode_category):
                            podcast_categories.append('#' + episode_category)

    return podcast_categories


def _valid_podcast_entry(base_dir: str, key: str, entry: {}) -> bool:
    """Is the given podcast namespace entry valid?
    https://github.com/Podcastindex-org/podcast-namespace/
    blob/main/proposal-docs/social/social.md#socialinteract-element
    """
    if key == 'socialInteract':
        if not entry.get('protocol'):
            return False
        if not entry.get('text'):
            return False
        if entry['protocol'].tolower() != 'activitypub':
            return False
        post_url = entry['text']
        if '://' not in post_url:
            return False
        post_domain, post_port = get_domain_from_actor(post_url)
        if not post_domain:
            return False
        if is_blocked_domain(base_dir, post_domain):
            return False
    return True


def xml_podcast_to_dict(base_dir: str, xml_item: str, xml_str: str) -> {}:
    """podcasting extensions for RSS feeds
    See https://github.com/Podcastindex-org/podcast-namespace/
    blob/main/docs/1.0.md
    https://github.com/Podcastindex-org/podcast-namespace/
    blob/main/proposal-docs/social/social.md#socialinteract-element
    """
    if '<podcast:' not in xml_item:
        if '<itunes:' not in xml_item:
            if '<media:thumbnail' not in xml_item:
                return {}

    podcast_properties = {
        "locations": [],
        "persons": [],
        "soundbites": [],
        "transcripts": [],
        "valueRecipients": [],
        "trailers": [],
        "socialInteract": []
    }

    pod_lines = xml_item.split('<podcast:')
    ctr = 0
    for pod_line in pod_lines:
        if ctr == 0 or '>' not in pod_line:
            ctr += 1
            continue
        if ' ' not in pod_line.split('>')[0]:
            pod_key = pod_line.split('>')[0].strip()
            pod_val = pod_line.split('>', 1)[1].strip()
            if '<' in pod_val:
                pod_val = pod_val.split('<')[0]
            podcast_properties[pod_key] = pod_val
            ctr += 1
            continue
        pod_key = pod_line.split(' ')[0]

        pod_fields = (
            'url', 'geo', 'osm', 'type', 'method', 'group',
            'owner', 'srcset', 'img', 'role', 'address', 'suggested',
            'startTime', 'duration', 'href', 'name', 'pubdate',
            'length', 'season', 'email', 'platform', 'protocol',
            'accountId', 'priority'
        )
        pod_entry = {}
        for pod_field in pod_fields:
            if pod_field + '="' not in pod_line:
                continue
            pod_str = pod_line.split(pod_field + '="')[1]
            if '"' not in pod_str:
                continue
            pod_val = pod_str.split('"')[0]
            pod_entry[pod_field] = pod_val

        pod_text = pod_line.split('>')[1]
        if '<' in pod_text:
            pod_text = pod_text.split('<')[0].strip()
            if pod_text:
                pod_entry['text'] = pod_text

        appended = False
        if pod_key + 's' in podcast_properties:
            if isinstance(podcast_properties[pod_key + 's'], list):
                podcast_properties[pod_key + 's'].append(pod_entry)
                appended = True
        if not appended:
            # if there are repeated keys then only use the first one
            if not podcast_properties.get(pod_key):
                if _valid_podcast_entry(base_dir, pod_key, pod_entry):
                    podcast_properties[pod_key] = pod_entry
        ctr += 1

    # get the image for the podcast, if it exists
    podcast_episode_image = None
    episode_image_tags = ['<itunes:image', '<media:thumbnail']
    for image_tag in episode_image_tags:
        item_str = xml_item
        if image_tag not in xml_item:
            if image_tag not in xml_str:
                continue
            item_str = xml_str

        episode_image = item_str.split(image_tag)[1]
        if image_tag + ' ' in item_str and '>' in episode_image:
            episode_image = episode_image.split('>')[0]

        if 'href="' in episode_image:
            episode_image = episode_image.split('href="')[1]
            if '"' in episode_image:
                episode_image = episode_image.split('"')[0]
                podcast_episode_image = episode_image
                break
        elif 'url="' in episode_image:
            episode_image = episode_image.split('url="')[1]
            if '"' in episode_image:
                episode_image = episode_image.split('"')[0]
                podcast_episode_image = episode_image
                break
        elif '>' in episode_image:
            episode_image = episode_image.split('>')[1]
            if '<' in episode_image:
                episode_image = episode_image.split('<')[0]
                if '://' in episode_image and '.' in episode_image:
                    podcast_episode_image = episode_image
                    break

    # get categories if they exist. These can be turned into hashtags
    podcast_categories = _get_podcast_categories(xml_item, xml_str)

    if podcast_episode_image:
        podcast_properties['image'] = podcast_episode_image
        podcast_properties['categories'] = podcast_categories

        if '<itunes:explicit>Y' in xml_item or \
           '<itunes:explicit>T' in xml_item or \
           '<itunes:explicit>1' in xml_item:
            podcast_properties['explicit'] = True
        else:
            podcast_properties['explicit'] = False
    else:
        if '<podcast:' not in xml_item:
            return {}

    return podcast_properties


def get_link_from_rss_item(rss_item: str) -> (str, str):
    """Extracts rss link from rss item string
    """
    mime_type = None

    if '<enclosure ' in rss_item:
        # get link from audio or video enclosure
        enclosure = rss_item.split('<enclosure ')[1]
        if '>' in enclosure:
            enclosure = enclosure.split('>')[0]
            if ' type="' in enclosure:
                mime_type = enclosure.split(' type="')[1]
                if '"' in mime_type:
                    mime_type = mime_type.split('"')[0]
            if 'url="' in enclosure and \
               ('"audio/' in enclosure or '"video/' in enclosure):
                link_str = enclosure.split('url="')[1]
                if '"' in link_str:
                    link = link_str.split('"')[0]
                    if '://' in link:
                        return link, mime_type

    if '<link>' in rss_item and '</link>' in rss_item:
        link = rss_item.split('<link>')[1]
        link = link.split('</link>')[0]
        if '://' not in link:
            return None, None
    elif '<link ' in rss_item:
        link_str = rss_item.split('<link ')[1]
        if '>' in link_str:
            link_str = link_str.split('>')[0]
            if 'href="' in link_str:
                link_str = link_str.split('href="')[1]
                if '"' in link_str:
                    link = link_str.split('"')[0]

    return link, mime_type


def _xml2str_to_dict(base_dir: str, domain: str, xml_str: str,
                     moderated: bool, mirrored: bool,
                     max_posts_per_source: int,
                     max_feed_item_size_kb: int,
                     max_categories_feedItem_size_kb: int,
                     session, debug: bool) -> {}:
    """Converts an xml RSS 2.0 string to a dictionary
    """
    if '<item>' not in xml_str:
        return {}
    result = {}

    # is this an rss feed containing hashtag categories?
    if '<title>#categories</title>' in xml_str:
        _xml2str_to_hashtag_categories(base_dir, xml_str,
                                       max_categories_feedItem_size_kb)
        return {}

    rss_items = xml_str.split('<item>')
    post_ctr = 0
    max_bytes = max_feed_item_size_kb * 1024
    first_item = True
    for rss_item in rss_items:
        if first_item:
            first_item = False
            continue
        if not rss_item:
            continue
        if len(rss_item) > max_bytes:
            print('WARN: rss feed item is too big')
            continue
        if '<title>' not in rss_item:
            continue
        if '</title>' not in rss_item:
            continue
        if '<link' not in rss_item:
            continue
        if '<pubDate>' not in rss_item:
            continue
        if '</pubDate>' not in rss_item:
            continue

        title = rss_item.split('<title>')[1]
        title = _remove_cdata(title.split('</title>')[0])
        title = remove_html(title)

        description = ''
        if '<description>' in rss_item and '</description>' in rss_item:
            description = rss_item.split('<description>')[1]
            description = remove_html(description.split('</description>')[0])
        else:
            if '<media:description>' in rss_item and \
               '</media:description>' in rss_item:
                description = rss_item.split('<media:description>')[1]
                description = description.split('</media:description>')[0]
                description = remove_html(description)

        link, link_mime_type = get_link_from_rss_item(rss_item)
        if not link:
            continue

        item_domain = link.split('://')[1]
        if '/' in item_domain:
            item_domain = item_domain.split('/')[0]

        if is_blocked_domain(base_dir, item_domain):
            continue
        pub_date = rss_item.split('<pubDate>')[1]
        pub_date = pub_date.split('</pubDate>')[0]

        unique_string_identifier = title + ' ' + link
        pub_date_str = parse_feed_date(pub_date, unique_string_identifier)
        if pub_date_str:
            if _valid_feed_date(pub_date_str):
                post_filename = ''
                votes_status = []
                podcast_properties = \
                    xml_podcast_to_dict(base_dir, rss_item, xml_str)
                if podcast_properties:
                    podcast_properties['linkMimeType'] = link_mime_type
                _add_newswire_dict_entry(base_dir, domain,
                                         result, pub_date_str,
                                         title, link,
                                         votes_status, post_filename,
                                         description, moderated,
                                         mirrored, [], 32, session, debug,
                                         podcast_properties)
                post_ctr += 1
                if post_ctr >= max_posts_per_source:
                    break
    if post_ctr > 0:
        print('Added ' + str(post_ctr) + ' rss 2.0 feed items to newswire')
    return result


def _xml1str_to_dict(base_dir: str, domain: str, xml_str: str,
                     moderated: bool, mirrored: bool,
                     max_posts_per_source: int,
                     max_feed_item_size_kb: int,
                     max_categories_feedItem_size_kb: int,
                     session, debug: bool) -> {}:
    """Converts an xml RSS 1.0 string to a dictionary
    https://validator.w3.org/feed/docs/rss1.html
    """
    item_str = '<item'
    if item_str not in xml_str:
        return {}
    result = {}

    # is this an rss feed containing hashtag categories?
    if '<title>#categories</title>' in xml_str:
        _xml2str_to_hashtag_categories(base_dir, xml_str,
                                       max_categories_feedItem_size_kb)
        return {}

    rss_items = xml_str.split(item_str)
    post_ctr = 0
    max_bytes = max_feed_item_size_kb * 1024
    first_item = True
    for rss_item in rss_items:
        if first_item:
            first_item = False
            continue
        if not rss_item:
            continue
        if len(rss_item) > max_bytes:
            print('WARN: rss 1.0 feed item is too big')
            continue
        if rss_item.startswith('s>'):
            continue
        if '<title>' not in rss_item:
            continue
        if '</title>' not in rss_item:
            continue
        if '<link' not in rss_item:
            continue
        if '<dc:date>' not in rss_item:
            continue
        if '</dc:date>' not in rss_item:
            continue
        title = rss_item.split('<title>')[1]
        title = _remove_cdata(title.split('</title>')[0])
        title = remove_html(title)
        description = ''
        if '<description>' in rss_item and '</description>' in rss_item:
            description = rss_item.split('<description>')[1]
            description = remove_html(description.split('</description>')[0])
        else:
            if '<media:description>' in rss_item and \
               '</media:description>' in rss_item:
                description = rss_item.split('<media:description>')[1]
                description = description.split('</media:description>')[0]
                description = remove_html(description)

        link, link_mime_type = get_link_from_rss_item(rss_item)
        if not link:
            continue

        item_domain = link.split('://')[1]
        if '/' in item_domain:
            item_domain = item_domain.split('/')[0]

        if is_blocked_domain(base_dir, item_domain):
            continue
        pub_date = rss_item.split('<dc:date>')[1]
        pub_date = pub_date.split('</dc:date>')[0]

        unique_string_identifier = title + ' ' + link
        pub_date_str = parse_feed_date(pub_date, unique_string_identifier)
        if pub_date_str:
            if _valid_feed_date(pub_date_str):
                post_filename = ''
                votes_status = []
                podcast_properties = \
                    xml_podcast_to_dict(base_dir, rss_item, xml_str)
                if podcast_properties:
                    podcast_properties['linkMimeType'] = link_mime_type
                _add_newswire_dict_entry(base_dir, domain,
                                         result, pub_date_str,
                                         title, link,
                                         votes_status, post_filename,
                                         description, moderated,
                                         mirrored, [], 32, session, debug,
                                         podcast_properties)
                post_ctr += 1
                if post_ctr >= max_posts_per_source:
                    break
    if post_ctr > 0:
        print('Added ' + str(post_ctr) + ' rss 1.0 feed items to newswire')
    return result


def _atom_feed_to_dict(base_dir: str, domain: str, xml_str: str,
                       moderated: bool, mirrored: bool,
                       max_posts_per_source: int,
                       max_feed_item_size_kb: int,
                       session, debug: bool) -> {}:
    """Converts an atom feed string to a dictionary
    """
    if '<entry>' not in xml_str:
        return {}
    result = {}
    atom_items = xml_str.split('<entry>')
    post_ctr = 0
    max_bytes = max_feed_item_size_kb * 1024
    first_item = True
    for atom_item in atom_items:
        if first_item:
            first_item = False
            continue
        if not atom_item:
            continue
        if len(atom_item) > max_bytes:
            print('WARN: atom feed item is too big')
            continue
        if '<title>' not in atom_item:
            continue
        if '</title>' not in atom_item:
            continue
        if '<link' not in atom_item:
            continue
        if '<updated>' not in atom_item:
            continue
        if '</updated>' not in atom_item:
            continue
        title = atom_item.split('<title>')[1]
        title = _remove_cdata(title.split('</title>')[0])
        title = remove_html(title)
        description = ''
        if '<summary>' in atom_item and '</summary>' in atom_item:
            description = atom_item.split('<summary>')[1]
            description = remove_html(description.split('</summary>')[0])
        else:
            if '<media:description>' in atom_item and \
               '</media:description>' in atom_item:
                description = atom_item.split('<media:description>')[1]
                description = description.split('</media:description>')[0]
                description = remove_html(description)

        link, link_mime_type = get_link_from_rss_item(atom_item)
        if not link:
            continue

        item_domain = link.split('://')[1]
        if '/' in item_domain:
            item_domain = item_domain.split('/')[0]

        if is_blocked_domain(base_dir, item_domain):
            continue
        pub_date = atom_item.split('<updated>')[1]
        pub_date = pub_date.split('</updated>')[0]

        unique_string_identifier = title + ' ' + link
        pub_date_str = parse_feed_date(pub_date, unique_string_identifier)
        if pub_date_str:
            if _valid_feed_date(pub_date_str):
                post_filename = ''
                votes_status = []
                podcast_properties = \
                    xml_podcast_to_dict(base_dir, atom_item, xml_str)
                if podcast_properties:
                    podcast_properties['linkMimeType'] = link_mime_type
                _add_newswire_dict_entry(base_dir, domain,
                                         result, pub_date_str,
                                         title, link,
                                         votes_status, post_filename,
                                         description, moderated,
                                         mirrored, [], 32, session, debug,
                                         podcast_properties)
                post_ctr += 1
                if post_ctr >= max_posts_per_source:
                    break
    if post_ctr > 0:
        print('Added ' + str(post_ctr) + ' atom feed items to newswire')
    return result


def _json_feed_v1to_dict(base_dir: str, domain: str, xml_str: str,
                         moderated: bool, mirrored: bool,
                         max_posts_per_source: int,
                         max_feed_item_size_kb: int,
                         session, debug: bool) -> {}:
    """Converts a json feed string to a dictionary
    See https://jsonfeed.org/version/1.1
    """
    if '"items"' not in xml_str:
        return {}
    try:
        feed_json = json.loads(xml_str)
    except BaseException:
        print('EX: _json_feed_v1to_dict unable to load json ' + str(xml_str))
        return {}
    max_bytes = max_feed_item_size_kb * 1024
    if not feed_json.get('version'):
        return {}
    if not feed_json['version'].startswith('https://jsonfeed.org/version/1'):
        return {}
    if not feed_json.get('items'):
        return {}
    if not isinstance(feed_json['items'], list):
        return {}
    post_ctr = 0
    result = {}
    for json_feed_item in feed_json['items']:
        if not json_feed_item:
            continue
        if not isinstance(json_feed_item, dict):
            continue
        if not json_feed_item.get('url'):
            continue
        if not isinstance(json_feed_item['url'], str):
            continue
        if not json_feed_item.get('date_published'):
            if not json_feed_item.get('date_modified'):
                continue
        if not json_feed_item.get('content_text'):
            if not json_feed_item.get('content_html'):
                continue
        if json_feed_item.get('content_html'):
            if not isinstance(json_feed_item['content_html'], str):
                continue
            title = remove_html(json_feed_item['content_html'])
        else:
            if not isinstance(json_feed_item['content_text'], str):
                continue
            title = remove_html(json_feed_item['content_text'])
        if len(title) > max_bytes:
            print('WARN: json feed title is too long')
            continue
        description = ''
        if json_feed_item.get('description'):
            if not isinstance(json_feed_item['description'], str):
                continue
            description = remove_html(json_feed_item['description'])
            if len(description) > max_bytes:
                print('WARN: json feed description is too long')
                continue
            if json_feed_item.get('tags'):
                if isinstance(json_feed_item['tags'], list):
                    for tag_name in json_feed_item['tags']:
                        if not isinstance(tag_name, str):
                            continue
                        if ' ' in tag_name:
                            continue
                        if not tag_name.startswith('#'):
                            tag_name = '#' + tag_name
                        if tag_name not in description:
                            description += ' ' + tag_name

        link = json_feed_item['url']
        if '://' not in link:
            continue
        if len(link) > max_bytes:
            print('WARN: json feed link is too long')
            continue
        item_domain = link.split('://')[1]
        if '/' in item_domain:
            item_domain = item_domain.split('/')[0]
        if is_blocked_domain(base_dir, item_domain):
            continue
        if json_feed_item.get('date_published'):
            if not isinstance(json_feed_item['date_published'], str):
                continue
            pub_date = json_feed_item['date_published']
        else:
            if not isinstance(json_feed_item['date_modified'], str):
                continue
            pub_date = json_feed_item['date_modified']

        unique_string_identifier = title + ' ' + link
        pub_date_str = parse_feed_date(pub_date, unique_string_identifier)
        if pub_date_str:
            if _valid_feed_date(pub_date_str):
                post_filename = ''
                votes_status = []
                _add_newswire_dict_entry(base_dir, domain,
                                         result, pub_date_str,
                                         title, link,
                                         votes_status, post_filename,
                                         description, moderated,
                                         mirrored, [], 32, session, debug,
                                         None)
                post_ctr += 1
                if post_ctr >= max_posts_per_source:
                    break
    if post_ctr > 0:
        print('Added ' + str(post_ctr) +
              ' json feed items to newswire')
    return result


def _atom_feed_yt_to_dict(base_dir: str, domain: str, xml_str: str,
                          moderated: bool, mirrored: bool,
                          max_posts_per_source: int,
                          max_feed_item_size_kb: int,
                          session, debug: bool) -> {}:
    """Converts an atom-style YouTube feed string to a dictionary
    """
    if '<entry>' not in xml_str:
        return {}
    if is_blocked_domain(base_dir, 'www.youtube.com'):
        return {}
    result = {}
    atom_items = xml_str.split('<entry>')
    post_ctr = 0
    max_bytes = max_feed_item_size_kb * 1024
    first_entry = True
    for atom_item in atom_items:
        if first_entry:
            first_entry = False
            continue
        if not atom_item:
            continue
        if not atom_item.strip():
            continue
        if len(atom_item) > max_bytes:
            print('WARN: atom feed item is too big')
            continue
        if '<title>' not in atom_item:
            continue
        if '</title>' not in atom_item:
            continue
        if '<published>' not in atom_item:
            continue
        if '</published>' not in atom_item:
            continue
        if '<yt:videoId>' not in atom_item:
            continue
        if '</yt:videoId>' not in atom_item:
            continue
        title = atom_item.split('<title>')[1]
        title = _remove_cdata(title.split('</title>')[0])
        description = ''
        if '<media:description>' in atom_item and \
           '</media:description>' in atom_item:
            description = atom_item.split('<media:description>')[1]
            description = description.split('</media:description>')[0]
            description = remove_html(description)
        elif '<summary>' in atom_item and '</summary>' in atom_item:
            description = atom_item.split('<summary>')[1]
            description = description.split('</summary>')[0]
            description = remove_html(description)

        link, _ = get_link_from_rss_item(atom_item)
        if not link:
            link = atom_item.split('<yt:videoId>')[1]
            link = link.split('</yt:videoId>')[0]
            link = 'https://www.youtube.com/watch?v=' + link.strip()
        if not link:
            continue

        pub_date = atom_item.split('<published>')[1]
        pub_date = pub_date.split('</published>')[0]

        unique_string_identifier = title + ' ' + link
        pub_date_str = parse_feed_date(pub_date, unique_string_identifier)
        if pub_date_str:
            if _valid_feed_date(pub_date_str):
                post_filename = ''
                votes_status = []
                podcast_properties = \
                    xml_podcast_to_dict(base_dir, atom_item, xml_str)
                if podcast_properties:
                    podcast_properties['linkMimeType'] = 'video/youtube'
                _add_newswire_dict_entry(base_dir, domain,
                                         result, pub_date_str,
                                         title, link,
                                         votes_status, post_filename,
                                         description, moderated, mirrored,
                                         [], 32, session, debug,
                                         podcast_properties)
                post_ctr += 1
                if post_ctr >= max_posts_per_source:
                    break
    if post_ctr > 0:
        print('Added ' + str(post_ctr) + ' YouTube feed items to newswire')
    return result


def _xml_str_to_dict(base_dir: str, domain: str, xml_str: str,
                     moderated: bool, mirrored: bool,
                     max_posts_per_source: int,
                     max_feed_item_size_kb: int,
                     max_categories_feedItem_size_kb: int,
                     session, debug: bool) -> {}:
    """Converts an xml string to a dictionary
    """
    if '<yt:videoId>' in xml_str and '<yt:channelId>' in xml_str:
        print('YouTube feed: reading')
        return _atom_feed_yt_to_dict(base_dir, domain,
                                     xml_str, moderated, mirrored,
                                     max_posts_per_source,
                                     max_feed_item_size_kb,
                                     session, debug)
    if 'rss version="2.0"' in xml_str:
        return _xml2str_to_dict(base_dir, domain,
                                xml_str, moderated, mirrored,
                                max_posts_per_source, max_feed_item_size_kb,
                                max_categories_feedItem_size_kb,
                                session, debug)
    if '<?xml version="1.0"' in xml_str:
        return _xml1str_to_dict(base_dir, domain,
                                xml_str, moderated, mirrored,
                                max_posts_per_source, max_feed_item_size_kb,
                                max_categories_feedItem_size_kb,
                                session, debug)
    if 'xmlns="http://www.w3.org/2005/Atom"' in xml_str:
        return _atom_feed_to_dict(base_dir, domain,
                                  xml_str, moderated, mirrored,
                                  max_posts_per_source, max_feed_item_size_kb,
                                  session, debug)
    if 'https://jsonfeed.org/version/1' in xml_str:
        return _json_feed_v1to_dict(base_dir, domain,
                                    xml_str, moderated, mirrored,
                                    max_posts_per_source,
                                    max_feed_item_size_kb,
                                    session, debug)
    return {}


def _yt_channel_to_atom_feed(url: str) -> str:
    """Converts a YouTube channel url into an atom feed url
    """
    if 'youtube.com/channel/' not in url:
        return url
    channel_id = url.split('youtube.com/channel/')[1].strip()
    channel_url = \
        'https://www.youtube.com/feeds/videos.xml?channel_id=' + channel_id
    print('YouTube feed: ' + channel_url)
    return channel_url


def get_rss(base_dir: str, domain: str, session, url: str,
            moderated: bool, mirrored: bool,
            max_posts_per_source: int, max_feed_size_kb: int,
            max_feed_item_size_kb: int,
            max_categories_feedItem_size_kb: int, debug: bool) -> {}:
    """Returns an RSS url as a dict
    """
    if not isinstance(url, str):
        print('url: ' + str(url))
        print('ERROR: get_rss url should be a string')
        return None
    headers = {
        'Accept': 'text/xml, application/xml; charset=UTF-8'
    }
    params = None
    session_params = {}
    session_headers = {}
    if headers:
        session_headers = headers
    if params:
        session_params = params
    session_headers['User-Agent'] = \
        'Mozilla/5.0 (X11; Linux x86_64; rv:81.0) Gecko/20100101 Firefox/81.0'
    if not session:
        print('WARN: no session specified for get_rss')
    url = _yt_channel_to_atom_feed(url)
    try:
        result = \
            session.get(url, headers=session_headers, params=session_params)
        if result:
            if int(len(result.text) / 1024) < max_feed_size_kb and \
               not contains_invalid_chars(result.text):
                return _xml_str_to_dict(base_dir, domain, result.text,
                                        moderated, mirrored,
                                        max_posts_per_source,
                                        max_feed_item_size_kb,
                                        max_categories_feedItem_size_kb,
                                        session, debug)
            else:
                print('WARN: feed is too large, ' +
                      'or contains invalid characters: ' + url)
        else:
            print('WARN: no result returned for feed ' + url)
    except requests.exceptions.RequestException as ex:
        print('WARN: get_rss failed\nurl: ' + str(url) + ', ' +
              'headers: ' + str(session_headers) + ', ' +
              'params: ' + str(session_params) + ', ' + str(ex))
    except ValueError as ex:
        print('WARN: get_rss failed\nurl: ' + str(url) + ', ' +
              'headers: ' + str(session_headers) + ', ' +
              'params: ' + str(session_params) + ', ' + str(ex))
    except SocketError as ex:
        if ex.errno == errno.ECONNRESET:
            print('WARN: connection was reset during get_rss ' + str(ex))
        else:
            print('WARN: get_rss, ' + str(ex))
    return None


def get_rs_sfrom_dict(base_dir: str, newswire: {},
                      http_prefix: str, domain_full: str,
                      title: str, translate: {}) -> str:
    """Returns an rss feed from the current newswire dict.
    This allows other instances to subscribe to the same newswire
    """
    rss_str = rss2header(http_prefix,
                         None, domain_full,
                         'Newswire', translate)
    if not newswire:
        return ''
    for published, fields in newswire.items():
        if '+00:00' in published:
            published = published.replace('+00:00', 'Z').strip()
            published = published.replace(' ', 'T')
        else:
            published_with_offset = \
                datetime.strptime(published, "%Y-%m-%d %H:%M:%S%z")
            published = published_with_offset.strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            pub_date = datetime.strptime(published, "%Y-%m-%dT%H:%M:%SZ")
        except BaseException as ex:
            print('WARN: Unable to convert date ' + published + ' ' + str(ex))
            continue
        rss_str += \
            '<item>\n' + \
            '  <title>' + fields[0] + '</title>\n'
        description = remove_html(first_paragraph_from_string(fields[4]))
        rss_str += '  <description>' + description + '</description>\n'
        url = fields[1]
        if '://' not in url:
            if domain_full not in url:
                url = http_prefix + '://' + domain_full + url
        rss_str += '  <link>' + url + '</link>\n'

        rss_date_str = pub_date.strftime("%a, %d %b %Y %H:%M:%S UT")
        rss_str += \
            '  <pubDate>' + rss_date_str + '</pubDate>\n' + \
            '</item>\n'
    rss_str += rss2footer()
    return rss_str


def _is_newswire_blog_post(post_json_object: {}) -> bool:
    """Is the given object a blog post?
    There isn't any difference between a blog post and a newswire blog post
    but we may here need to check for different properties than
    is_blog_post does
    """
    if not post_json_object:
        return False
    if not has_object_dict(post_json_object):
        return False
    if post_json_object['object'].get('summary') and \
       post_json_object['object'].get('url') and \
       post_json_object['object'].get('content') and \
       post_json_object['object'].get('published'):
        return is_public_post(post_json_object)
    return False


def _get_hashtags_from_post(post_json_object: {}) -> []:
    """Returns a list of any hashtags within a post
    """
    if not has_object_dict(post_json_object):
        return []
    if not post_json_object['object'].get('tag'):
        return []
    if not isinstance(post_json_object['object']['tag'], list):
        return []
    tags = []
    for tgname in post_json_object['object']['tag']:
        if not isinstance(tgname, dict):
            continue
        if not tgname.get('name'):
            continue
        if not tgname.get('type'):
            continue
        if tgname['type'] != 'Hashtag':
            continue
        if tgname['name'] not in tags:
            tags.append(tgname['name'])
    return tags


def _add_account_blogs_to_newswire(base_dir: str, nickname: str, domain: str,
                                   newswire: {},
                                   max_blogs_per_account: int,
                                   index_filename: str,
                                   max_tags: int, system_language: str,
                                   session, debug: bool) -> None:
    """Adds blogs for the given account to the newswire
    """
    if not os.path.isfile(index_filename):
        return
    # local blog entries are unmoderated by default
    moderated = False

    # local blogs can potentially be moderated
    moderated_filename = \
        acct_dir(base_dir, nickname, domain) + '/.newswiremoderated'
    if os.path.isfile(moderated_filename):
        moderated = True

    with open(index_filename, 'r') as index_file:
        post_filename = 'start'
        ctr = 0
        while post_filename:
            post_filename = index_file.readline()
            if post_filename:
                # if this is a full path then remove the directories
                if '/' in post_filename:
                    post_filename = post_filename.split('/')[-1]

                # filename of the post without any extension or path
                # This should also correspond to any index entry in
                # the posts cache
                post_url = \
                    post_filename.replace('\n', '').replace('\r', '')
                post_url = post_url.replace('.json', '').strip()

                # read the post from file
                full_post_filename = \
                    locate_post(base_dir, nickname,
                                domain, post_url, False)
                if not full_post_filename:
                    print('Unable to locate post for newswire ' + post_url)
                    ctr += 1
                    if ctr >= max_blogs_per_account:
                        break
                    continue

                post_json_object = None
                if full_post_filename:
                    post_json_object = load_json(full_post_filename)
                if _is_newswire_blog_post(post_json_object):
                    published = post_json_object['object']['published']
                    published = published.replace('T', ' ')
                    published = published.replace('Z', '+00:00')
                    votes = []
                    if os.path.isfile(full_post_filename + '.votes'):
                        votes = load_json(full_post_filename + '.votes')
                    content = \
                        get_base_content_from_post(post_json_object,
                                                   system_language)
                    description = first_paragraph_from_string(content)
                    description = remove_html(description)
                    tags_from_post = _get_hashtags_from_post(post_json_object)
                    summary = post_json_object['object']['summary']
                    _add_newswire_dict_entry(base_dir, domain,
                                             newswire, published,
                                             summary,
                                             post_json_object['object']['url'],
                                             votes, full_post_filename,
                                             description, moderated, False,
                                             tags_from_post,
                                             max_tags, session, debug,
                                             None)

            ctr += 1
            if ctr >= max_blogs_per_account:
                break


def _add_blogs_to_newswire(base_dir: str, domain: str, newswire: {},
                           max_blogs_per_account: int,
                           max_tags: int, system_language: str,
                           session, debug: bool) -> None:
    """Adds blogs from each user account into the newswire
    """
    moderation_dict = {}

    # go through each account
    for _, dirs, _ in os.walk(base_dir + '/accounts'):
        for handle in dirs:
            if not is_account_dir(handle):
                continue

            nickname = handle.split('@')[0]

            # has this account been suspended?
            if is_suspended(base_dir, nickname):
                continue

            if os.path.isfile(base_dir + '/accounts/' + handle +
                              '/.nonewswire'):
                continue

            # is there a blogs timeline for this account?
            account_dir = os.path.join(base_dir + '/accounts', handle)
            blogs_index = account_dir + '/tlblogs.index'
            if os.path.isfile(blogs_index):
                domain = handle.split('@')[1]
                _add_account_blogs_to_newswire(base_dir, nickname, domain,
                                               newswire, max_blogs_per_account,
                                               blogs_index, max_tags,
                                               system_language, session,
                                               debug)
        break

    # sort the moderation dict into chronological order, latest first
    sorted_moderation_dict = \
        OrderedDict(sorted(moderation_dict.items(), reverse=True))
    # save the moderation queue details for later display
    newswire_moderation_filename = \
        base_dir + '/accounts/newswiremoderation.txt'
    if sorted_moderation_dict:
        save_json(sorted_moderation_dict, newswire_moderation_filename)
    else:
        # remove the file if there is nothing to moderate
        if os.path.isfile(newswire_moderation_filename):
            try:
                os.remove(newswire_moderation_filename)
            except OSError:
                print('EX: _add_blogs_to_newswire unable to delete ' +
                      str(newswire_moderation_filename))


def get_dict_from_newswire(session, base_dir: str, domain: str,
                           max_posts_per_source: int, max_feed_size_kb: int,
                           max_tags: int, max_feed_item_size_kb: int,
                           max_newswire_posts: int,
                           max_categories_feedItem_size_kb: int,
                           system_language: str, debug: bool) -> {}:
    """Gets rss feeds as a dictionary from newswire file
    """
    subscriptions_filename = base_dir + '/accounts/newswire.txt'
    if not os.path.isfile(subscriptions_filename):
        return {}

    max_posts_per_source = 5

    # add rss feeds
    rss_feed = []
    with open(subscriptions_filename, 'r') as fp_sub:
        rss_feed = fp_sub.readlines()
    result = {}
    for url in rss_feed:
        url = url.strip()

        # Does this contain a url?
        if '://' not in url:
            continue

        # is this a comment?
        if url.startswith('#'):
            continue

        # should this feed be moderated?
        moderated = False
        if '*' in url:
            moderated = True
            url = url.replace('*', '').strip()

        # should this feed content be mirrored?
        mirrored = False
        if '!' in url:
            mirrored = True
            url = url.replace('!', '').strip()

        items_list = get_rss(base_dir, domain, session, url,
                             moderated, mirrored,
                             max_posts_per_source, max_feed_size_kb,
                             max_feed_item_size_kb,
                             max_categories_feedItem_size_kb, debug)
        if items_list:
            for date_str, item in items_list.items():
                result[date_str] = item

    # add blogs from each user account
    _add_blogs_to_newswire(base_dir, domain, result,
                           max_posts_per_source, max_tags, system_language,
                           session, debug)

    # sort into chronological order, latest first
    sorted_result = OrderedDict(sorted(result.items(), reverse=True))

    # are there too many posts? If so then remove the oldest ones
    no_of_posts = len(sorted_result.items())
    if no_of_posts > max_newswire_posts:
        ctr = 0
        removals = []
        for date_str, item in sorted_result.items():
            ctr += 1
            if ctr > max_newswire_posts:
                removals.append(date_str)
        for remov in removals:
            sorted_result.pop(remov)

    return sorted_result
