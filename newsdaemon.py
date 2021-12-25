__filename__ = "newsdaemon.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Web Interface Columns"

# Example hashtag logic:
#
# if moderated and not #imcoxford then block
# if #pol and contains "westminster" then add #britpol
# if #unwantedtag then block

import os
import time
import datetime
import html
from shutil import rmtree
from subprocess import Popen
from collections import OrderedDict
from newswire import getDictFromNewswire
# from posts import sendSignedJson
from posts import createNewsPost
from posts import archivePostsForPerson
from content import validHashTag
from utils import getBaseContentFromPost
from utils import removeHtml
from utils import getFullDomain
from utils import loadJson
from utils import saveJson
from utils import getStatusNumber
from utils import clearFromPostCaches
from utils import dangerousMarkup
from utils import localActorUrl
from inbox import storeHashTags
from session import createSession


def _updateFeedsOutboxIndex(base_dir: str, domain: str, postId: str) -> None:
    """Updates the index used for imported RSS feeds
    """
    basePath = base_dir + '/accounts/news@' + domain
    indexFilename = basePath + '/outbox.index'

    if os.path.isfile(indexFilename):
        if postId not in open(indexFilename).read():
            try:
                with open(indexFilename, 'r+') as feedsFile:
                    content = feedsFile.read()
                    if postId + '\n' not in content:
                        feedsFile.seek(0, 0)
                        feedsFile.write(postId + '\n' + content)
                        print('DEBUG: feeds post added to index')
            except Exception as ex:
                print('WARN: Failed to write entry to feeds posts index ' +
                      indexFilename + ' ' + str(ex))
    else:
        try:
            with open(indexFilename, 'w+') as feedsFile:
                feedsFile.write(postId + '\n')
        except OSError:
            print('EX: unable to write ' + indexFilename)


def _saveArrivedTime(base_dir: str, postFilename: str, arrived: str) -> None:
    """Saves the time when an rss post arrived to a file
    """
    try:
        with open(postFilename + '.arrived', 'w+') as arrivedFile:
            arrivedFile.write(arrived)
    except OSError:
        print('EX: unable to write ' + postFilename + '.arrived')


def _removeControlCharacters(content: str) -> str:
    """Remove escaped html
    """
    if '&' in content:
        return html.unescape(content)
    return content


def _hashtagLogicalNot(tree: [], hashtags: [], moderated: bool,
                       content: str, url: str) -> bool:
    """ NOT
    """
    if len(tree) != 2:
        return False
    if isinstance(tree[1], str):
        return tree[1] not in hashtags
    elif isinstance(tree[1], list):
        return not hashtagRuleResolve(tree[1], hashtags,
                                      moderated, content, url)
    return False


def _hashtagLogicalContains(tree: [], hashtags: [], moderated: bool,
                            content: str, url: str) -> bool:
    """ Contains
    """
    if len(tree) != 2:
        return False
    matchStr = None
    if isinstance(tree[1], str):
        matchStr = tree[1]
    elif isinstance(tree[1], list):
        matchStr = tree[1][0]
    if matchStr:
        if matchStr.startswith('"') and matchStr.endswith('"'):
            matchStr = matchStr[1:]
            matchStr = matchStr[:len(matchStr) - 1]
        matchStrLower = matchStr.lower()
        contentWithoutTags = content.replace('#' + matchStrLower, '')
        return matchStrLower in contentWithoutTags
    return False


def _hashtagLogicalFrom(tree: [], hashtags: [], moderated: bool,
                        content: str, url: str) -> bool:
    """ FROM
    """
    if len(tree) != 2:
        return False
    matchStr = None
    if isinstance(tree[1], str):
        matchStr = tree[1]
    elif isinstance(tree[1], list):
        matchStr = tree[1][0]
    if matchStr:
        if matchStr.startswith('"') and matchStr.endswith('"'):
            matchStr = matchStr[1:]
            matchStr = matchStr[:len(matchStr) - 1]
        return matchStr.lower() in url
    return False


