__filename__ = "newsdaemon.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
import time
import datetime
from collections import OrderedDict
from newswire import getDictFromNewswire
# from posts import sendSignedJson
from posts import createNewsPost
from content import removeHtmlTag
from content import dangerousMarkup
from content import validHashTag
from utils import loadJson
from utils import saveJson
from utils import getStatusNumber


def updateFeedsOutboxIndex(baseDir: str, domain: str, postId: str) -> None:
    """Updates the index used for imported RSS feeds
    """
    basePath = baseDir + '/accounts/news@' + domain
    indexFilename = basePath + '/outbox.index'

    if os.path.isfile(indexFilename):
        if postId not in open(indexFilename).read():
            try:
                with open(indexFilename, 'r+') as feedsFile:
                    content = feedsFile.read()
                    feedsFile.seek(0, 0)
                    feedsFile.write(postId + '\n' + content)
                    print('DEBUG: feeds post added to index')
            except Exception as e:
                print('WARN: Failed to write entry to feeds posts index ' +
                      indexFilename + ' ' + str(e))
    else:
        feedsFile = open(indexFilename, 'w+')
        if feedsFile:
            feedsFile.write(postId + '\n')
            feedsFile.close()


def saveArrivedTime(baseDir: str, postFilename: str, arrived: str) -> None:
    """Saves the time when an rss post arrived to a file
    """
    arrivedFile = open(postFilename + '.arrived', 'w+')
    if arrivedFile:
        arrivedFile.write(arrived)
        arrivedFile.close()


def removeControlCharacters(content: str) -> str:
    """TODO this is hacky and a better solution is needed
    the unicode is messing up somehow
    """
    lookups = {
        "8211": "-",
        "8230": "...",
        "8216": "'",
        "8217": "'",
        "8220": '"',
        "8221": '"'
    }
    for code, ch in lookups.items():
        content = content.replace('&' + code + ';', ch)
        content = content.replace('&#' + code + ';', ch)
    return content


def hasttagRuleResolve(tree: [], hashtags: []) -> bool:
    """Returns whether the tree for a hashtag rule evaluates to true or false
    """
    if not tree:
        return False

    if tree[0] == 'not':
        if len(tree) == 2:
            if isinstance(tree[1], str):
                return tree[1] not in hashtags
            elif isinstance(tree[1], list):
                return not hasttagRuleResolve(tree[1], hashtags)
    elif tree[0] == 'and':
        if len(tree) == 3:

            firstArg = False
            if isinstance(tree[1], str):
                firstArg = (tree[1] in hashtags)
            elif isinstance(tree[1], list):
                firstArg = (hasttagRuleResolve(tree[1], hashtags))

            secondArg = False
            if isinstance(tree[2], str):
                secondArg = (tree[2] in hashtags)
            elif isinstance(tree[2], list):
                secondArg = (hasttagRuleResolve(tree[2], hashtags))
            return firstArg and secondArg
    elif tree[0] == 'or':
        if len(tree) == 3:

            firstArg = False
            if isinstance(tree[1], str):
                firstArg = (tree[1] in hashtags)
            elif isinstance(tree[1], list):
                firstArg = (hasttagRuleResolve(tree[1], hashtags))

            secondArg = False
            if isinstance(tree[2], str):
                secondArg = (tree[2] in hashtags)
            elif isinstance(tree[2], list):
                secondArg = (hasttagRuleResolve(tree[2], hashtags))
            return firstArg or secondArg
    elif tree[0].startswith('#') and len(tree) == 1:
        return tree[0] in hashtags

    return False


def hashtagRuleTree(operators: [],
                    conditionsStr: str,
                    tagsInConditions: []) -> []:
    """Walks the tree
    """
    if not operators and conditionsStr:
        conditionsStr = conditionsStr.strip()
        if conditionsStr.startswith('#') or conditionsStr in operators:
            if conditionsStr.startswith('#'):
                if conditionsStr not in tagsInConditions:
                    if ' ' not in conditionsStr:
                        tagsInConditions.append(conditionsStr)
            return [conditionsStr.strip()]
        else:
            return None
    if not operators or not conditionsStr:
        return None
    tree = None
    conditionsStr = conditionsStr.strip()
    if conditionsStr.startswith('#') or conditionsStr in operators:
        if conditionsStr.startswith('#'):
            if conditionsStr not in tagsInConditions:
                if ' ' not in conditionsStr:
                    tagsInConditions.append(conditionsStr)
        tree = [conditionsStr.strip()]
    ctr = 0
    while ctr < len(operators):
        op = operators[ctr]
        if op not in conditionsStr:
            ctr += 1
            continue
        else:
            tree = [op]
            sections = conditionsStr.split(op)
            for subConditionStr in sections:
                result = hashtagRuleTree(operators[ctr + 1:], subConditionStr,
                                         tagsInConditions)
                if result:
                    tree.append(result)
            break
    return tree


