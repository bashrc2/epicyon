__filename__ = "daemon_get_profile.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.5.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"

import os
import json
from roles import get_actor_roles_list
from skills import no_of_actor_skills
from skills import get_skills_from_list
from utils import get_nickname_from_actor
from utils import load_json
from utils import get_json_content_from_accept
from utils import get_occupation_skills
from utils import get_instance_url
from utils import acct_dir
from utils import convert_domains
from httpcodes import write2
from httpcodes import http_404
from person import person_lookup
from person import add_alternate_domains
from httprequests import request_http
from httpheaders import redirect_headers
from httpheaders import set_headers
from session import establish_session
from city import get_spoofed_city
from webapp_profile import html_profile
from webapp_profile import html_edit_profile
from fitnessFunctions import fitness_performance
from securemode import secure_mode


def show_person_profile(self, authorized: bool,
                        calling_domain: str,
                        referer_domain: str, path: str,
                        base_dir: str, http_prefix: str,
                        domain: str,
                        onion_domain: str, i2p_domain: str,
                        getreq_start_time,
                        proxy_type: str, cookie: str,
                        debug: str,
                        curr_session) -> bool:
    """Shows the profile for a person
    """
    # look up a person
    actor_json = person_lookup(domain, path, base_dir)
    if not actor_json:
        return False
    add_alternate_domains(actor_json, domain, onion_domain, i2p_domain)
    if request_http(self.headers, debug):
        curr_session = \
            establish_session("showPersonProfile",
                              curr_session, proxy_type,
                              self.server)
        if not curr_session:
            http_404(self, 86)
            return True

        access_keys = self.server.access_keys
        city = None
        timezone = None
        if '/users/' in path:
            nickname = path.split('/users/')[1]
            if '/' in nickname:
                nickname = nickname.split('/')[0]
            if self.server.key_shortcuts.get(nickname):
                access_keys = \
                    self.server.key_shortcuts[nickname]

            city = get_spoofed_city(self.server.city,
                                    base_dir, nickname, domain)
            if self.server.account_timezone.get(nickname):
                timezone = \
                    self.server.account_timezone.get(nickname)
        bold_reading = False
        if self.server.bold_reading.get(nickname):
            bold_reading = True
        max_shares_on_profile = \
            self.server.max_shares_on_profile
        sites_unavailable = \
            self.server.sites_unavailable
        msg = \
            html_profile(self.server.signing_priv_key_pem,
                         self.server.rss_icon_at_top,
                         self.server.icons_as_buttons,
                         self.server.default_timeline,
                         self.server.recent_posts_cache,
                         self.server.max_recent_posts,
                         self.server.translate,
                         self.server.project_version,
                         base_dir, http_prefix, authorized,
                         actor_json, 'posts', curr_session,
                         self.server.cached_webfingers,
                         self.server.person_cache,
                         self.server.yt_replace_domain,
                         self.server.twitter_replacement_domain,
                         self.server.show_published_date_only,
                         self.server.newswire,
                         self.server.theme_name,
                         self.server.dormant_months,
                         self.server.peertube_instances,
                         self.server.allow_local_network_access,
                         self.server.text_mode_banner,
                         self.server.debug,
                         access_keys, city,
                         self.server.system_language,
                         self.server.max_like_count,
                         self.server.shared_items_federated_domains,
                         None, None, None,
                         self.server.cw_lists,
                         self.server.lists_enabled,
                         self.server.content_license_url,
                         timezone, bold_reading,
                         self.server.buy_sites,
                         None,
                         max_shares_on_profile,
                         sites_unavailable,
                         self.server.no_of_books,
                         self.server.auto_cw_cache).encode('utf-8')
        msglen = len(msg)
        set_headers(self, 'text/html', msglen,
                    cookie, calling_domain, False)
        write2(self, msg)
        fitness_performance(getreq_start_time,
                            self.server.fitness,
                            '_GET', '_show_person_profile',
                            debug)
        if self.server.debug:
            print('DEBUG: html actor sent')
    else:
        if secure_mode(curr_session, proxy_type, False,
                       self.server, self.headers, self.path):
            accept_str = self.headers['Accept']
            msg_str = json.dumps(actor_json, ensure_ascii=False)
            msg_str = convert_domains(calling_domain,
                                      referer_domain,
                                      msg_str, http_prefix,
                                      domain,
                                      self.server.onion_domain,
                                      self.server.i2p_domain)
            msg = msg_str.encode('utf-8')
            msglen = len(msg)
            if 'application/ld+json' in accept_str:
                set_headers(self, 'application/ld+json', msglen,
                            cookie, calling_domain, False)
            elif 'application/jrd+json' in accept_str:
                set_headers(self, 'application/jrd+json', msglen,
                            cookie, calling_domain, False)
            else:
                set_headers(self, 'application/activity+json', msglen,
                            cookie, calling_domain, False)
            write2(self, msg)
            fitness_performance(getreq_start_time,
                                self.server.fitness,
                                '_GET', '_show_person_profile json',
                                self.server.debug)
            if self.server.debug:
                print('DEBUG: json actor sent')
        else:
            http_404(self, 87)
    return True


