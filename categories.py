__filename__ = "categories.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "RSS Feeds"

import os
import datetime


def get_hashtag_category(base_dir: str, hashtag: str) -> str:
    """Returns the category for the hashtag
    """
    categoryFilename = base_dir + '/tags/' + hashtag + '.category'
    if not os.path.isfile(categoryFilename):
        categoryFilename = base_dir + '/tags/' + hashtag.title() + '.category'
        if not os.path.isfile(categoryFilename):
            categoryFilename = \
                base_dir + '/tags/' + hashtag.upper() + '.category'
            if not os.path.isfile(categoryFilename):
                return ''

    categoryStr = None
    try:
        with open(categoryFilename, 'r') as fp:
            categoryStr = fp.read()
    except OSError:
        print('EX: unable to read category ' + categoryFilename)
    if categoryStr:
        return categoryStr
    return ''


def get_hashtag_categories(base_dir: str,
                           recent: bool = False,
                           category: str = None) -> None:
    """Returns a dictionary containing hashtag categories
    """
    maxTagLength = 42
    hashtagCategories = {}

    if recent:
        curr_time = datetime.datetime.utcnow()
        daysSinceEpoch = (curr_time - datetime.datetime(1970, 1, 1)).days
        recently = daysSinceEpoch - 1

    for subdir, dirs, files in os.walk(base_dir + '/tags'):
        for f in files:
            if not f.endswith('.category'):
                continue
            categoryFilename = os.path.join(base_dir + '/tags', f)
            if not os.path.isfile(categoryFilename):
                continue
            hashtag = f.split('.')[0]
            if len(hashtag) > maxTagLength:
                continue
            with open(categoryFilename, 'r') as fp:
                categoryStr = fp.read()

                if not categoryStr:
                    continue

                if category:
                    # only return a dictionary for a specific category
                    if categoryStr != category:
                        continue

                if recent:
                    tagsFilename = base_dir + '/tags/' + hashtag + '.txt'
                    if not os.path.isfile(tagsFilename):
                        continue
                    modTimesinceEpoc = \
                        os.path.getmtime(tagsFilename)
                    lastModifiedDate = \
                        datetime.datetime.fromtimestamp(modTimesinceEpoc)
                    fileDaysSinceEpoch = \
                        (lastModifiedDate -
                         datetime.datetime(1970, 1, 1)).days
                    if fileDaysSinceEpoch < recently:
                        continue

                if not hashtagCategories.get(categoryStr):
                    hashtagCategories[categoryStr] = [hashtag]
                else:
                    if hashtag not in hashtagCategories[categoryStr]:
                        hashtagCategories[categoryStr].append(hashtag)
        break
    return hashtagCategories


def update_hashtag_categories(base_dir: str) -> None:
    """Regenerates the list of hashtag categories
    """
    categoryListFilename = base_dir + '/accounts/categoryList.txt'
    hashtagCategories = get_hashtag_categories(base_dir)
    if not hashtagCategories:
        if os.path.isfile(categoryListFilename):
            try:
                os.remove(categoryListFilename)
            except OSError:
                print('EX: update_hashtag_categories ' +
                      'unable to delete cached category list ' +
                      categoryListFilename)
        return

    categoryList = []
    for categoryStr, hashtagList in hashtagCategories.items():
        categoryList.append(categoryStr)
    categoryList.sort()

    categoryListStr = ''
    for categoryStr in categoryList:
        categoryListStr += categoryStr + '\n'

    # save a list of available categories for quick lookup
    try:
        with open(categoryListFilename, 'w+') as fp:
            fp.write(categoryListStr)
    except OSError:
        print('EX: unable to write category ' + categoryListFilename)


def _valid_hashtag_category(category: str) -> bool:
    """Returns true if the category name is valid
    """
    if not category:
        return False

    invalidChars = (',', ' ', '<', ';', '\\', '"', '&', '#')
    for ch in invalidChars:
        if ch in category:
            return False

    # too long
    if len(category) > 40:
        return False

    return True


def set_hashtag_category(base_dir: str, hashtag: str, category: str,
                         update: bool, force: bool = False) -> bool:
    """Sets the category for the hashtag
    """
    if not _valid_hashtag_category(category):
        return False

    if not force:
        hashtagFilename = base_dir + '/tags/' + hashtag + '.txt'
        if not os.path.isfile(hashtagFilename):
            hashtag = hashtag.title()
            hashtagFilename = base_dir + '/tags/' + hashtag + '.txt'
            if not os.path.isfile(hashtagFilename):
                hashtag = hashtag.upper()
                hashtagFilename = base_dir + '/tags/' + hashtag + '.txt'
                if not os.path.isfile(hashtagFilename):
                    return False

    if not os.path.isdir(base_dir + '/tags'):
        os.mkdir(base_dir + '/tags')
    categoryFilename = base_dir + '/tags/' + hashtag + '.category'
    if force:
        # don't overwrite any existing categories
        if os.path.isfile(categoryFilename):
            return False

    categoryWritten = False
    try:
        with open(categoryFilename, 'w+') as fp:
            fp.write(category)
            categoryWritten = True
    except OSError as ex:
        print('EX: unable to write category ' + categoryFilename +
              ' ' + str(ex))

    if categoryWritten:
        if update:
            update_hashtag_categories(base_dir)
        return True

    return False


def guess_hashtag_category(tagName: str, hashtagCategories: {}) -> str:
    """Tries to guess a category for the given hashtag.
    This works by trying to find the longest similar hashtag
    """
    if len(tagName) < 4:
        return ''

    categoryMatched = ''
    tagMatchedLen = 0

    for categoryStr, hashtagList in hashtagCategories.items():
        for hashtag in hashtagList:
            if len(hashtag) < 4:
                # avoid matching very small strings which often
                # lead to spurious categories
                continue
            if hashtag not in tagName:
                if tagName not in hashtag:
                    continue
            if not categoryMatched:
                tagMatchedLen = len(hashtag)
                categoryMatched = categoryStr
            else:
                # match the longest tag
                if len(hashtag) > tagMatchedLen:
                    categoryMatched = categoryStr
    if not categoryMatched:
        return ''
    return categoryMatched