def _hashtagLogicalAnd(tree: [], hashtags: [], moderated: bool,
                       content: str, url: str) -> bool:
    """ AND
    """
    if len(tree) < 3:
        return False
    for argIndex in range(1, len(tree)):
        argValue = False
        if isinstance(tree[argIndex], str):
            argValue = (tree[argIndex] in hashtags)
        elif isinstance(tree[argIndex], list):
            argValue = hashtagRuleResolve(tree[argIndex],
                                          hashtags, moderated,
                                          content, url)
        if not argValue:
            return False
    return True


def _hashtagLogicalOr(tree: [], hashtags: [], moderated: bool,
                      content: str, url: str) -> bool:
    """ OR
    """
    if len(tree) < 3:
        return False
    for argIndex in range(1, len(tree)):
        argValue = False
        if isinstance(tree[argIndex], str):
            argValue = (tree[argIndex] in hashtags)
        elif isinstance(tree[argIndex], list):
            argValue = hashtagRuleResolve(tree[argIndex],
                                          hashtags, moderated,
                                          content, url)
        if argValue:
            return True
    return False


def _hashtagLogicalXor(tree: [], hashtags: [], moderated: bool,
                       content: str, url: str) -> bool:
    """ XOR
    """
    if len(tree) < 3:
        return False
    trueCtr = 0
    for argIndex in range(1, len(tree)):
        argValue = False
        if isinstance(tree[argIndex], str):
            argValue = (tree[argIndex] in hashtags)
        elif isinstance(tree[argIndex], list):
            argValue = hashtagRuleResolve(tree[argIndex],
                                          hashtags, moderated,
                                          content, url)
        if argValue:
            trueCtr += 1
    if trueCtr == 1:
        return True
    return False


def hashtagRuleResolve(tree: [], hashtags: [], moderated: bool,
                       content: str, url: str) -> bool:
    """Returns whether the tree for a hashtag rule evaluates to true or false
    """
    if not tree:
        return False

    if tree[0] == 'not':
        return _hashtagLogicalNot(tree, hashtags, moderated, content, url)
    elif tree[0] == 'contains':
        return _hashtagLogicalContains(tree, hashtags, moderated, content, url)
    elif tree[0] == 'from':
        return _hashtagLogicalFrom(tree, hashtags, moderated, content, url)
    elif tree[0] == 'and':
        return _hashtagLogicalAnd(tree, hashtags, moderated, content, url)
    elif tree[0] == 'or':
        return _hashtagLogicalOr(tree, hashtags, moderated, content, url)
    elif tree[0] == 'xor':
        return _hashtagLogicalXor(tree, hashtags, moderated, content, url)
    elif tree[0].startswith('#') and len(tree) == 1:
        return tree[0] in hashtags
    elif tree[0].startswith('moderated'):
        return moderated
    elif tree[0].startswith('"') and tree[0].endswith('"'):
        return True

    return False


def hashtagRuleTree(operators: [],
                    conditionsStr: str,
                    tagsInConditions: [],
                    moderated: bool) -> []:
    """Walks the tree
    """
    if not operators and conditionsStr:
        conditionsStr = conditionsStr.strip()
        isStr = conditionsStr.startswith('"') and conditionsStr.endswith('"')
        if conditionsStr.startswith('#') or isStr or \
           conditionsStr in operators or \
           conditionsStr == 'moderated' or \
           conditionsStr == 'contains':
            if conditionsStr.startswith('#'):
                if conditionsStr not in tagsInConditions:
                    if ' ' not in conditionsStr or \
                       conditionsStr.startswith('"'):
                        tagsInConditions.append(conditionsStr)
            return [conditionsStr.strip()]
        else:
            return None
    if not operators or not conditionsStr:
        return None
    tree = None
    conditionsStr = conditionsStr.strip()
    isStr = conditionsStr.startswith('"') and conditionsStr.endswith('"')
    if conditionsStr.startswith('#') or isStr or \
       conditionsStr in operators or \
       conditionsStr == 'moderated' or \
       conditionsStr == 'contains':
        if conditionsStr.startswith('#'):
            if conditionsStr not in tagsInConditions:
                if ' ' not in conditionsStr or \
                   conditionsStr.startswith('"'):
                    tagsInConditions.append(conditionsStr)
        tree = [conditionsStr.strip()]
    ctr = 0
    while ctr < len(operators):
        op = operators[ctr]
        opMatch = ' ' + op + ' '
        if opMatch not in conditionsStr and \
           not conditionsStr.startswith(op + ' '):
            ctr += 1
            continue
        else:
            tree = [op]
            if opMatch in conditionsStr:
                sections = conditionsStr.split(opMatch)
            else:
                sections = conditionsStr.split(op + ' ', 1)
            for subConditionStr in sections:
                result = hashtagRuleTree(operators[ctr + 1:],
                                         subConditionStr,
                                         tagsInConditions, moderated)
                if result:
                    tree.append(result)
            break
    return tree