def newswireHashtagProcessing(session, baseDir: str, postJsonObject: {},
                              hashtags: str, httpPrefix: str,
                              domain: str, port: int,
                              personCache: {},
                              cachedWebfingers: {},
                              federationList: [],
                              sendThreads: [], postLog: []) -> bool:
    """Applies hashtag rules to a news post.
    Returns true if the post should be saved to the news timeline
    of this instance
    """
    rulesFilename = baseDir + '/accounts/hashtagrules.txt'
    if not os.path.isfile(rulesFilename):
        return True
    rules = []
    with open(rulesFilename, "r") as f:
        rules = f.readlines()

    domainFull = domain
    if port:
        if port != 80 and port != 443:
            domainFull = domain + ':' + str(port)

    actionOccurred = False
    operators = ('not', 'and', 'or')
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
        tree = hashtagRuleTree(operators, conditionsStr, tagsInConditions)
        # does the rule contain any hashtags?
        if not tagsInConditions:
            continue
        if not hasttagRuleResolve(tree, hashtags):
            continue
        # the condition matches, so do something
        actionStr = ruleStr.split(' then ')[1].strip()

        # add a hashtag
        if actionStr.startswith('add '):
            addHashtag = actionStr.split('add ', 1)[1].strip()
            if addHashtag.startswith('#'):
                if addHashtag not in hashtags:
                    hashtags.append(addHashtag)
                    htId = addHashtag.replace('#', '')
                    if validHashTag(htId):
                        hashtagUrl = \
                            httpPrefix + "://" + domainFull + "/tags/" + htId
                        postJsonObject['object']['tag'][htId] = {
                            'href': hashtagUrl,
                            'name': addHashtag,
                            'type': 'Hashtag'
                        }
                        hashtagHtml = \
                            " <a href=\"" + hashtagUrl + \
                            "\" class=\"mention hashtag\" " + \
                            "rel=\"tag\">#<span>" + \
                            htId + "</span></a>"
                        content = postJsonObject['object']['content']
                        if content.endswith('</p>'):
                            content = \
                                content[:len(content) - len('</p>')] + \
                                hashtagHtml + '</p>'
                        else:
                            content += hashtagHtml
                        postJsonObject['object']['content'] = content
                        actionOccurred = True

        # remove a hashtag
        if actionStr.startswith('remove '):
            rmHashtag = actionStr.split('remove ', 1)[1].strip()
            if rmHashtag.startswith('#'):
                if rmHashtag in hashtags:
                    hashtags.remove(rmHashtag)
                    htId = addHashtag.replace('#', '')
                    hashtagUrl = \
                        httpPrefix + "://" + domainFull + "/tags/" + htId
                    hashtagHtml = \
                        "<a href=\"" + hashtagUrl + \
                        "\" class=\"mention hashtag\" " + \
                        "rel=\"tag\">#<span>" + \
                        htId + "</span></a>"
                    content = postJsonObject['object']['content']
                    if hashtagHtml in content:
                        content = \
                            content.replace(hashtagHtml, '').replace('  ', ' ')
                        postJsonObject['object']['content'] = content
                    del postJsonObject['object']['tag'][htId]
                    actionOccurred = True

    # TODO
    # If routing to another instance
    # sendSignedJson(postJsonObject: {}, session, baseDir: str,
    #                nickname: str, domain: str, port: int,
    #                toNickname: str, toDomain: str, toPort: int, cc: str,
    #                httpPrefix: str, False, False,
    #                federationList: [],
    #                sendThreads: [], postLog: [], cachedWebfingers: {},
    #                personCache: {}, False, __version__) -> int:
    if actionOccurred:
        return True
    return True