def show_roles(self, calling_domain: str, referer_domain: str,
               path: str, base_dir: str, http_prefix: str,
               domain: str, getreq_start_time,
               proxy_type: str, cookie: str, debug: str,
               curr_session) -> bool:
    """Show roles within profile screen
    """
    named_status = path.split('/users/')[1]
    if '/' not in named_status:
        return False

    post_sections = named_status.split('/')
    nickname = post_sections[0]
    actor_filename = acct_dir(base_dir, nickname, domain) + '.json'
    if not os.path.isfile(actor_filename):
        return False

    actor_json = load_json(actor_filename)
    if not actor_json:
        return False

    if actor_json.get('hasOccupation'):
        if request_http(self.headers, debug):
            get_person = \
                person_lookup(domain, path.replace('/roles', ''),
                              base_dir)
            if get_person:
                default_timeline = \
                    self.server.default_timeline
                recent_posts_cache = \
                    self.server.recent_posts_cache
                cached_webfingers = \
                    self.server.cached_webfingers
                yt_replace_domain = \
                    self.server.yt_replace_domain
                twitter_replacement_domain = \
                    self.server.twitter_replacement_domain
                icons_as_buttons = \
                    self.server.icons_as_buttons

                access_keys = self.server.access_keys
                if self.server.key_shortcuts.get(nickname):
                    access_keys = self.server.key_shortcuts[nickname]

                roles_list = get_actor_roles_list(actor_json)
                city = \
                    get_spoofed_city(self.server.city,
                                     base_dir, nickname, domain)
                shared_items_federated_domains = \
                    self.server.shared_items_federated_domains

                timezone = None
                if self.server.account_timezone.get(nickname):
                    timezone = \
                        self.server.account_timezone.get(nickname)
                bold_reading = False
                if self.server.bold_reading.get(nickname):
                    bold_reading = True
                msg = \
                    html_profile(self.server.signing_priv_key_pem,
                                 self.server.rss_icon_at_top,
                                 icons_as_buttons,
                                 default_timeline,
                                 recent_posts_cache,
                                 self.server.max_recent_posts,
                                 self.server.translate,
                                 self.server.project_version,
                                 base_dir, http_prefix, True,
                                 get_person, 'roles',
                                 curr_session,
                                 cached_webfingers,
                                 self.server.person_cache,
                                 yt_replace_domain,
                                 twitter_replacement_domain,
                                 self.server.show_published_date_only,
                                 self.server.newswire,
                                 self.server.theme_name,
                                 self.server.dormant_months,
                                 self.server.peertube_instances,
                                 self.server.allow_local_network_access,
                                 self.server.text_mode_banner,
                                 self.server.debug,
                                 access_keys, city,
                                 self.server.system_language,
                                 self.server.max_like_count,
                                 shared_items_federated_domains,
                                 roles_list,
                                 None, None, self.server.cw_lists,
                                 self.server.lists_enabled,
                                 self.server.content_license_url,
                                 timezone, bold_reading,
                                 self.server.buy_sites, None,
                                 self.server.max_shares_on_profile,
                                 self.server.sites_unavailable,
                                 self.server.no_of_books,
                                 self.server.auto_cw_cache)
                msg = msg.encode('utf-8')
                msglen = len(msg)
                set_headers(self, 'text/html', msglen,
                            cookie, calling_domain, False)
                write2(self, msg)
                fitness_performance(getreq_start_time, self.server.fitness,
                                    '_GET', '_show_roles', debug)
        else:
            if secure_mode(curr_session, proxy_type, False,
                           self.server, self.headers, self.path):
                roles_list = get_actor_roles_list(actor_json)
                msg_str = json.dumps(roles_list, ensure_ascii=False)
                msg_str = convert_domains(calling_domain,
                                          referer_domain,
                                          msg_str, http_prefix,
                                          domain,
                                          self.server.onion_domain,
                                          self.server.i2p_domain)
                msg = msg_str.encode('utf-8')
                msglen = len(msg)
                protocol_str = \
                    get_json_content_from_accept(self.headers['Accept'])
                set_headers(self, protocol_str, msglen,
                            None, calling_domain, False)
                write2(self, msg)
                fitness_performance(getreq_start_time, self.server.fitness,
                                    '_GET', '_show_roles json', debug)
            else:
                http_404(self, 65)
        return True
    return False


