__filename__ = "daemon_post_receive.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.5.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"

import os
import time
from shares import add_share
from languages import get_understood_languages
from languages import set_default_post_language
from content import get_price_from_string
from content import replace_emoji_from_tags
from content import add_html_tags
from content import extract_text_fields_in_post
from content import extract_media_in_form_post
from content import save_media_in_form_post
from media import replace_twitter
from media import replace_you_tube
from media import process_meta_data
from media import convert_image_to_low_bandwidth
from media import attach_media
from city import get_spoofed_city
from utils import get_instance_url
from utils import is_float
from utils import save_json
from utils import remove_post_from_cache
from utils import load_json
from utils import locate_post
from utils import refresh_newswire
from utils import get_base_content_from_post
from utils import license_link_from_name
from utils import get_config_param
from utils import acct_dir
from utils import is_image_file
from posts import create_reading_post
from posts import create_question_post
from posts import create_report_post
from posts import create_direct_message_post
from posts import create_followers_only_post
from posts import create_unlisted_post
from posts import create_blog_post
from posts import create_public_post
from posts import undo_pinned_post
from posts import pin_post2
from inbox import populate_replies
from inbox import update_edited_post
from daemon_utils import post_to_outbox
from webapp_column_right import html_citations
from httpheaders import set_headers
from httpcodes import write2
from cache import store_person_in_cache
from cache import remove_person_from_cache
from cache import get_person_from_cache
from shares import add_shares_to_actor
from person import get_actor_update_json


