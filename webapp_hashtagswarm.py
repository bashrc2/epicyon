__filename__ = "webapp_hashtagswarm.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.3.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Web Interface"

import os
from datetime import datetime
from utils import get_nickname_from_actor
from utils import get_config_param
from categories import get_hashtag_categories
from categories import get_hashtag_category
from webapp_utils import set_custom_background
from webapp_utils import get_search_banner_file
from webapp_utils import get_content_warning_button
from webapp_utils import html_header_with_external_style
from webapp_utils import html_footer


def get_hashtag_categories_feed(base_dir: str,
                                hashtag_categories: {} = None) -> str:
    """Returns an rss feed for hashtag categories
    """
    if not hashtag_categories:
        hashtag_categories = get_hashtag_categories(base_dir)
    if not hashtag_categories:
        return None

    rss_str = \
        "<?xml version=\"1.0\" encoding=\"UTF-8\" ?>\n" + \
        "<rss version=\"2.0\">\n" + \
        '<channel>\n' + \
        '    <title>#categories</title>\n'

    rss_date_str = \
        datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S UT")

    for category_str, hashtag_list in hashtag_categories.items():
        rss_str += \
            '<item>\n' + \
            '  <title>' + category_str + '</title>\n'
        list_str = ''
        for hashtag in hashtag_list:
            if ':' in hashtag:
                continue
            if '&' in hashtag:
                continue
            list_str += hashtag + ' '
        rss_str += \
            '  <description>' + list_str.strip() + '</description>\n' + \
            '  <link/>\n' + \
            '  <pubDate>' + rss_date_str + '</pubDate>\n' + \
            '</item>\n'

    rss_str += \
        '</channel>\n' + \
        '</rss>\n'
    return rss_str


def html_hash_tag_swarm(base_dir: str, actor: str, translate: {}) -> str:
    """Returns a tag swarm of today's hashtags
    """
    max_tag_length = 42
    curr_time = datetime.utcnow()
    days_since_epoch = (curr_time - datetime(1970, 1, 1)).days
    days_since_epoch_str = str(days_since_epoch) + ' '
    days_since_epoch_str2 = str(days_since_epoch - 1) + ' '
    recently = days_since_epoch - 1
    tag_swarm = []
    category_swarm = []
    domain_histogram = {}

    # Load the blocked hashtags into memory.
    # This avoids needing to repeatedly load the blocked file for each hashtag
    blocked_str = ''
    global_blocking_filename = base_dir + '/accounts/blocking.txt'
    if os.path.isfile(global_blocking_filename):
        with open(global_blocking_filename, 'r',
                  encoding='utf-8') as fp_block:
            blocked_str = fp_block.read()

    for _, _, files in os.walk(base_dir + '/tags'):
        for fname in files:
            if not fname.endswith('.txt'):
                continue
            tags_filename = os.path.join(base_dir + '/tags', fname)
            if not os.path.isfile(tags_filename):
                continue

            # get last modified datetime
            mod_time_since_epoc = os.path.getmtime(tags_filename)
            last_modified_date = datetime.fromtimestamp(mod_time_since_epoc)
            file_days_since_epoch = \
                (last_modified_date - datetime(1970, 1, 1)).days

            # check if the file was last modified within the previous
            # two days
            if file_days_since_epoch < recently:
                continue

            hash_tag_name = fname.split('.')[0]
            if len(hash_tag_name) > max_tag_length:
                # NoIncrediblyLongAndBoringHashtagsShownHere
                continue
            if '#' in hash_tag_name or \
               '&' in hash_tag_name or \
               '"' in hash_tag_name or \
               "'" in hash_tag_name:
                continue
            if '#' + hash_tag_name + '\n' in blocked_str:
                continue
            with open(tags_filename, 'r', encoding='utf-8') as fp_tags:
                # only read one line, which saves time and memory
                last_tag = fp_tags.readline()
                if not last_tag.startswith(days_since_epoch_str):
                    if not last_tag.startswith(days_since_epoch_str2):
                        continue
            with open(tags_filename, 'r', encoding='utf-8') as fp_tags:
                while True:
                    line = fp_tags.readline()
                    if not line:
                        break
                    if '  ' not in line:
                        break
                    sections = line.split('  ')
                    if len(sections) != 3:
                        break
                    post_days_since_epoch_str = sections[0]
                    if not post_days_since_epoch_str.isdigit():
                        break
                    post_days_since_epoch = int(post_days_since_epoch_str)
                    if post_days_since_epoch < recently:
                        break
                    post_url = sections[2]
                    if '##' not in post_url:
                        break
                    post_domain = post_url.split('##')[1]
                    if '#' in post_domain:
                        post_domain = post_domain.split('#')[0]

                    if domain_histogram.get(post_domain):
                        domain_histogram[post_domain] = \
                            domain_histogram[post_domain] + 1
                    else:
                        domain_histogram[post_domain] = 1
                    tag_swarm.append(hash_tag_name)
                    category_filename = \
                        tags_filename.replace('.txt', '.category')
                    if os.path.isfile(category_filename):
                        category_str = \
                            get_hashtag_category(base_dir, hash_tag_name)
                        if len(category_str) < max_tag_length:
                            if '#' not in category_str and \
                               '&' not in category_str and \
                               '"' not in category_str and \
                               "'" not in category_str:
                                if category_str not in category_swarm:
                                    category_swarm.append(category_str)
                    break
        break

    if not tag_swarm:
        return ''
    tag_swarm.sort()

    # swarm of categories
    category_swarm_str = ''
    if category_swarm:
        if len(category_swarm) > 3:
            category_swarm.sort()
            for category_str in category_swarm:
                category_swarm_str += \
                    '<a href="' + actor + '/category/' + category_str + \
                    '" class="hashtagswarm"><b>' + category_str + '</b></a>\n'
            category_swarm_str += '<br>\n'

    # swarm of tags
    tag_swarm_str = ''
    for tag_name in tag_swarm:
        tag_display_name = tag_name
        tag_map_filename = \
            os.path.join(base_dir + '/tagmaps', tag_name + '.txt')
        if os.path.isfile(tag_map_filename):
            tag_display_name = '📌' + tag_name
        tag_swarm_str += \
            '<a href="' + actor + '/tags/' + tag_name + \
            '" class="hashtagswarm">' + tag_display_name + '</a>\n'

    if category_swarm_str:
        tag_swarm_str = \
            get_content_warning_button('alltags', translate, tag_swarm_str)

    tag_swarm_html = category_swarm_str + tag_swarm_str.strip() + '\n'
    return tag_swarm_html