def show_skills(self, calling_domain: str, referer_domain: str,
                path: str, base_dir: str, http_prefix: str,
                domain: str, getreq_start_time, proxy_type: str,
                cookie: str, debug: str, curr_session) -> bool:
    """Show skills on the profile screen
    """
    named_status = path.split('/users/')[1]
    if '/' in named_status:
        post_sections = named_status.split('/')
        nickname = post_sections[0]
        actor_filename = acct_dir(base_dir, nickname, domain) + '.json'
        if os.path.isfile(actor_filename):
            actor_json = load_json(actor_filename)
            if actor_json:
                if no_of_actor_skills(actor_json) > 0:
                    if request_http(self.headers, self.server.debug):
                        get_person = \
                            person_lookup(domain,
                                          path.replace('/skills', ''),
                                          base_dir)
                        if get_person:
                            default_timeline =  \
                                self.server.default_timeline
                            recent_posts_cache = \
                                self.server.recent_posts_cache
                            cached_webfingers = \
                                self.server.cached_webfingers
                            yt_replace_domain = \
                                self.server.yt_replace_domain
                            twitter_replacement_domain = \
                                self.server.twitter_replacement_domain
                            show_published_date_only = \
                                self.server.show_published_date_only
                            icons_as_buttons = \
                                self.server.icons_as_buttons
                            allow_local_network_access = \
                                self.server.allow_local_network_access
                            access_keys = self.server.access_keys
                            if self.server.key_shortcuts.get(nickname):
                                access_keys = \
                                    self.server.key_shortcuts[nickname]
                            actor_skills_list = \
                                get_occupation_skills(actor_json)
                            skills = \
                                get_skills_from_list(actor_skills_list)
                            city = get_spoofed_city(self.server.city,
                                                    base_dir,
                                                    nickname, domain)
                            shared_items_fed_domains = \
                                self.server.shared_items_federated_domains
                            signing_priv_key_pem = \
                                self.server.signing_priv_key_pem
                            content_license_url = \
                                self.server.content_license_url
                            peertube_instances = \
                                self.server.peertube_instances
                            timezone = None
                            nick = nickname
                            if self.server.account_timezone.get(nick):
                                timezone = \
                                    self.server.account_timezone.get(nick)
                            bold_reading = False
                            if self.server.bold_reading.get(nick):
                                bold_reading = True
                            max_shares_on_profile = \
                                self.server.max_shares_on_profile
                            msg = \
                                html_profile(signing_priv_key_pem,
                                             self.server.rss_icon_at_top,
                                             icons_as_buttons,
                                             default_timeline,
                                             recent_posts_cache,
                                             self.server.max_recent_posts,
                                             self.server.translate,
                                             self.server.project_version,
                                             base_dir, http_prefix, True,
                                             get_person, 'skills',
                                             curr_session,
                                             cached_webfingers,
                                             self.server.person_cache,
                                             yt_replace_domain,
                                             twitter_replacement_domain,
                                             show_published_date_only,
                                             self.server.newswire,
                                             self.server.theme_name,
                                             self.server.dormant_months,
                                             peertube_instances,
                                             allow_local_network_access,
                                             self.server.text_mode_banner,
                                             self.server.debug,
                                             access_keys, city,
                                             self.server.system_language,
                                             self.server.max_like_count,
                                             shared_items_fed_domains,
                                             skills,
                                             None, None,
                                             self.server.cw_lists,
                                             self.server.lists_enabled,
                                             content_license_url,
                                             timezone, bold_reading,
                                             self.server.buy_sites,
                                             None,
                                             max_shares_on_profile,
                                             self.server.sites_unavailable,
                                             self.server.no_of_books,
                                             self.server.auto_cw_cache)
                            msg = msg.encode('utf-8')
                            msglen = len(msg)
                            set_headers(self, 'text/html', msglen,
                                        cookie, calling_domain,
                                              False)
                            write2(self, msg)
                            fitness_performance(getreq_start_time,
                                                self.server.fitness,
                                                '_GET', '_show_skills',
                                                self.server.debug)
                    else:
                        if secure_mode(curr_session,
                                       proxy_type, False,
                                       self.server,
                                       self.headers,
                                       self.path):
                            actor_skills_list = \
                                get_occupation_skills(actor_json)
                            skills = \
                                get_skills_from_list(actor_skills_list)
                            msg_str = json.dumps(skills,
                                                 ensure_ascii=False)
                            onion_domain = self.server.onion_domain
                            i2p_domain = self.server.i2p_domain
                            msg_str = convert_domains(calling_domain,
                                                      referer_domain,
                                                      msg_str,
                                                      http_prefix,
                                                      domain,
                                                      onion_domain,
                                                      i2p_domain)
                            msg = msg_str.encode('utf-8')
                            msglen = len(msg)
                            accept_str = self.headers['Accept']
                            protocol_str = \
                                get_json_content_from_accept(accept_str)
                            set_headers(self, protocol_str, msglen, None,
                                        calling_domain, False)
                            write2(self, msg)
                            fitness_performance(getreq_start_time,
                                                self.server.fitness,
                                                '_GET',
                                                '_show_skills json',
                                                debug)
                        else:
                            http_404(self, 66)
                    return True
    actor = path.replace('/skills', '')
    actor_absolute = \
        get_instance_url(calling_domain,
                         self.server.http_prefix,
                         self.server.domain_full,
                         self.server.onion_domain,
                         self.server.i2p_domain) + \
        actor
    redirect_headers(self, actor_absolute, cookie, calling_domain)
    return True


