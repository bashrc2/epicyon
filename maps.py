__filename__ = "maps.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.3.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"


import os
import datetime
from utils import is_float
from utils import acct_dir
from utils import load_json
from utils import save_json


def get_location_from_tags(tags: []) -> str:
    """Returns the location from the tags list
    """
    for tag_item in tags:
        if not tag_item.get('type'):
            continue
        if tag_item['type'] != 'Place':
            continue
        if not tag_item.get('name'):
            continue
        if not isinstance(tag_item['name'], str):
            continue
        return tag_item['name'].replace('\n', ' ')
    return None


def _geocoords_from_osm_link(url: str, osm_domain: str) -> (int, float, float):
    """Returns geocoordinates from an OSM map link
    """
    if osm_domain not in url:
        return None, None, None
    if '#map=' not in url:
        return None, None, None

    coords_str = url.split('#map=')[1]
    if '/' not in coords_str:
        return None, None, None

    coords = coords_str.split('/')
    if len(coords) != 3:
        return None, None, None
    zoom = coords[0]
    if not zoom.isdigit():
        return None, None, None
    latitude = coords[1]
    if not is_float(latitude):
        return None, None, None
    longitude = coords[2]
    if not is_float(longitude):
        return None, None, None
    zoom = int(zoom)
    latitude = float(latitude)
    longitude = float(longitude)
    return zoom, latitude, longitude


def _geocoords_from_osmorg_link(url: str) -> (int, float, float):
    """Returns geocoordinates from an OSM map link
    """
    osm_domain = 'osm.org'
    if osm_domain not in url:
        return None, None, None
    if 'mlat=' not in url:
        return None, None, None
    if 'mlon=' not in url:
        return None, None, None
    if 'zoom=' not in url:
        return None, None, None

    latitude = url.split('mlat=')[1]
    if '&' in latitude:
        latitude = latitude.split('&')[0]
    if not is_float(latitude):
        return None, None, None

    longitude = url.split('mlon=')[1]
    if '&' in longitude:
        longitude = longitude.split('&')[0]
    if not is_float(longitude):
        return None, None, None

    zoom = url.split('zoom=')[1]
    if '&' in zoom:
        zoom = zoom.split('&')[0]
    if not zoom.isdigit():
        return None, None, None
    zoom = int(zoom)
    latitude = float(latitude)
    longitude = float(longitude)
    return zoom, latitude, longitude


def _geocoords_from_gmaps_link(url: str) -> (int, float, float):
    """Returns geocoordinates from a Gmaps link
    """
    if '/maps/' not in url:
        return None, None, None
    coords_str = url.split('/maps', 1)[1]
    if '/@' not in coords_str:
        return None, None, None

    coords_str = coords_str.split('/@', 1)[1]
    if 'z' not in coords_str:
        return None, None, None
    coords_str = coords_str.split('z', 1)[0]

    if ',' not in coords_str:
        return None, None, None

    coords = coords_str.split(',')
    if len(coords) != 3:
        return None, None, None
    zoom = coords[2]
    if not zoom.isdigit():
        return None, None, None
    latitude = coords[0]
    if not is_float(latitude):
        return None, None, None
    longitude = coords[1]
    if not is_float(longitude):
        return None, None, None
    zoom = int(zoom)
    latitude = float(latitude)
    longitude = float(longitude)
    return zoom, latitude, longitude


def _geocoords_from_bmaps_link(url: str) -> (int, float, float):
    """Returns geocoordinates from a bing map link
    """
    prefixes = ('/maps?cp=', '/maps/directions?cp=')
    map_prefix = None
    for prefix in prefixes:
        if prefix in url:
            map_prefix = prefix
            break
    if not map_prefix:
        return None, None, None

    coords_str = url.split(map_prefix)[1]
    if '~' not in coords_str:
        return None, None, None
    orig_coords_str = coords_str
    if '&' in coords_str:
        coords_str = coords_str.split('&')[0]
    if ';' in coords_str:
        coords_str = coords_str.split(';')[0]

    coords = coords_str.split('~')
    if len(coords) != 2:
        return None, None, None
    latitude = coords[0]
    if not is_float(latitude):
        return None, None, None
    longitude = coords[1]
    if not is_float(longitude):
        return None, None, None
    zoom = 17
    if 'lvl=' in orig_coords_str:
        zoom = orig_coords_str.split('lvl=')[1]
        if '&' in zoom:
            zoom = zoom.split('&')[0]
        if ';' in zoom:
            zoom = zoom.split(';')[0]
    if not zoom.isdigit():
        return None, None, None
    zoom = int(zoom)
    latitude = float(latitude)
    longitude = float(longitude)
    return zoom, latitude, longitude