def _hashtagAdd(base_dir: str, http_prefix: str, domainFull: str,
                postJsonObject: {},
                actionStr: str, hashtags: [], systemLanguage: str,
                translate: {}) -> None:
    """Adds a hashtag via a hashtag rule
    """
    addHashtag = actionStr.split('add ', 1)[1].strip()
    if not addHashtag.startswith('#'):
        return

    if addHashtag not in hashtags:
        hashtags.append(addHashtag)
    htId = addHashtag.replace('#', '')
    if not validHashTag(htId):
        return

    hashtagUrl = http_prefix + "://" + domainFull + "/tags/" + htId
    newTag = {
        'href': hashtagUrl,
        'name': addHashtag,
        'type': 'Hashtag'
    }
    # does the tag already exist?
    addTagObject = None
    for t in postJsonObject['object']['tag']:
        if t.get('type') and t.get('name'):
            if t['type'] == 'Hashtag' and \
               t['name'] == addHashtag:
                addTagObject = t
                break
    # append the tag if it wasn't found
    if not addTagObject:
        postJsonObject['object']['tag'].append(newTag)
    # add corresponding html to the post content
    hashtagHtml = \
        " <a href=\"" + hashtagUrl + "\" class=\"addedHashtag\" " + \
        "rel=\"tag\">#<span>" + htId + "</span></a>"
    content = getBaseContentFromPost(postJsonObject, systemLanguage)
    if hashtagHtml in content:
        return

    if content.endswith('</p>'):
        content = \
            content[:len(content) - len('</p>')] + \
            hashtagHtml + '</p>'
    else:
        content += hashtagHtml
    postJsonObject['object']['content'] = content
    domain = domainFull
    if ':' in domain:
        domain = domain.split(':')[0]
    storeHashTags(base_dir, 'news', domain,
                  http_prefix, domainFull,
                  postJsonObject, translate)


def _hashtagRemove(http_prefix: str, domainFull: str, postJsonObject: {},
                   actionStr: str, hashtags: [], systemLanguage: str) -> None:
    """Removes a hashtag via a hashtag rule
    """
    rmHashtag = actionStr.split('remove ', 1)[1].strip()
    if not rmHashtag.startswith('#'):
        return

    if rmHashtag in hashtags:
        hashtags.remove(rmHashtag)
    htId = rmHashtag.replace('#', '')
    hashtagUrl = http_prefix + "://" + domainFull + "/tags/" + htId
    # remove tag html from the post content
    hashtagHtml = \
        "<a href=\"" + hashtagUrl + "\" class=\"addedHashtag\" " + \
        "rel=\"tag\">#<span>" + htId + "</span></a>"
    content = getBaseContentFromPost(postJsonObject, systemLanguage)
    if hashtagHtml in content:
        content = content.replace(hashtagHtml, '').replace('  ', ' ')
        postJsonObject['object']['content'] = content
        postJsonObject['object']['contentMap'][systemLanguage] = content
    rmTagObject = None
    for t in postJsonObject['object']['tag']:
        if t.get('type') and t.get('name'):
            if t['type'] == 'Hashtag' and \
               t['name'] == rmHashtag:
                rmTagObject = t
                break
    if rmTagObject:
        postJsonObject['object']['tag'].remove(rmTagObject)