def receive_new_post_process(self, post_type: str, path: str, headers: {},
                             length: int, post_bytes, boundary: str,
                             calling_domain: str, cookie: str,
                             content_license_url: str,
                             curr_session, proxy_type: str) -> int:
    # Note: this needs to happen synchronously
    # 0=this is not a new post
    # 1=new post success
    # -1=new post failed
    # 2=new post canceled
    if self.server.debug:
        print('DEBUG: receiving POST')

    if ' boundary=' in headers['Content-Type']:
        if self.server.debug:
            print('DEBUG: receiving POST headers ' +
                  headers['Content-Type'] +
                  ' path ' + path)
        nickname = None
        nickname_str = path.split('/users/')[1]
        if '?' in nickname_str:
            nickname_str = nickname_str.split('?')[0]
        if '/' in nickname_str:
            nickname = nickname_str.split('/')[0]
        else:
            nickname = nickname_str
        if self.server.debug:
            print('DEBUG: POST nickname ' + str(nickname))
        if not nickname:
            print('WARN: no nickname found when receiving ' + post_type +
                  ' path ' + path)
            return -1

        # get the message id of an edited post
        edited_postid = None
        print('DEBUG: edited_postid path ' + path)
        if '?editid=' in path:
            edited_postid = path.split('?editid=')[1]
            if '?' in edited_postid:
                edited_postid = edited_postid.split('?')[0]
            print('DEBUG: edited_postid ' + edited_postid)

        # get the published date of an edited post
        edited_published = None
        if '?editpub=' in path:
            edited_published = path.split('?editpub=')[1]
            if '?' in edited_published:
                edited_published = \
                    edited_published.split('?')[0]
            print('DEBUG: edited_published ' +
                  edited_published)

        length = int(headers['Content-Length'])
        if length > self.server.max_post_length:
            print('POST size too large')
            return -1

        boundary = headers['Content-Type'].split('boundary=')[1]
        if ';' in boundary:
            boundary = boundary.split(';')[0]

        # Note: we don't use cgi here because it's due to be deprecated
        # in Python 3.8/3.10
        # Instead we use the multipart mime parser from the email module
        if self.server.debug:
            print('DEBUG: extracting media from POST')
        media_bytes, post_bytes = \
            extract_media_in_form_post(post_bytes, boundary, 'attachpic')
        if self.server.debug:
            if media_bytes:
                print('DEBUG: media was found. ' +
                      str(len(media_bytes)) + ' bytes')
            else:
                print('DEBUG: no media was found in POST')

        # Note: a .temp extension is used here so that at no time is
        # an image with metadata publicly exposed, even for a few mS
        filename_base = \
            acct_dir(self.server.base_dir,
                     nickname, self.server.domain) + '/upload.temp'

        filename, attachment_media_type = \
            save_media_in_form_post(media_bytes, self.server.debug,
                                    filename_base)
        if self.server.debug:
            if filename:
                print('DEBUG: POST media filename is ' + filename)
            else:
                print('DEBUG: no media filename in POST')

        if filename:
            if is_image_file(filename):
                post_image_filename = filename.replace('.temp', '')
                print('Removing metadata from ' + post_image_filename)
                city = get_spoofed_city(self.server.city,
                                        self.server.base_dir,
                                        nickname, self.server.domain)
                if self.server.low_bandwidth:
                    convert_image_to_low_bandwidth(filename)
                process_meta_data(self.server.base_dir,
                                  nickname, self.server.domain,
                                  filename, post_image_filename, city,
                                  content_license_url)
                if os.path.isfile(post_image_filename):
                    print('POST media saved to ' + post_image_filename)
                else:
                    print('ERROR: POST media could not be saved to ' +
                          post_image_filename)
            else:
                if os.path.isfile(filename):
                    new_filename = filename.replace('.temp', '')
                    os.rename(filename, new_filename)
                    filename = new_filename

        fields = \
            extract_text_fields_in_post(post_bytes, boundary,
                                        self.server.debug, None)
        if self.server.debug:
            if fields:
                print('DEBUG: text field extracted from POST ' +
                      str(fields))
            else:
                print('WARN: no text fields could be extracted from POST')

        # was the citations button pressed on the newblog screen?
        citations_button_press = False
        if post_type == 'newblog' and fields.get('submitCitations'):
            if fields['submitCitations'] == \
               self.server.translate['Citations']:
                citations_button_press = True

        if not citations_button_press:
            # process the received text fields from the POST
            if not fields.get('message') and \
               not fields.get('imageDescription') and \
               not fields.get('pinToProfile'):
                print('WARN: no message, image description or pin')
                return -1
            submit_text1 = self.server.translate['Publish']
            submit_text2 = self.server.translate['Send']
            submit_text3 = submit_text2
            custom_submit_text = \
                get_config_param(self.server.base_dir, 'customSubmitText')
            if custom_submit_text:
                submit_text3 = custom_submit_text
            if fields.get('submitPost'):
                if fields['submitPost'] != submit_text1 and \
                   fields['submitPost'] != submit_text2 and \
                   fields['submitPost'] != submit_text3:
                    print('WARN: no submit field ' + fields['submitPost'])
                    return -1
            else:
                print('WARN: no submitPost')
                return 2

        if not fields.get('imageDescription'):
            fields['imageDescription'] = None
        if not fields.get('videoTranscript'):
            fields['videoTranscript'] = None
        if not fields.get('subject'):
            fields['subject'] = None
        if not fields.get('replyTo'):
            fields['replyTo'] = None

        if not fields.get('schedulePost'):
            fields['schedulePost'] = False
        else:
            fields['schedulePost'] = True
        print('DEBUG: shedulePost ' + str(fields['schedulePost']))

        if not fields.get('eventDate'):
            fields['eventDate'] = None
        if not fields.get('eventTime'):
            fields['eventTime'] = None
        if not fields.get('eventEndTime'):
            fields['eventEndTime'] = None
        if not fields.get('location'):
            fields['location'] = None
        if not fields.get('languagesDropdown'):
            fields['languagesDropdown'] = self.server.system_language
        set_default_post_language(self.server.base_dir, nickname,
                                  self.server.domain,
                                  fields['languagesDropdown'])
        self.server.default_post_language[nickname] = \
            fields['languagesDropdown']

        if not citations_button_press:
            # Store a file which contains the time in seconds
            # since epoch when an attempt to post something was made.
            # This is then used for active monthly users counts
            last_used_filename = \
                acct_dir(self.server.base_dir,
                         nickname, self.server.domain) + '/.lastUsed'
            try:
                with open(last_used_filename, 'w+',
                          encoding='utf-8') as lastfile:
                    lastfile.write(str(int(time.time())))
            except OSError:
                print('EX: _receive_new_post_process unable to write ' +
                      last_used_filename)

        mentions_str = ''
        if fields.get('mentions'):
            mentions_str = fields['mentions'].strip() + ' '
        if not fields.get('commentsEnabled'):
            comments_enabled = False
        else:
            comments_enabled = True

        buy_url = ''
        if fields.get('buyUrl'):
            buy_url = fields['buyUrl']

        chat_url = ''
        if fields.get('chatUrl'):
            chat_url = fields['chatUrl']

        if post_type == 'newpost':
            if not fields.get('pinToProfile'):
                pin_to_profile = False
            else:
                pin_to_profile = True
                # is the post message empty?
                if not fields['message']:
                    # remove the pinned content from profile screen
                    undo_pinned_post(self.server.base_dir,
                                     nickname, self.server.domain)
                    return 1

            city = get_spoofed_city(self.server.city,
                                    self.server.base_dir,
                                    nickname, self.server.domain)

            conversation_id = None
            if fields.get('conversationId'):
                conversation_id = fields['conversationId']

            languages_understood = \
                get_understood_languages(self.server.base_dir,
                                         self.server.http_prefix,
                                         nickname,
                                         self.server.domain_full,
                                         self.server.person_cache)

            media_license_url = self.server.content_license_url
            if fields.get('mediaLicense'):
                media_license_url = fields['mediaLicense']
                if '://' not in media_license_url:
                    media_license_url = \
                        license_link_from_name(media_license_url)
            media_creator = ''
            if fields.get('mediaCreator'):
                media_creator = fields['mediaCreator']
            video_transcript = ''
            if fields.get('videoTranscript'):
                video_transcript = fields['videoTranscript']
            message_json = \
                create_public_post(self.server.base_dir,
                                   nickname,
                                   self.server.domain,
                                   self.server.port,
                                   self.server.http_prefix,
                                   mentions_str + fields['message'],
                                   False, False, comments_enabled,
                                   filename, attachment_media_type,
                                   fields['imageDescription'],
                                   video_transcript,
                                   city,
                                   fields['replyTo'], fields['replyTo'],
                                   fields['subject'],
                                   fields['schedulePost'],
                                   fields['eventDate'],
                                   fields['eventTime'],
                                   fields['eventEndTime'],
                                   fields['location'], False,
                                   fields['languagesDropdown'],
                                   conversation_id,
                                   self.server.low_bandwidth,
                                   self.server.content_license_url,
                                   media_license_url, media_creator,
                                   languages_understood,
                                   self.server.translate, buy_url,
                                   chat_url,
                                   self.server.auto_cw_cache)
            if message_json:
                if edited_postid:
                    recent_posts_cache = self.server.recent_posts_cache
                    allow_local_network_access = \
                        self.server.allow_local_network_access
                    signing_priv_key_pem = \
                        self.server.signing_priv_key_pem
                    twitter_replacement_domain = \
                        self.server.twitter_replacement_domain
                    show_published_date_only = \
                        self.server.show_published_date_only
                    min_images_for_accounts = \
                        self.server.min_images_for_accounts
                    peertube_instances = \
                        self.server.peertube_instances
                    update_edited_post(self.server.base_dir,
                                       nickname, self.server.domain,
                                       message_json,
                                       edited_published,
                                       edited_postid,
                                       recent_posts_cache,
                                       'outbox',
                                       self.server.max_mentions,
                                       self.server.max_emoji,
                                       allow_local_network_access,
                                       self.server.debug,
                                       self.server.system_language,
                                       self.server.http_prefix,
                                       self.server.domain_full,
                                       self.server.person_cache,
                                       signing_priv_key_pem,
                                       self.server.max_recent_posts,
                                       self.server.translate,
                                       curr_session,
                                       self.server.cached_webfingers,
                                       self.server.port,
                                       self.server.allow_deletion,
                                       self.server.yt_replace_domain,
                                       twitter_replacement_domain,
                                       show_published_date_only,
                                       peertube_instances,
                                       self.server.theme_name,
                                       self.server.max_like_count,
                                       self.server.cw_lists,
                                       self.server.dogwhistles,
                                       min_images_for_accounts,
                                       self.server.max_hashtags,
                                       self.server.buy_sites,
                                       self.server.auto_cw_cache)
                    print('DEBUG: sending edited public post ' +
                          str(message_json))
                if fields['schedulePost']:
                    return 1
                if pin_to_profile:
                    sys_language = self.server.system_language
                    content_str = \
                        get_base_content_from_post(message_json,
                                                   sys_language)
                    pin_post2(self.server.base_dir,
                              nickname, self.server.domain, content_str)
                    return 1
                if post_to_outbox(self, message_json,
                                  self.server.project_version,
                                  nickname,
                                  curr_session, proxy_type):
                    populate_replies(self.server.base_dir,
                                     self.server.http_prefix,
                                     self.server.domain_full,
                                     message_json,
                                     self.server.max_replies,
                                     self.server.debug)
                    return 1
                return -1
        elif post_type == 'newblog':
            # citations button on newblog screen
            if citations_button_press:
                message_json = \
                    html_citations(self.server.base_dir,
                                   nickname,
                                   self.server.domain,
                                   self.server.translate,
                                   self.server.newswire,
                                   fields['subject'],
                                   fields['message'],
                                   self.server.theme_name)
                if message_json:
                    message_json = message_json.encode('utf-8')
                    message_json_len = len(message_json)
                    set_headers(self, 'text/html',
                                message_json_len,
                                cookie, calling_domain, False)
                    write2(self, message_json)
                    return 1
                else:
                    return -1
            if not fields['subject']:
                print('WARN: blog posts must have a title')
                return -1
            if not fields['message']:
                print('WARN: blog posts must have content')
                return -1
            # submit button on newblog screen
            save_to_file = False
            client_to_server = False
            city = None
            conversation_id = None
            if fields.get('conversationId'):
                conversation_id = fields['conversationId']
            languages_understood = \
                get_understood_languages(self.server.base_dir,
                                         self.server.http_prefix,
                                         nickname,
                                         self.server.domain_full,
                                         self.server.person_cache)
            media_license_url = self.server.content_license_url
            if fields.get('mediaLicense'):
                media_license_url = fields['mediaLicense']
                if '://' not in media_license_url:
                    media_license_url = \
                        license_link_from_name(media_license_url)
            media_creator = ''
            if fields.get('mediaCreator'):
                media_creator = fields['mediaCreator']
            video_transcript = ''
            if fields.get('videoTranscript'):
                video_transcript = fields['videoTranscript']
            message_json = \
                create_blog_post(self.server.base_dir, nickname,
                                 self.server.domain, self.server.port,
                                 self.server.http_prefix,
                                 fields['message'],
                                 save_to_file,
                                 client_to_server, comments_enabled,
                                 filename, attachment_media_type,
                                 fields['imageDescription'],
                                 video_transcript,
                                 city,
                                 fields['replyTo'], fields['replyTo'],
                                 fields['subject'],
                                 fields['schedulePost'],
                                 fields['eventDate'],
                                 fields['eventTime'],
                                 fields['eventEndTime'],
                                 fields['location'],
                                 fields['languagesDropdown'],
                                 conversation_id,
                                 self.server.low_bandwidth,
                                 self.server.content_license_url,
                                 media_license_url, media_creator,
                                 languages_understood,
                                 self.server.translate, buy_url,
                                 chat_url)
            if message_json:
                if fields['schedulePost']:
                    return 1
                if post_to_outbox(self, message_json,
                                  self.server.project_version,
                                  nickname,
                                  curr_session, proxy_type):
                    refresh_newswire(self.server.base_dir)
                    populate_replies(self.server.base_dir,
                                     self.server.http_prefix,
                                     self.server.domain_full,
                                     message_json,
                                     self.server.max_replies,
                                     self.server.debug)
                    return 1
                return -1
        elif post_type == 'editblogpost':
            print('Edited blog post received')
            post_filename = \
                locate_post(self.server.base_dir,
                            nickname, self.server.domain,
                            fields['postUrl'])
            if os.path.isfile(post_filename):
                post_json_object = load_json(post_filename)
                if post_json_object:
                    cached_filename = \
                        acct_dir(self.server.base_dir,
                                 nickname, self.server.domain) + \
                        '/postcache/' + \
                        fields['postUrl'].replace('/', '#') + '.html'
                    if os.path.isfile(cached_filename):
                        print('Edited blog post, removing cached html')
                        try:
                            os.remove(cached_filename)
                        except OSError:
                            print('EX: _receive_new_post_process ' +
                                  'unable to delete ' + cached_filename)
                    # remove from memory cache
                    remove_post_from_cache(post_json_object,
                                           self.server.recent_posts_cache)
                    # change the blog post title
                    post_json_object['object']['summary'] = \
                        fields['subject']
                    # format message
                    tags = []
                    hashtags_dict = {}
                    mentioned_recipients = []
                    fields['message'] = \
                        add_html_tags(self.server.base_dir,
                                      self.server.http_prefix,
                                      nickname, self.server.domain,
                                      fields['message'],
                                      mentioned_recipients,
                                      hashtags_dict,
                                      self.server.translate,
                                      True)
                    # replace emoji with unicode
                    tags = []
                    for _, tag in hashtags_dict.items():
                        tags.append(tag)
                    # get list of tags
                    fields['message'] = \
                        replace_emoji_from_tags(curr_session,
                                                self.server.base_dir,
                                                fields['message'],
                                                tags, 'content',
                                                self.server.debug,
                                                True)

                    post_json_object['object']['content'] = \
                        fields['message']
                    content_map = post_json_object['object']['contentMap']
                    content_map[self.server.system_language] = \
                        fields['message']

                    img_description = ''
                    if fields.get('imageDescription'):
                        img_description = fields['imageDescription']
                    video_transcript = ''
                    if fields.get('videoTranscript'):
                        video_transcript = fields['videoTranscript']

                    if filename:
                        city = get_spoofed_city(self.server.city,
                                                self.server.base_dir,
                                                nickname,
                                                self.server.domain)
                        license_url = self.server.content_license_url
                        if fields.get('mediaLicense'):
                            license_url = fields['mediaLicense']
                            if '://' not in license_url:
                                license_url = \
                                    license_link_from_name(license_url)
                        creator = ''
                        if fields.get('mediaCreator'):
                            creator = fields['mediaCreator']
                        post_json_object['object'] = \
                            attach_media(self.server.base_dir,
                                         self.server.http_prefix,
                                         nickname,
                                         self.server.domain,
                                         self.server.port,
                                         post_json_object['object'],
                                         filename,
                                         attachment_media_type,
                                         img_description,
                                         video_transcript,
                                         city,
                                         self.server.low_bandwidth,
                                         license_url, creator,
                                         fields['languagesDropdown'])

                    replace_you_tube(post_json_object,
                                     self.server.yt_replace_domain,
                                     self.server.system_language)
                    replace_twitter(post_json_object,
                                    self.server.twitter_replacement_domain,
                                    self.server.system_language)
                    save_json(post_json_object, post_filename)
                    # also save to the news actor
                    if nickname != 'news':
                        post_filename = \
                            post_filename.replace('#users#' +
                                                  nickname + '#',
                                                  '#users#news#')
                        save_json(post_json_object, post_filename)
                    print('Edited blog post, resaved ' + post_filename)
                    return 1
                else:
                    print('Edited blog post, unable to load json for ' +
                          post_filename)
            else:
                print('Edited blog post not found ' +
                      str(fields['postUrl']))
            return -1
        elif post_type == 'newunlisted':
            city = get_spoofed_city(self.server.city,
                                    self.server.base_dir,
                                    nickname,
                                    self.server.domain)
            save_to_file = False
            client_to_server = False

            conversation_id = None
            if fields.get('conversationId'):
                conversation_id = fields['conversationId']

            languages_understood = \
                get_understood_languages(self.server.base_dir,
                                         self.server.http_prefix,
                                         nickname,
                                         self.server.domain_full,
                                         self.server.person_cache)
            media_license_url = self.server.content_license_url
            if fields.get('mediaLicense'):
                media_license_url = fields['mediaLicense']
                if '://' not in media_license_url:
                    media_license_url = \
                        license_link_from_name(media_license_url)
            media_creator = ''
            if fields.get('mediaCreator'):
                media_creator = fields['mediaCreator']
            video_transcript = ''
            if fields.get('videoTranscript'):
                video_transcript = fields['videoTranscript']
            message_json = \
                create_unlisted_post(self.server.base_dir,
                                     nickname,
                                     self.server.domain, self.server.port,
                                     self.server.http_prefix,
                                     mentions_str + fields['message'],
                                     save_to_file,
                                     client_to_server, comments_enabled,
                                     filename, attachment_media_type,
                                     fields['imageDescription'],
                                     video_transcript,
                                     city,
                                     fields['replyTo'],
                                     fields['replyTo'],
                                     fields['subject'],
                                     fields['schedulePost'],
                                     fields['eventDate'],
                                     fields['eventTime'],
                                     fields['eventEndTime'],
                                     fields['location'],
                                     fields['languagesDropdown'],
                                     conversation_id,
                                     self.server.low_bandwidth,
                                     self.server.content_license_url,
                                     media_license_url, media_creator,
                                     languages_understood,
                                     self.server.translate, buy_url,
                                     chat_url,
                                     self.server.auto_cw_cache)
            if message_json:
                if edited_postid:
                    recent_posts_cache = self.server.recent_posts_cache
                    allow_local_network_access = \
                        self.server.allow_local_network_access
                    signing_priv_key_pem = \
                        self.server.signing_priv_key_pem
                    twitter_replacement_domain = \
                        self.server.twitter_replacement_domain
                    show_published_date_only = \
                        self.server.show_published_date_only
                    min_images_for_accounts = \
                        self.server.min_images_for_accounts
                    peertube_instances = \
                        self.server.peertube_instances
                    update_edited_post(self.server.base_dir,
                                       nickname, self.server.domain,
                                       message_json,
                                       edited_published,
                                       edited_postid,
                                       recent_posts_cache,
                                       'outbox',
                                       self.server.max_mentions,
                                       self.server.max_emoji,
                                       allow_local_network_access,
                                       self.server.debug,
                                       self.server.system_language,
                                       self.server.http_prefix,
                                       self.server.domain_full,
                                       self.server.person_cache,
                                       signing_priv_key_pem,
                                       self.server.max_recent_posts,
                                       self.server.translate,
                                       curr_session,
                                       self.server.cached_webfingers,
                                       self.server.port,
                                       self.server.allow_deletion,
                                       self.server.yt_replace_domain,
                                       twitter_replacement_domain,
                                       show_published_date_only,
                                       peertube_instances,
                                       self.server.theme_name,
                                       self.server.max_like_count,
                                       self.server.cw_lists,
                                       self.server.dogwhistles,
                                       min_images_for_accounts,
                                       self.server.max_hashtags,
                                       self.server.buy_sites,
                                       self.server.auto_cw_cache)
                    print('DEBUG: sending edited unlisted post ' +
                          str(message_json))

                if fields['schedulePost']:
                    return 1
                if post_to_outbox(self, message_json,
                                  self.server.project_version,
                                  nickname,
                                  curr_session, proxy_type):
                    populate_replies(self.server.base_dir,
                                     self.server.http_prefix,
                                     self.server.domain,
                                     message_json,
                                     self.server.max_replies,
                                     self.server.debug)
                    return 1
                return -1
        elif post_type == 'newfollowers':
            city = get_spoofed_city(self.server.city,
                                    self.server.base_dir,
                                    nickname,
                                    self.server.domain)
            save_to_file = False
            client_to_server = False

            conversation_id = None
            if fields.get('conversationId'):
                conversation_id = fields['conversationId']

            mentions_message = mentions_str + fields['message']
            languages_understood = \
                get_understood_languages(self.server.base_dir,
                                         self.server.http_prefix,
                                         nickname,
                                         self.server.domain_full,
                                         self.server.person_cache)
            media_license_url = self.server.content_license_url
            if fields.get('mediaLicense'):
                media_license_url = fields['mediaLicense']
                if '://' not in media_license_url:
                    media_license_url = \
                        license_link_from_name(media_license_url)
            media_creator = ''
            if fields.get('mediaCreator'):
                media_creator = fields['mediaCreator']
            video_transcript = ''
            if fields.get('videoTranscript'):
                video_transcript = fields['videoTranscript']
            message_json = \
                create_followers_only_post(self.server.base_dir,
                                           nickname,
                                           self.server.domain,
                                           self.server.port,
                                           self.server.http_prefix,
                                           mentions_message,
                                           save_to_file,
                                           client_to_server,
                                           comments_enabled,
                                           filename, attachment_media_type,
                                           fields['imageDescription'],
                                           video_transcript,
                                           city,
                                           fields['replyTo'],
                                           fields['replyTo'],
                                           fields['subject'],
                                           fields['schedulePost'],
                                           fields['eventDate'],
                                           fields['eventTime'],
                                           fields['eventEndTime'],
                                           fields['location'],
                                           fields['languagesDropdown'],
                                           conversation_id,
                                           self.server.low_bandwidth,
                                           self.server.content_license_url,
                                           media_license_url,
                                           media_creator,
                                           languages_understood,
                                           self.server.translate,
                                           buy_url, chat_url,
                                           self.server.auto_cw_cache)
            if message_json:
                if edited_postid:
                    recent_posts_cache = self.server.recent_posts_cache
                    allow_local_network_access = \
                        self.server.allow_local_network_access
                    signing_priv_key_pem = \
                        self.server.signing_priv_key_pem
                    twitter_replacement_domain = \
                        self.server.twitter_replacement_domain
                    show_published_date_only = \
                        self.server.show_published_date_only
                    min_images_for_accounts = \
                        self.server.min_images_for_accounts
                    peertube_instances = \
                        self.server.peertube_instances
                    update_edited_post(self.server.base_dir,
                                       nickname, self.server.domain,
                                       message_json,
                                       edited_published,
                                       edited_postid,
                                       recent_posts_cache,
                                       'outbox',
                                       self.server.max_mentions,
                                       self.server.max_emoji,
                                       allow_local_network_access,
                                       self.server.debug,
                                       self.server.system_language,
                                       self.server.http_prefix,
                                       self.server.domain_full,
                                       self.server.person_cache,
                                       signing_priv_key_pem,
                                       self.server.max_recent_posts,
                                       self.server.translate,
                                       curr_session,
                                       self.server.cached_webfingers,
                                       self.server.port,
                                       self.server.allow_deletion,
                                       self.server.yt_replace_domain,
                                       twitter_replacement_domain,
                                       show_published_date_only,
                                       peertube_instances,
                                       self.server.theme_name,
                                       self.server.max_like_count,
                                       self.server.cw_lists,
                                       self.server.dogwhistles,
                                       min_images_for_accounts,
                                       self.server.max_hashtags,
                                       self.server.buy_sites,
                                       self.server.auto_cw_cache)
                    print('DEBUG: sending edited followers post ' +
                          str(message_json))

                if fields['schedulePost']:
                    return 1
                if post_to_outbox(self, message_json,
                                  self.server.project_version,
                                  nickname,
                                  curr_session, proxy_type):
                    populate_replies(self.server.base_dir,
                                     self.server.http_prefix,
                                     self.server.domain,
                                     message_json,
                                     self.server.max_replies,
                                     self.server.debug)
                    return 1
                return -1
        elif post_type == 'newdm':
            message_json = None
            print('A DM was posted')
            if '@' in mentions_str:
                city = get_spoofed_city(self.server.city,
                                        self.server.base_dir,
                                        nickname,
                                        self.server.domain)
                save_to_file = False
                client_to_server = False

                conversation_id = None
                if fields.get('conversationId'):
                    conversation_id = fields['conversationId']
                content_license_url = self.server.content_license_url

                languages_understood = \
                    get_understood_languages(self.server.base_dir,
                                             self.server.http_prefix,
                                             nickname,
                                             self.server.domain_full,
                                             self.server.person_cache)

                reply_is_chat = False
                if fields.get('replychatmsg'):
                    reply_is_chat = fields['replychatmsg']

                dm_license_url = self.server.dm_license_url
                media_license_url = content_license_url
                if fields.get('mediaLicense'):
                    media_license_url = fields['mediaLicense']
                    if '://' not in media_license_url:
                        media_license_url = \
                            license_link_from_name(media_license_url)
                media_creator = ''
                if fields.get('mediaCreator'):
                    media_creator = fields['mediaCreator']
                video_transcript = ''
                if fields.get('videoTranscript'):
                    video_transcript = fields['videoTranscript']
                message_json = \
                    create_direct_message_post(self.server.base_dir,
                                               nickname,
                                               self.server.domain,
                                               self.server.port,
                                               self.server.http_prefix,
                                               mentions_str +
                                               fields['message'],
                                               save_to_file,
                                               client_to_server,
                                               comments_enabled,
                                               filename,
                                               attachment_media_type,
                                               fields['imageDescription'],
                                               video_transcript,
                                               city,
                                               fields['replyTo'],
                                               fields['replyTo'],
                                               fields['subject'],
                                               True,
                                               fields['schedulePost'],
                                               fields['eventDate'],
                                               fields['eventTime'],
                                               fields['eventEndTime'],
                                               fields['location'],
                                               fields['languagesDropdown'],
                                               conversation_id,
                                               self.server.low_bandwidth,
                                               dm_license_url,
                                               media_license_url,
                                               media_creator,
                                               languages_understood,
                                               reply_is_chat,
                                               self.server.translate,
                                               buy_url, chat_url,
                                               self.server.auto_cw_cache)
            if message_json:
                print('DEBUG: posting DM edited_postid ' +
                      str(edited_postid))
                if edited_postid:
                    recent_posts_cache = self.server.recent_posts_cache
                    allow_local_network_access = \
                        self.server.allow_local_network_access
                    signing_priv_key_pem = \
                        self.server.signing_priv_key_pem
                    twitter_replacement_domain = \
                        self.server.twitter_replacement_domain
                    show_published_date_only = \
                        self.server.show_published_date_only
                    min_images_for_accounts = \
                        self.server.min_images_for_accounts
                    peertube_instances = \
                        self.server.peertube_instances
                    update_edited_post(self.server.base_dir,
                                       nickname, self.server.domain,
                                       message_json,
                                       edited_published,
                                       edited_postid,
                                       recent_posts_cache,
                                       'outbox',
                                       self.server.max_mentions,
                                       self.server.max_emoji,
                                       allow_local_network_access,
                                       self.server.debug,
                                       self.server.system_language,
                                       self.server.http_prefix,
                                       self.server.domain_full,
                                       self.server.person_cache,
                                       signing_priv_key_pem,
                                       self.server.max_recent_posts,
                                       self.server.translate,
                                       curr_session,
                                       self.server.cached_webfingers,
                                       self.server.port,
                                       self.server.allow_deletion,
                                       self.server.yt_replace_domain,
                                       twitter_replacement_domain,
                                       show_published_date_only,
                                       peertube_instances,
                                       self.server.theme_name,
                                       self.server.max_like_count,
                                       self.server.cw_lists,
                                       self.server.dogwhistles,
                                       min_images_for_accounts,
                                       self.server.max_hashtags,
                                       self.server.buy_sites,
                                       self.server.auto_cw_cache)
                    print('DEBUG: sending edited dm post ' +
                          str(message_json))

                if fields['schedulePost']:
                    return 1
                print('Sending new DM to ' +
                      str(message_json['object']['to']))
                if post_to_outbox(self, message_json,
                                  self.server.project_version,
                                  nickname,
                                  curr_session, proxy_type):
                    populate_replies(self.server.base_dir,
                                     self.server.http_prefix,
                                     self.server.domain,
                                     message_json,
                                     self.server.max_replies,
                                     self.server.debug)
                    return 1
                return -1
        elif post_type == 'newreminder':
            message_json = None
            handle = nickname + '@' + self.server.domain_full
            print('A reminder was posted for ' + handle)
            if '@' + handle not in mentions_str:
                mentions_str = '@' + handle + ' ' + mentions_str
            city = get_spoofed_city(self.server.city,
                                    self.server.base_dir,
                                    nickname,
                                    self.server.domain)
            save_to_file = False
            client_to_server = False
            comments_enabled = False
            conversation_id = None
            mentions_message = mentions_str + fields['message']
            languages_understood = \
                get_understood_languages(self.server.base_dir,
                                         self.server.http_prefix,
                                         nickname,
                                         self.server.domain_full,
                                         self.server.person_cache)
            media_license_url = self.server.content_license_url
            if fields.get('mediaLicense'):
                media_license_url = fields['mediaLicense']
                if '://' not in media_license_url:
                    media_license_url = \
                        license_link_from_name(media_license_url)
            media_creator = ''
            if fields.get('mediaCreator'):
                media_creator = fields['mediaCreator']
            video_transcript = ''
            if fields.get('videoTranscript'):
                video_transcript = fields['videoTranscript']
            message_json = \
                create_direct_message_post(self.server.base_dir,
                                           nickname,
                                           self.server.domain,
                                           self.server.port,
                                           self.server.http_prefix,
                                           mentions_message,
                                           save_to_file,
                                           client_to_server,
                                           comments_enabled,
                                           filename, attachment_media_type,
                                           fields['imageDescription'],
                                           video_transcript,
                                           city,
                                           None, None,
                                           fields['subject'],
                                           True, fields['schedulePost'],
                                           fields['eventDate'],
                                           fields['eventTime'],
                                           fields['eventEndTime'],
                                           fields['location'],
                                           fields['languagesDropdown'],
                                           conversation_id,
                                           self.server.low_bandwidth,
                                           self.server.dm_license_url,
                                           media_license_url,
                                           media_creator,
                                           languages_understood,
                                           False, self.server.translate,
                                           buy_url, chat_url,
                                           self.server.auto_cw_cache)
            if message_json:
                if fields['schedulePost']:
                    return 1
                print('DEBUG: new reminder to ' +
                      str(message_json['object']['to']) + ' ' +
                      str(edited_postid))
                if edited_postid:
                    recent_posts_cache = self.server.recent_posts_cache
                    allow_local_network_access = \
                        self.server.allow_local_network_access
                    signing_priv_key_pem = \
                        self.server.signing_priv_key_pem
                    twitter_replacement_domain = \
                        self.server.twitter_replacement_domain
                    show_published_date_only = \
                        self.server.show_published_date_only
                    min_images_for_accounts = \
                        self.server.min_images_for_accounts
                    peertube_instances = \
                        self.server.peertube_instances
                    update_edited_post(self.server.base_dir,
                                       nickname, self.server.domain,
                                       message_json,
                                       edited_published,
                                       edited_postid,
                                       recent_posts_cache,
                                       'dm',
                                       self.server.max_mentions,
                                       self.server.max_emoji,
                                       allow_local_network_access,
                                       self.server.debug,
                                       self.server.system_language,
                                       self.server.http_prefix,
                                       self.server.domain_full,
                                       self.server.person_cache,
                                       signing_priv_key_pem,
                                       self.server.max_recent_posts,
                                       self.server.translate,
                                       curr_session,
                                       self.server.cached_webfingers,
                                       self.server.port,
                                       self.server.allow_deletion,
                                       self.server.yt_replace_domain,
                                       twitter_replacement_domain,
                                       show_published_date_only,
                                       peertube_instances,
                                       self.server.theme_name,
                                       self.server.max_like_count,
                                       self.server.cw_lists,
                                       self.server.dogwhistles,
                                       min_images_for_accounts,
                                       self.server.max_hashtags,
                                       self.server.buy_sites,
                                       self.server.auto_cw_cache)
                    print('DEBUG: sending edited reminder post ' +
                          str(message_json))
                if post_to_outbox(self, message_json,
                                  self.server.project_version,
                                  nickname,
                                  curr_session, proxy_type):
                    return 1
                return -1
        elif post_type == 'newreport':
            if attachment_media_type:
                if attachment_media_type != 'image':
                    return -1
            # So as to be sure that this only goes to moderators
            # and not accounts being reported we disable any
            # included fediverse addresses by replacing '@' with '-at-'
            fields['message'] = fields['message'].replace('@', '-at-')
            city = get_spoofed_city(self.server.city,
                                    self.server.base_dir,
                                    nickname,
                                    self.server.domain)
            languages_understood = \
                get_understood_languages(self.server.base_dir,
                                         self.server.http_prefix,
                                         nickname,
                                         self.server.domain_full,
                                         self.server.person_cache)
            media_license_url = self.server.content_license_url
            if fields.get('mediaLicense'):
                media_license_url = fields['mediaLicense']
                if '://' not in media_license_url:
                    media_license_url = \
                        license_link_from_name(media_license_url)
            media_creator = ''
            if fields.get('mediaCreator'):
                media_creator = fields['mediaCreator']
            video_transcript = ''
            if fields.get('videoTranscript'):
                video_transcript = fields['videoTranscript']
            message_json = \
                create_report_post(self.server.base_dir,
                                   nickname,
                                   self.server.domain, self.server.port,
                                   self.server.http_prefix,
                                   mentions_str + fields['message'],
                                   False, False, True,
                                   filename, attachment_media_type,
                                   fields['imageDescription'],
                                   video_transcript,
                                   city,
                                   self.server.debug, fields['subject'],
                                   fields['languagesDropdown'],
                                   self.server.low_bandwidth,
                                   self.server.content_license_url,
                                   media_license_url, media_creator,
                                   languages_understood,
                                   self.server.translate,
                                   self.server.auto_cw_cache)
            if message_json:
                if post_to_outbox(self, message_json,
                                  self.server.project_version,
                                  nickname,
                                  curr_session, proxy_type):
                    return 1
                return -1
        elif post_type == 'newquestion':
            if not fields.get('duration'):
                return -1
            if not fields.get('message'):
                return -1
            q_options = []
            for question_ctr in range(8):
                if fields.get('questionOption' + str(question_ctr)):
                    q_options.append(fields['questionOption' +
                                            str(question_ctr)])
            if not q_options:
                return -1
            city = get_spoofed_city(self.server.city,
                                    self.server.base_dir,
                                    nickname,
                                    self.server.domain)
            if isinstance(fields['duration'], str):
                if len(fields['duration']) > 5:
                    return -1
            int_duration_days = int(fields['duration'])
            languages_understood = \
                get_understood_languages(self.server.base_dir,
                                         self.server.http_prefix,
                                         nickname,
                                         self.server.domain_full,
                                         self.server.person_cache)
            media_license_url = self.server.content_license_url
            if fields.get('mediaLicense'):
                media_license_url = fields['mediaLicense']
                if '://' not in media_license_url:
                    media_license_url = \
                        license_link_from_name(media_license_url)
            media_creator = ''
            if fields.get('mediaCreator'):
                media_creator = fields['mediaCreator']
            video_transcript = ''
            if fields.get('videoTranscript'):
                video_transcript = fields['videoTranscript']
            message_json = \
                create_question_post(self.server.base_dir,
                                     nickname,
                                     self.server.domain,
                                     self.server.port,
                                     self.server.http_prefix,
                                     fields['message'], q_options,
                                     False, False,
                                     comments_enabled,
                                     filename, attachment_media_type,
                                     fields['imageDescription'],
                                     video_transcript,
                                     city,
                                     fields['subject'],
                                     int_duration_days,
                                     fields['languagesDropdown'],
                                     self.server.low_bandwidth,
                                     self.server.content_license_url,
                                     media_license_url, media_creator,
                                     languages_understood,
                                     self.server.translate,
                                     self.server.auto_cw_cache)
            if message_json:
                if self.server.debug:
                    print('DEBUG: new Question')
                if post_to_outbox(self, message_json,
                                  self.server.project_version,
                                  nickname,
                                  curr_session, proxy_type):
                    return 1
            return -1
        elif post_type in ('newreadingstatus'):
            if not fields.get('readingupdatetype'):
                print(post_type + ' no readingupdatetype')
                return -1
            if fields['readingupdatetype'] not in ('readingupdatewant',
                                                   'readingupdateread',
                                                   'readingupdatefinished',
                                                   'readingupdaterating'):
                print(post_type + ' not recognised ' +
                      fields['readingupdatetype'])
                return -1
            if not fields.get('booktitle'):
                print(post_type + ' no booktitle')
                return -1
            if not fields.get('bookurl'):
                print(post_type + ' no bookurl')
                return -1
            book_rating = 0.0
            if fields.get('bookrating'):
                if isinstance(fields['bookrating'], float) or \
                   isinstance(fields['bookrating'], int):
                    book_rating = fields['bookrating']
            media_license_url = self.server.content_license_url
            if fields.get('mediaLicense'):
                media_license_url = fields['mediaLicense']
                if '://' not in media_license_url:
                    media_license_url = \
                        license_link_from_name(media_license_url)
            media_creator = ''
            if fields.get('mediaCreator'):
                media_creator = fields['mediaCreator']
            video_transcript = ''
            if fields.get('videoTranscript'):
                video_transcript = fields['videoTranscript']
            conversation_id = None
            languages_understood = \
                get_understood_languages(self.server.base_dir,
                                         self.server.http_prefix,
                                         nickname,
                                         self.server.domain_full,
                                         self.server.person_cache)
            city = get_spoofed_city(self.server.city,
                                    self.server.base_dir,
                                    nickname, self.server.domain)
            msg_str = fields['readingupdatetype']
            # reading status
            message_json = \
                create_reading_post(self.server.base_dir,
                                    nickname,
                                    self.server.domain,
                                    self.server.port,
                                    self.server.http_prefix,
                                    mentions_str, msg_str,
                                    fields['booktitle'],
                                    fields['bookurl'],
                                    book_rating,
                                    False, False, comments_enabled,
                                    filename, attachment_media_type,
                                    fields['imageDescription'],
                                    video_transcript,
                                    city, None, None,
                                    fields['subject'],
                                    fields['schedulePost'],
                                    fields['eventDate'],
                                    fields['eventTime'],
                                    fields['eventEndTime'],
                                    fields['location'], False,
                                    fields['languagesDropdown'],
                                    conversation_id,
                                    self.server.low_bandwidth,
                                    self.server.content_license_url,
                                    media_license_url, media_creator,
                                    languages_understood,
                                    self.server.translate, buy_url,
                                    chat_url,
                                    self.server.auto_cw_cache)
            if message_json:
                if edited_postid:
                    recent_posts_cache = self.server.recent_posts_cache
                    allow_local_network_access = \
                        self.server.allow_local_network_access
                    signing_priv_key_pem = \
                        self.server.signing_priv_key_pem
                    twitter_replacement_domain = \
                        self.server.twitter_replacement_domain
                    show_published_date_only = \
                        self.server.show_published_date_only
                    min_images_for_accounts = \
                        self.server.min_images_for_accounts
                    peertube_instances = \
                        self.server.peertube_instances
                    update_edited_post(self.server.base_dir,
                                       nickname, self.server.domain,
                                       message_json,
                                       edited_published,
                                       edited_postid,
                                       recent_posts_cache,
                                       'outbox',
                                       self.server.max_mentions,
                                       self.server.max_emoji,
                                       allow_local_network_access,
                                       self.server.debug,
                                       self.server.system_language,
                                       self.server.http_prefix,
                                       self.server.domain_full,
                                       self.server.person_cache,
                                       signing_priv_key_pem,
                                       self.server.max_recent_posts,
                                       self.server.translate,
                                       curr_session,
                                       self.server.cached_webfingers,
                                       self.server.port,
                                       self.server.allow_deletion,
                                       self.server.yt_replace_domain,
                                       twitter_replacement_domain,
                                       show_published_date_only,
                                       peertube_instances,
                                       self.server.theme_name,
                                       self.server.max_like_count,
                                       self.server.cw_lists,
                                       self.server.dogwhistles,
                                       min_images_for_accounts,
                                       self.server.max_hashtags,
                                       self.server.buy_sites,
                                       self.server.auto_cw_cache)
                    print('DEBUG: sending edited reading status post ' +
                          str(message_json))
                if fields['schedulePost']:
                    return 1
                if not fields.get('pinToProfile'):
                    pin_to_profile = False
                else:
                    pin_to_profile = True
                if pin_to_profile:
                    sys_language = self.server.system_language
                    content_str = \
                        get_base_content_from_post(message_json,
                                                   sys_language)
                    pin_post2(self.server.base_dir,
                              nickname, self.server.domain, content_str)
                    return 1
                if post_to_outbox(self, message_json,
                                  self.server.project_version,
                                  nickname,
                                  curr_session, proxy_type):
                    populate_replies(self.server.base_dir,
                                     self.server.http_prefix,
                                     self.server.domain_full,
                                     message_json,
                                     self.server.max_replies,
                                     self.server.debug)
                    return 1
                return -1
        elif post_type in ('newshare', 'newwanted'):
            if not fields.get('itemQty'):
                print(post_type + ' no itemQty')
                return -1
            if not fields.get('itemType'):
                print(post_type + ' no itemType')
                return -1
            if 'itemPrice' not in fields:
                print(post_type + ' no itemPrice')
                return -1
            if 'itemCurrency' not in fields:
                print(post_type + ' no itemCurrency')
                return -1
            if not fields.get('category'):
                print(post_type + ' no category')
                return -1
            if not fields.get('duration'):
                print(post_type + ' no duratio')
                return -1
            if attachment_media_type:
                if attachment_media_type != 'image':
                    print('Attached media is not an image')
                    return -1
            duration_str = fields['duration']
            if duration_str:
                if ' ' not in duration_str:
                    duration_str = duration_str + ' days'
            city = get_spoofed_city(self.server.city,
                                    self.server.base_dir,
                                    nickname,
                                    self.server.domain)
            item_qty = 1
            if fields['itemQty']:
                if is_float(fields['itemQty']):
                    item_qty = float(fields['itemQty'])
            item_price = "0.00"
            item_currency = "EUR"
            if fields['itemPrice']:
                item_price, item_currency = \
                    get_price_from_string(fields['itemPrice'])
            if fields['itemCurrency']:
                item_currency = fields['itemCurrency']
            if post_type == 'newshare':
                print('Adding shared item')
                shares_file_type = 'shares'
            else:
                print('Adding wanted item')
                shares_file_type = 'wanted'
            share_on_profile = False
            if fields.get('shareOnProfile'):
                if fields['shareOnProfile'] == 'on':
                    share_on_profile = True
            add_share(self.server.base_dir,
                      self.server.http_prefix,
                      nickname,
                      self.server.domain, self.server.port,
                      fields['subject'],
                      fields['message'],
                      filename,
                      item_qty, fields['itemType'],
                      fields['category'],
                      fields['location'],
                      duration_str,
                      self.server.debug,
                      city, item_price, item_currency,
                      fields['languagesDropdown'],
                      self.server.translate, shares_file_type,
                      self.server.low_bandwidth,
                      self.server.content_license_url,
                      share_on_profile,
                      self.server.block_federated)
            if post_type == 'newshare':
                # add shareOnProfile items to the actor attachments
                # https://codeberg.org/fediverse/fep/src/branch/main/fep/0837/fep-0837.md
                actor = \
                    get_instance_url(calling_domain,
                                     self.server.http_prefix,
                                     self.server.domain_full,
                                     self.server.onion_domain,
                                     self.server.i2p_domain) + \
                    '/users/' + nickname
                person_cache = self.server.person_cache
                actor_json = get_person_from_cache(self.server.base_dir,
                                                   actor, person_cache)
                if not actor_json:
                    actor_filename = \
                        acct_dir(self.server.base_dir, nickname,
                                 self.server.domain) + '.json'
                    if os.path.isfile(actor_filename):
                        actor_json = load_json(actor_filename, 1, 1)
                if actor_json:
                    max_shares_on_profile = \
                        self.server.max_shares_on_profile
                    if add_shares_to_actor(self.server.base_dir,
                                           nickname, self.server.domain,
                                           actor_json,
                                           max_shares_on_profile):
                        remove_person_from_cache(self.server.base_dir,
                                                 actor, person_cache)
                        store_person_in_cache(self.server.base_dir, actor,
                                              actor_json, person_cache,
                                              True)
                        actor_filename = \
                            acct_dir(self.server.base_dir,
                                     nickname,
                                     self.server.domain) + '.json'
                        save_json(actor_json, actor_filename)
                        # send profile update to followers
                        update_actor_json = \
                            get_actor_update_json(actor_json)
                        print('Sending actor update ' +
                              'after change to attached shares: ' +
                              str(update_actor_json))
                        post_to_outbox(self, update_actor_json,
                                       self.server.project_version,
                                       nickname,
                                       curr_session, proxy_type)

            if filename:
                if os.path.isfile(filename):
                    try:
                        os.remove(filename)
                    except OSError:
                        print('EX: _receive_new_post_process ' +
                              'unable to delete ' + filename)
            self.post_to_nickname = nickname
            return 1
    return -1