def _geocoords_from_waze_link(url: str) -> (int, float, float):
    """Returns geocoordinates from a waze map link
    """
    prefixes = ['/ul?ll=']
    map_prefix = None
    for prefix in prefixes:
        if prefix in url:
            map_prefix = prefix
            break
    if not map_prefix:
        return None, None, None

    coords_str = url.split(map_prefix)[1]
    orig_coords_str = coords_str
    if '&' in coords_str:
        coords_str = coords_str.split('&')[0]
    if '%2C' not in coords_str and ',' not in coords_str:
        return None, None, None

    if '%2C' in coords_str:
        coords = coords_str.split('%2C')
    else:
        coords = coords_str.split(',')
    if len(coords) != 2:
        return None, None, None
    latitude = coords[0]
    if not is_float(latitude):
        return None, None, None
    longitude = coords[1]
    if not is_float(longitude):
        return None, None, None
    zoom = 17
    if 'zoom=' in orig_coords_str:
        zoom = orig_coords_str.split('zoom=')[1]
        if '&' in zoom:
            zoom = zoom.split('&')[0]
    if not zoom.isdigit():
        return None, None, None
    zoom = int(zoom)
    latitude = float(latitude)
    longitude = float(longitude)
    return zoom, latitude, longitude


def _geocoords_from_wego_link(url: str) -> (int, float, float):
    """Returns geocoordinates from a wego map link
    """
    prefixes = ['/?map=']
    map_prefix = None
    for prefix in prefixes:
        if prefix in url:
            map_prefix = prefix
            break
    if not map_prefix:
        return None, None, None

    coords_str = url.split(map_prefix)[1]
    if ',' not in coords_str:
        return None, None, None

    coords = coords_str.split(',')
    if len(coords) < 3:
        return None, None, None
    latitude = coords[0]
    if not is_float(latitude):
        return None, None, None
    longitude = coords[1]
    if not is_float(longitude):
        return None, None, None
    zoom = coords[2]
    if not zoom.isdigit():
        return None, None, None
    zoom = int(zoom)
    latitude = float(latitude)
    longitude = float(longitude)
    return zoom, latitude, longitude


def geocoords_from_map_link(url: str,
                            osm_domain: str = 'openstreetmap.org') -> (int,
                                                                       float,
                                                                       float):
    """Returns geocoordinates from a map link url
    """
    if osm_domain in url:
        return _geocoords_from_osm_link(url, osm_domain)
    if 'osm.org' in url and 'mlat=' in url:
        return _geocoords_from_osmorg_link(url)
    if '.google.co' in url:
        return _geocoords_from_gmaps_link(url)
    if '.bing.co' in url:
        return _geocoords_from_bmaps_link(url)
    if '.waze.co' in url:
        return _geocoords_from_waze_link(url)
    if 'wego.here.co' in url:
        return _geocoords_from_wego_link(url)
    return None, None, None


def html_open_street_map(url: str,
                         bounding_box_degrees: float,
                         translate: {},
                         width: str = "725",
                         height: str = "650") -> str:
    """Returns embed html for an OSM link
    """
    osm_domain = 'openstreetmap.org'
    zoom, latitude, longitude = geocoords_from_map_link(url, osm_domain)
    if not latitude:
        return ''
    if not longitude:
        return ''
    if not zoom:
        return ''

    html_str = \
        '<iframe width="' + width + '" height="' + height + \
        '" frameborder="0" ' + \
        'scrolling="no" marginheight="0" marginwidth="0" ' + \
        'src="https://www.' + osm_domain + '/export/embed.html?' + \
        'bbox=' + str(longitude - bounding_box_degrees) + \
        '%2C' + \
        str(latitude - bounding_box_degrees) + \
        '%2C' + \
        str(longitude + bounding_box_degrees) + \
        '%2C' + \
        str(latitude + bounding_box_degrees) + \
        '&amp;layer=mapnik" style="border: 1px solid black"></iframe>' + \
        '<br/><small><a href="https://www.' + osm_domain + '/#map=' + \
        str(zoom) + '/' + str(latitude) + '/' + str(longitude) + \
        '">' + translate['View Larger Map'] + '</a></small>\n'
    return html_str