def _newswireHashtagProcessing(session, base_dir: str, postJsonObject: {},
                               hashtags: [], http_prefix: str,
                               domain: str, port: int,
                               personCache: {},
                               cachedWebfingers: {},
                               federationList: [],
                               sendThreads: [], postLog: [],
                               moderated: bool, url: str,
                               systemLanguage: str,
                               translate: {}) -> bool:
    """Applies hashtag rules to a news post.
    Returns true if the post should be saved to the news timeline
    of this instance
    """
    rulesFilename = base_dir + '/accounts/hashtagrules.txt'
    if not os.path.isfile(rulesFilename):
        return True
    rules = []
    with open(rulesFilename, 'r') as f:
        rules = f.readlines()

    domainFull = getFullDomain(domain, port)

    # get the full text content of the post
    content = ''
    if postJsonObject['object'].get('content'):
        content += getBaseContentFromPost(postJsonObject, systemLanguage)
    if postJsonObject['object'].get('summary'):
        content += ' ' + postJsonObject['object']['summary']
    content = content.lower()

    # actionOccurred = False
    operators = ('not', 'and', 'or', 'xor', 'from', 'contains')
    for ruleStr in rules:
        if not ruleStr:
            continue
        if not ruleStr.startswith('if '):
            continue
        if ' then ' not in ruleStr:
            continue
        conditionsStr = ruleStr.split('if ', 1)[1]
        conditionsStr = conditionsStr.split(' then ')[0]
        tagsInConditions = []
        tree = hashtagRuleTree(operators, conditionsStr,
                               tagsInConditions, moderated)
        if not hashtagRuleResolve(tree, hashtags, moderated, content, url):
            continue
        # the condition matches, so do something
        actionStr = ruleStr.split(' then ')[1].strip()

        if actionStr.startswith('add '):
            # add a hashtag
            _hashtagAdd(base_dir, http_prefix, domainFull,
                        postJsonObject, actionStr, hashtags, systemLanguage,
                        translate)
        elif actionStr.startswith('remove '):
            # remove a hashtag
            _hashtagRemove(http_prefix, domainFull, postJsonObject,
                           actionStr, hashtags, systemLanguage)
        elif actionStr.startswith('block') or actionStr.startswith('drop'):
            # Block this item
            return False
    return True


def _createNewsMirror(base_dir: str, domain: str,
                      postIdNumber: str, url: str,
                      maxMirroredArticles: int) -> bool:
    """Creates a local mirror of a news article
    """
    if '|' in url or '>' in url:
        return True

    mirrorDir = base_dir + '/accounts/newsmirror'
    if not os.path.isdir(mirrorDir):
        os.mkdir(mirrorDir)

    # count the directories
    noOfDirs = 0
    for subdir, dirs, files in os.walk(mirrorDir):
        noOfDirs = len(dirs)

    mirrorIndexFilename = base_dir + '/accounts/newsmirror.txt'

    if maxMirroredArticles > 0 and noOfDirs > maxMirroredArticles:
        if not os.path.isfile(mirrorIndexFilename):
            # no index for mirrors found
            return True
        removals = []
        with open(mirrorIndexFilename, 'r') as indexFile:
            # remove the oldest directories
            ctr = 0
            while noOfDirs > maxMirroredArticles:
                ctr += 1
                if ctr > 5000:
                    # escape valve
                    break

                postId = indexFile.readline()
                if not postId:
                    continue
                postId = postId.strip()
                mirrorArticleDir = mirrorDir + '/' + postId
                if os.path.isdir(mirrorArticleDir):
                    rmtree(mirrorArticleDir, ignore_errors=False, onerror=None)
                    removals.append(postId)
                    noOfDirs -= 1

        # remove the corresponding index entries
        if removals:
            indexContent = ''
            with open(mirrorIndexFilename, 'r') as indexFile:
                indexContent = indexFile.read()
                for removePostId in removals:
                    indexContent = \
                        indexContent.replace(removePostId + '\n', '')
            try:
                with open(mirrorIndexFilename, 'w+') as indexFile:
                    indexFile.write(indexContent)
            except OSError:
                print('EX: unable to write ' + mirrorIndexFilename)

    mirrorArticleDir = mirrorDir + '/' + postIdNumber
    if os.path.isdir(mirrorArticleDir):
        # already mirrored
        return True

    # for onion instances mirror via tor
    prefixStr = ''
    if domain.endswith('.onion'):
        prefixStr = '/usr/bin/torsocks '

    # download the files
    commandStr = \
        prefixStr + '/usr/bin/wget -mkEpnp -e robots=off ' + url + \
        ' -P ' + mirrorArticleDir
    p = Popen(commandStr, shell=True)
    os.waitpid(p.pid, 0)

    if not os.path.isdir(mirrorArticleDir):
        print('WARN: failed to mirror ' + url)
        return True

    # append the post Id number to the index file
    if os.path.isfile(mirrorIndexFilename):
        try:
            with open(mirrorIndexFilename, 'a+') as indexFile:
                indexFile.write(postIdNumber + '\n')
        except OSError:
            print('EX: unable to append ' + mirrorIndexFilename)
    else:
        try:
            with open(mirrorIndexFilename, 'w+') as indexFile:
                indexFile.write(postIdNumber + '\n')
        except OSError:
            print('EX: unable to write ' + mirrorIndexFilename)

    return True