def convertRSStoActivityPub(baseDir: str, httpPrefix: str,
                            domain: str, port: int,
                            newswire: {},
                            translate: {},
                            recentPostsCache: {}, maxRecentPosts: int,
                            session, cachedWebfingers: {},
                            personCache: {},
                            federationList: [],
                            sendThreads: [], postLog: []) -> None:
    """Converts rss items in a newswire into posts
    """
    basePath = baseDir + '/accounts/news@' + domain + '/outbox'
    if not os.path.isdir(basePath):
        os.mkdir(basePath)

    # oldest items first
    newswireReverse = \
        OrderedDict(sorted(newswire.items(), reverse=False))

    for dateStr, item in newswireReverse.items():
        originalDateStr = dateStr
        # convert the date to the format used by ActivityPub
        dateStr = dateStr.replace(' ', 'T')
        dateStr = dateStr.replace('+00:00', 'Z')

        statusNumber, published = getStatusNumber(dateStr)
        newPostId = \
            httpPrefix + '://' + domain + \
            '/users/news/statuses/' + statusNumber

        # file where the post is stored
        filename = basePath + '/' + newPostId.replace('/', '#') + '.json'
        if os.path.isfile(filename):
            # don't create the post if it already exists
            # set the url
            newswire[originalDateStr][1] = \
                '/users/news/statuses/' + statusNumber
            # set the filename
            newswire[originalDateStr][3] = filename
            continue

        rssTitle = removeControlCharacters(item[0])
        url = item[1]
        if dangerousMarkup(url) or dangerousMarkup(rssTitle):
            continue
        rssDescription = ''

        # get the rss description if it exists
        rssDescription = removeControlCharacters(item[4])
        if rssDescription.startswith('<![CDATA['):
            rssDescription = rssDescription.replace('<![CDATA[', '')
            rssDescription = rssDescription.replace(']]>', '')
        rssDescription = '<p>' + rssDescription + '<p>'

        # add the off-site link to the description
        if rssDescription and not dangerousMarkup(rssDescription):
            rssDescription += \
                '<br><a href="' + url + '">' + \
                translate['Read more...'] + '</a>'
        else:
            rssDescription = \
                '<a href="' + url + '">' + \
                translate['Read more...'] + '</a>'

        # remove image dimensions
        if '<img' in rssDescription:
            rssDescription = removeHtmlTag(rssDescription, 'width')
            rssDescription = removeHtmlTag(rssDescription, 'height')

        followersOnly = False
        useBlurhash = False
        # NOTE: the id when the post is created will not be
        # consistent (it's based on the current time, not the
        # published time), so we change that later
        blog = createNewsPost(baseDir,
                              domain, port, httpPrefix,
                              rssDescription,
                              followersOnly, False,
                              None, None, None, useBlurhash,
                              rssTitle)
        if not blog:
            continue

        idStr = \
            httpPrefix + '://' + domain + '/users/news' + \
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
            httpPrefix + '://' + domain + '/@news/' + statusNumber
        blog['object']['published'] = dateStr

        postId = newPostId.replace('/', '#')

        moderated = item[5]

        hashtags = item[6]
        savePost = newswireHashtagProcessing(session, baseDir, blog, hashtags,
                                             httpPrefix, domain, port,
                                             personCache, cachedWebfingers,
                                             federationList,
                                             sendThreads, postLog)

        # save the post and update the index
        if savePost:
            newswire[originalDateStr][6] = hashtags
            if saveJson(blog, filename):
                updateFeedsOutboxIndex(baseDir, domain, postId + '.json')

                # Save a file containing the time when the post arrived
                # this can then later be used to construct the news timeline
                # excluding items during the voting period
                if moderated:
                    saveArrivedTime(baseDir, filename,
                                    blog['object']['arrived'])
                else:
                    if os.path.isfile(filename + '.arrived'):
                        os.remove(filename + '.arrived')

                # set the url
                newswire[originalDateStr][1] = \
                    '/users/news/statuses/' + statusNumber
                # set the filename
                newswire[originalDateStr][3] = filename


def mergeWithPreviousNewswire(oldNewswire: {}, newNewswire: {}) -> None:
    """Preserve any votes or generated activitypub post filename
    as rss feeds are updated
    """
    for published, fields in oldNewswire.items():
        if not newNewswire.get(published):
            continue
        for i in range(1, 5):
            newNewswire[published][i] = fields[i]


def runNewswireDaemon(baseDir: str, httpd,
                      httpPrefix: str, domain: str, port: int,
                      translate: {}) -> None:
    """Periodically updates RSS feeds
    """
    newswireStateFilename = baseDir + '/accounts/.newswirestate.json'

    # initial sleep to allow the system to start up
    time.sleep(50)
    while True:
        # has the session been created yet?
        if not httpd.session:
            print('Newswire daemon waiting for session')
            time.sleep(60)
            continue

        # try to update the feeds
        newNewswire = None
        try:
            newNewswire = \
                getDictFromNewswire(httpd.session, baseDir,
                                    httpd.maxNewswirePostsPerSource,
                                    httpd.maxNewswireFeedSizeKb)
        except Exception as e:
            print('WARN: unable to update newswire ' + str(e))
            time.sleep(120)
            continue

        if not httpd.newswire:
            if os.path.isfile(newswireStateFilename):
                httpd.newswire = loadJson(newswireStateFilename)

        mergeWithPreviousNewswire(httpd.newswire, newNewswire)

        httpd.newswire = newNewswire
        saveJson(httpd.newswire, newswireStateFilename)
        print('Newswire updated')

        convertRSStoActivityPub(baseDir,
                                httpPrefix, domain, port,
                                newNewswire, translate,
                                httpd.recentPostsCache,
                                httpd.maxRecentPosts,
                                httpd.session,
                                httpd.cachedWebfingers,
                                httpd.personCache,
                                httpd.federationList,
                                httpd.sendThreads,
                                httpd.postLog)
        print('Newswire feed converted to ActivityPub')

        # wait a while before the next feeds update
        time.sleep(1200)


def runNewswireWatchdog(projectVersion: str, httpd) -> None:
    """This tries to keep the newswire update thread running even if it dies
    """
    print('Starting newswire watchdog')
    newswireOriginal = \
        httpd.thrPostSchedule.clone(runNewswireDaemon)
    httpd.thrNewswireDaemon.start()
    while True:
        time.sleep(50)
        if not httpd.thrNewswireDaemon.isAlive():
            httpd.thrNewswireDaemon.kill()
            httpd.thrNewswireDaemon = \
                newswireOriginal.clone(runNewswireDaemon)
            httpd.thrNewswireDaemon.start()
            print('Restarting newswire daemon...')