def set_map_preferences_url(base_dir: str, nickname: str, domain: str,
                            maps_website_url: str) -> None:
    """Sets the preferred maps website for an account
    """
    maps_filename = \
        acct_dir(base_dir, nickname, domain) + '/map_preferences.json'
    if os.path.isfile(maps_filename):
        maps_json = load_json(maps_filename)
        maps_json['url'] = maps_website_url
    else:
        maps_json = {
            'url': maps_website_url
        }
    save_json(maps_json, maps_filename)


def get_map_preferences_url(base_dir: str, nickname: str, domain: str) -> str:
    """Gets the preferred maps website for an account
    """
    maps_filename = \
        acct_dir(base_dir, nickname, domain) + '/map_preferences.json'
    if os.path.isfile(maps_filename):
        maps_json = load_json(maps_filename)
        if maps_json.get('url'):
            return maps_json['url']
    return None


def set_map_preferences_coords(base_dir: str, nickname: str, domain: str,
                               latitude: float, longitude: float,
                               zoom: int) -> None:
    """Sets the preferred maps website coordinates for an account
    """
    maps_filename = \
        acct_dir(base_dir, nickname, domain) + '/map_preferences.json'
    if os.path.isfile(maps_filename):
        maps_json = load_json(maps_filename)
        maps_json['latitude'] = latitude
        maps_json['longitude'] = longitude
        maps_json['zoom'] = zoom
    else:
        maps_json = {
            'latitude': latitude,
            'longitude': longitude,
            'zoom': zoom
        }
    save_json(maps_json, maps_filename)


def get_map_preferences_coords(base_dir: str,
                               nickname: str,
                               domain: str) -> (float, float, int):
    """Gets the preferred maps website coordinates for an account
    """
    maps_filename = \
        acct_dir(base_dir, nickname, domain) + '/map_preferences.json'
    if os.path.isfile(maps_filename):
        maps_json = load_json(maps_filename)
        if maps_json.get('latitude') and \
           maps_json.get('longitude') and \
           maps_json.get('zoom'):
            return maps_json['latitude'], \
                maps_json['longitude'], \
                maps_json['zoom']
    return None, None, None


def get_map_links_from_post_content(content: str) -> []:
    """Returns a list of map links
    """
    osm_domain = 'openstreetmap.org'
    sections = content.split('://')
    map_links = []
    ctr = 0
    for link_str in sections:
        if ctr == 0:
            ctr += 1
            continue
        url = link_str
        if '"' in link_str:
            url = link_str.split('"')[0]
        if '<' in link_str:
            url = link_str.split('<')[0]
        zoom, latitude, longitude = geocoords_from_map_link(url, osm_domain)
        if not latitude:
            continue
        if not longitude:
            continue
        if not zoom:
            continue
        if url not in map_links:
            map_links.append(url)
        ctr += 1
    return map_links


def add_tag_map_links(tag_maps_dir: str, tag_name: str,
                      map_links: [], published: str, post_url: str) -> None:
    """Appends to a hashtag file containing map links
    This is used to show a map for a particular hashtag
    """
    tag_map_filename = tag_maps_dir + '/' + tag_name + '.txt'

    # read the existing map links
    existing_map_links = []
    if os.path.isfile(tag_map_filename):
        try:
            with open(tag_map_filename, 'r', encoding='utf-8') as fp_tag:
                existing_map_links = fp_tag.read().split('\n')
        except OSError:
            print('EX: error reading tag map ' + tag_map_filename)

    # combine map links with the existing list
    secs_since_epoch = \
        int((datetime.datetime.strptime(published, '%Y-%m-%dT%H:%M:%SZ') -
             datetime.datetime(1970, 1, 1)).total_seconds())
    links_changed = False
    for link in map_links:
        line = str(secs_since_epoch) + ' ' + link + ' ' + post_url
        if line in existing_map_links:
            continue
        links_changed = True
        existing_map_links = [line] + existing_map_links
    if not links_changed:
        return

    # sort the list of map links
    existing_map_links.sort(reverse=True)
    map_links_str = ''
    ctr = 0
    for link in existing_map_links:
        if not link:
            continue
        map_links_str += link + '\n'
        ctr += 1
        # don't allow the list to grow indefinitely
        if ctr >= 2000:
            break

    # save the tag
    try:
        with open(tag_map_filename, 'w+', encoding='utf-8') as fp_tag:
            fp_tag.write(map_links_str)
    except OSError:
        print('EX: error writing tag map ' + tag_map_filename)