def _convertRSStoActivityPub(base_dir: str, http_prefix: str,
                             domain: str, port: int,
                             newswire: {},
                             translate: {},
                             recentPostsCache: {}, maxRecentPosts: int,
                             session, cachedWebfingers: {},
                             personCache: {},
                             federationList: [],
                             sendThreads: [], postLog: [],
                             maxMirroredArticles: int,
                             allow_local_network_access: bool,
                             systemLanguage: str,
                             low_bandwidth: bool,
                             content_license_url: str) -> None:
    """Converts rss items in a newswire into posts
    """
    if not newswire:
        print('No newswire to convert')
        return

    basePath = base_dir + '/accounts/news@' + domain + '/outbox'
    if not os.path.isdir(basePath):
        os.mkdir(basePath)

    # oldest items first
    newswireReverse = OrderedDict(sorted(newswire.items(), reverse=False))

    for dateStr, item in newswireReverse.items():
        originalDateStr = dateStr
        # convert the date to the format used by ActivityPub
        if '+00:00' in dateStr:
            dateStr = dateStr.replace(' ', 'T')
            dateStr = dateStr.replace('+00:00', 'Z')
        else:
            try:
                dateStrWithOffset = \
                    datetime.datetime.strptime(dateStr, "%Y-%m-%d %H:%M:%S%z")
            except BaseException:
                print('EX: Newswire strptime failed ' + str(dateStr))
                continue
            try:
                dateStr = dateStrWithOffset.strftime("%Y-%m-%dT%H:%M:%SZ")
            except BaseException:
                print('EX: Newswire dateStrWithOffset failed ' +
                      str(dateStrWithOffset))
                continue

        statusNumber, published = getStatusNumber(dateStr)
        newPostId = \
            localActorUrl(http_prefix, 'news', domain) + \
            '/statuses/' + statusNumber

        # file where the post is stored
        filename = basePath + '/' + newPostId.replace('/', '#') + '.json'
        if os.path.isfile(filename):
            # don't create the post if it already exists
            # set the url
            # newswire[originalDateStr][1] = \
            #     '/users/news/statuses/' + statusNumber
            # set the filename
            newswire[originalDateStr][3] = filename
            continue

        rssTitle = _removeControlCharacters(item[0])
        url = item[1]
        if dangerousMarkup(url, allow_local_network_access) or \
           dangerousMarkup(rssTitle, allow_local_network_access):
            continue
        rssDescription = ''

        # get the rss description if it exists
        rssDescription = '<p>' + removeHtml(item[4]) + '<p>'

        mirrored = item[7]
        postUrl = url
        if mirrored and '://' in url:
            postUrl = '/newsmirror/' + statusNumber + '/' + \
                url.split('://')[1]
            if postUrl.endswith('/'):
                postUrl += 'index.html'
            else:
                postUrl += '/index.html'

        # add the off-site link to the description
        rssDescription += \
            '<br><a href="' + postUrl + '">' + \
            translate['Read more...'] + '</a>'

        followersOnly = False
        # NOTE: the id when the post is created will not be
        # consistent (it's based on the current time, not the
        # published time), so we change that later
        saveToFile = False
        attachImageFilename = None
        mediaType = None
        imageDescription = None
        city = 'London, England'
        conversationId = None
        blog = createNewsPost(base_dir,
                              domain, port, http_prefix,
                              rssDescription,
                              followersOnly, saveToFile,
                              attachImageFilename, mediaType,
                              imageDescription, city,
                              rssTitle, systemLanguage,
                              conversationId, low_bandwidth,
                              content_license_url)
        if not blog:
            continue

        if mirrored:
            if not _createNewsMirror(base_dir, domain, statusNumber,
                                     url, maxMirroredArticles):
                continue

        idStr = \
            localActorUrl(http_prefix, 'news', domain) + \
            '/statuses/' + statusNumber + '/replies'
        blog['news'] = True

        # note the time of arrival
        currTime = datetime.datetime.utcnow()
        blog['object']['arrived'] = currTime.strftime("%Y-%m-%dT%H:%M:%SZ")

        # change the id, based upon the published time
        blog['object']['replies']['id'] = idStr
        blog['object']['replies']['first']['partOf'] = idStr

        blog['id'] = newPostId + '/activity'
        blog['object']['id'] = newPostId
        blog['object']['atomUri'] = newPostId
        blog['object']['url'] = \
            http_prefix + '://' + domain + '/@news/' + statusNumber
        blog['object']['published'] = dateStr

        blog['object']['content'] = rssDescription
        blog['object']['contentMap'][systemLanguage] = rssDescription

        domainFull = getFullDomain(domain, port)

        hashtags = item[6]

        postId = newPostId.replace('/', '#')

        moderated = item[5]

        savePost = _newswireHashtagProcessing(session, base_dir,
                                              blog, hashtags,
                                              http_prefix, domain, port,
                                              personCache, cachedWebfingers,
                                              federationList,
                                              sendThreads, postLog,
                                              moderated, url, systemLanguage,
                                              translate)

        # save the post and update the index
        if savePost:
            # ensure that all hashtags are stored in the json
            # and appended to the content
            blog['object']['tag'] = []
            for tagName in hashtags:
                htId = tagName.replace('#', '')
                hashtagUrl = \
                    http_prefix + "://" + domainFull + "/tags/" + htId
                newTag = {
                    'href': hashtagUrl,
                    'name': tagName,
                    'type': 'Hashtag'
                }
                blog['object']['tag'].append(newTag)
                hashtagHtml = \
                    " <a href=\"" + hashtagUrl + \
                    "\" class=\"addedHashtag\" " + \
                    "rel=\"tag\">#<span>" + \
                    htId + "</span></a>"
                content = getBaseContentFromPost(blog, systemLanguage)
                if hashtagHtml not in content:
                    if content.endswith('</p>'):
                        content = \
                            content[:len(content) - len('</p>')] + \
                            hashtagHtml + '</p>'
                    else:
                        content += hashtagHtml
                    blog['object']['content'] = content
                    blog['object']['contentMap'][systemLanguage] = content

            # update the newswire tags if new ones have been found by
            # _newswireHashtagProcessing
            for tag in hashtags:
                if tag not in newswire[originalDateStr][6]:
                    newswire[originalDateStr][6].append(tag)

            storeHashTags(base_dir, 'news', domain,
                          http_prefix, domainFull,
                          blog, translate)

            clearFromPostCaches(base_dir, recentPostsCache, postId)
            if saveJson(blog, filename):
                _updateFeedsOutboxIndex(base_dir, domain, postId + '.json')

                # Save a file containing the time when the post arrived
                # this can then later be used to construct the news timeline
                # excluding items during the voting period
                if moderated:
                    _saveArrivedTime(base_dir, filename,
                                     blog['object']['arrived'])
                else:
                    if os.path.isfile(filename + '.arrived'):
                        try:
                            os.remove(filename + '.arrived')
                        except OSError:
                            print('EX: _convertRSStoActivityPub ' +
                                  'unable to delete ' + filename + '.arrived')

                # setting the url here links to the activitypub object
                # stored locally
                # newswire[originalDateStr][1] = \
                #     '/users/news/statuses/' + statusNumber

                # set the filename
                newswire[originalDateStr][3] = filename