def edit_profile2(self, calling_domain: str, path: str,
                  translate: {}, base_dir: str,
                  domain: str, port: int,
                  cookie: str) -> bool:
    """Show the edit profile screen
    """
    if '/users/' in path and path.endswith('/editprofile'):
        peertube_instances = self.server.peertube_instances
        nickname = get_nickname_from_actor(path)

        access_keys = self.server.access_keys
        if '/users/' in path:
            if self.server.key_shortcuts.get(nickname):
                access_keys = self.server.key_shortcuts[nickname]

        default_reply_interval_hrs = self.server.default_reply_interval_hrs
        msg = html_edit_profile(self.server, translate,
                                base_dir, path, domain, port,
                                self.server.default_timeline,
                                self.server.theme_name,
                                peertube_instances,
                                self.server.text_mode_banner,
                                self.server.user_agents_blocked,
                                self.server.crawlers_allowed,
                                access_keys,
                                default_reply_interval_hrs,
                                self.server.cw_lists,
                                self.server.lists_enabled,
                                self.server.system_language,
                                self.server.min_images_for_accounts,
                                self.server.max_recent_posts,
                                self.server.reverse_sequence,
                                self.server.buy_sites,
                                self.server.block_military,
                                self.server.block_federated_endpoints)
        if msg:
            msg = msg.encode('utf-8')
            msglen = len(msg)
            set_headers(self, 'text/html', msglen,
                        cookie, calling_domain, False)
            write2(self, msg)
        else:
            http_404(self, 105)
        return True
    return False