def html_search_hashtag_category(translate: {},
                                 base_dir: str, path: str, domain: str,
                                 theme: str) -> str:
    """Show hashtags after selecting a category on the main search screen
    """
    actor = path.split('/category/')[0]
    category_str = path.split('/category/')[1].strip()
    search_nickname = get_nickname_from_actor(actor)
    if not search_nickname:
        return ''

    set_custom_background(base_dir, 'search-background', 'follow-background')

    css_filename = base_dir + '/epicyon-search.css'
    if os.path.isfile(base_dir + '/search.css'):
        css_filename = base_dir + '/search.css'

    instance_title = \
        get_config_param(base_dir, 'instanceTitle')
    html_str = \
        html_header_with_external_style(css_filename, instance_title, None)

    # show a banner above the search box
    search_banner_file, search_banner_filename = \
        get_search_banner_file(base_dir, search_nickname, domain, theme)

    if os.path.isfile(search_banner_filename):
        html_str += '<a href="' + actor + '/search">\n'
        html_str += '<img loading="lazy" decoding="async" ' + \
            'class="timeline-banner" src="' + \
            actor + '/' + search_banner_file + '" alt="" /></a>\n'

    html_str += \
        '<div class="follow">' + \
        '<center><br><br><br>' + \
        '<h1><a href="' + actor + '/search"><b>' + \
        translate['Category'] + ': ' + category_str + '</b></a></h1>'

    hashtags_dict = get_hashtag_categories(base_dir, True, category_str)
    if hashtags_dict:
        for _, hashtag_list in hashtags_dict.items():
            hashtag_list.sort()
            for tag_name in hashtag_list:
                html_str += \
                    '<a href="' + actor + '/tags/' + tag_name + \
                    '" class="hashtagswarm">' + tag_name + '</a>\n'

    html_str += \
        '</center>' + \
        '</div>'
    html_str += html_footer()
    return html_str