def _mergeWithPreviousNewswire(oldNewswire: {}, newNewswire: {}) -> None:
    """Preserve any votes or generated activitypub post filename
    as rss feeds are updated
    """
    if not oldNewswire:
        return

    for published, fields in oldNewswire.items():
        if not newNewswire.get(published):
            continue
        for i in range(1, 5):
            newNewswire[published][i] = fields[i]


def runNewswireDaemon(base_dir: str, httpd,
                      http_prefix: str, domain: str, port: int,
                      translate: {}) -> None:
    """Periodically updates RSS feeds
    """
    newswireStateFilename = base_dir + '/accounts/.newswirestate.json'
    refreshFilename = base_dir + '/accounts/.refresh_newswire'

    # initial sleep to allow the system to start up
    time.sleep(50)
    while True:
        # has the session been created yet?
        if not httpd.session:
            print('Newswire daemon waiting for session')
            httpd.session = createSession(httpd.proxyType)
            if not httpd.session:
                print('Newswire daemon has no session')
                time.sleep(60)
                continue
            else:
                print('Newswire daemon session established')

        # try to update the feeds
        print('Updating newswire feeds')
        newNewswire = \
            getDictFromNewswire(httpd.session, base_dir, domain,
                                httpd.max_newswire_postsPerSource,
                                httpd.maxNewswireFeedSizeKb,
                                httpd.maxTags,
                                httpd.max_feed_item_size_kb,
                                httpd.max_newswire_posts,
                                httpd.maxCategoriesFeedItemSizeKb,
                                httpd.systemLanguage,
                                httpd.debug)

        if not httpd.newswire:
            print('Newswire feeds not updated')
            if os.path.isfile(newswireStateFilename):
                print('Loading newswire from file')
                httpd.newswire = loadJson(newswireStateFilename)

        print('Merging with previous newswire')
        _mergeWithPreviousNewswire(httpd.newswire, newNewswire)

        httpd.newswire = newNewswire
        if newNewswire:
            saveJson(httpd.newswire, newswireStateFilename)
            print('Newswire updated')
        else:
            print('No new newswire')

        print('Converting newswire to activitypub format')
        _convertRSStoActivityPub(base_dir,
                                 http_prefix, domain, port,
                                 newNewswire, translate,
                                 httpd.recentPostsCache,
                                 httpd.maxRecentPosts,
                                 httpd.session,
                                 httpd.cachedWebfingers,
                                 httpd.personCache,
                                 httpd.federationList,
                                 httpd.sendThreads,
                                 httpd.postLog,
                                 httpd.maxMirroredArticles,
                                 httpd.allow_local_network_access,
                                 httpd.systemLanguage,
                                 httpd.low_bandwidth,
                                 httpd.content_license_url)
        print('Newswire feed converted to ActivityPub')

        if httpd.maxNewsPosts > 0:
            archiveDir = base_dir + '/archive'
            archiveSubdir = \
                archiveDir + '/accounts/news@' + domain + '/outbox'
            print('Archiving news posts')
            archivePostsForPerson(http_prefix, 'news',
                                  domain, base_dir, 'outbox',
                                  archiveSubdir,
                                  httpd.recentPostsCache,
                                  httpd.maxNewsPosts)

        # wait a while before the next feeds update
        for tick in range(120):
            time.sleep(10)
            # if a new blog post has been created then stop
            # waiting and recalculate the newswire
            if os.path.isfile(refreshFilename):
                try:
                    os.remove(refreshFilename)
                except OSError:
                    print('EX: runNewswireDaemon unable to delete ' +
                          str(refreshFilename))
                break


def runNewswireWatchdog(projectVersion: str, httpd) -> None:
    """This tries to keep the newswire update thread running even if it dies
    """
    print('Starting newswire watchdog')
    newswireOriginal = \
        httpd.thrPostSchedule.clone(runNewswireDaemon)
    httpd.thrNewswireDaemon.start()
    while True:
        time.sleep(50)
        if httpd.thrNewswireDaemon.is_alive():
            continue
        httpd.thrNewswireDaemon.kill()
        httpd.thrNewswireDaemon = \
            newswireOriginal.clone(runNewswireDaemon)
        httpd.thrNewswireDaemon.start()
        print('Restarting newswire daemon...')
