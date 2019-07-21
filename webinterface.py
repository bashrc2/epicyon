__filename__ = "webinterface.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import json
from utils import getNicknameFromActor
from utils import getDomainFromActor

def htmlHeader(lang='en') -> str:
    htmlStr= \
        '<!DOCTYPE html>\n' \
        '<html lang="'+lang+'">\n' \
        '  <meta charset="utf-8">\n' \
        '  <style>\n' \
        '    @import url("epicyon.css");\n' \
        '  </style>\n' \
        '  <body>\n'
    return htmlStr

def htmlFooter() -> str:
    htmlStr= \
        '  </body>\n' \
        '</html>\n'
    return htmlStr

def htmlProfile(profileJson: {}) -> str:
    """Show the profile page as html
    """
    return htmlHeader()+"<h1>Profile page</h1>"+htmlFooter()

def htmlFollowing(followingJson: {}) -> str:
    """Show the following collection as html
    """
    return htmlHeader()+"<h1>Following collection</h1>"+htmlFooter()

def htmlFollowers(followersJson: {}) -> str:
    """Show the followers collection as html
    """
    return htmlHeader()+"<h1>Followers collection</h1>"+htmlFooter()

def individualPostAsHtml(postJsonObject: {}) -> str:
    avatarPosition=''
    containerClass='container'
    timeClass='time-right'
    nickname=getNicknameFromActor(postJsonObject['actor'])
    domain,port=getDomainFromActor(postJsonObject['actor'])
    titleStr='@'+nickname+'@'+domain
    if postJsonObject['object']['inReplyTo']:
        containerClass='container darker'
        avatarPosition=' class="right"'
        timeClass='time-left'
        if '/statuses/' in postJsonObject['object']['inReplyTo']:
            replyNickname=getNicknameFromActor(postJsonObject['object']['inReplyTo'])
            replyDomain,replyPort=getDomainFromActor(postJsonObject['object']['inReplyTo'])
            if replyNickname and replyDomain:
                titleStr+=' <i>replying to</i> <a href="'+postJsonObject['object']['inReplyTo']+'">@'+replyNickname+'@'+replyDomain+'</a>'
        else:
            titleStr+=' <i>replying to</i> '+postJsonObject['object']['inReplyTo']
    attachmentStr=''
    if postJsonObject['object']['attachment']:
        if isinstance(postJsonObject['object']['attachment'], list):
            attachmentCtr=0
            for attach in postJsonObject['object']['attachment']:
                if attach.get('mediaType') and attach.get('url'):
                    mediaType=attach['mediaType']
                    imageDescription=''
                    if attach.get('name'):
                        imageDescription=attach['name']
                    if mediaType=='image/png' or \
                       mediaType=='image/jpeg' or \
                       mediaType=='image/gif':
                        if attach['url'].endswith('.png') or \
                           attach['url'].endswith('.jpg') or \
                           attach['url'].endswith('.jpeg') or \
                           attach['url'].endswith('.gif'):
                            if attachmentCtr>0:
                                attachmentStr+='<br>'
                            attachmentStr+= \
                                '<a href="'+attach['url']+'">' \
                                '<img src="'+attach['url']+'" alt="'+imageDescription+'" title="'+imageDescription+'" class="attachment"></a>\n'
                            attachmentCtr+=1
    
    return \
        '<div class="'+containerClass+'">\n' \
        '<a href="'+postJsonObject['actor']+'">' \
        '<img src="'+postJsonObject['actor']+'/avatar.png" alt="Avatar"'+avatarPosition+'></a>\n'+ \
        '<p class="post-title">'+titleStr+'</p>'+ \
        postJsonObject['object']['content']+'\n'+ \
        attachmentStr+ \
        '<span class="'+timeClass+'">'+postJsonObject['object']['published']+'</span>\n'+ \
        '</div>\n'

def htmlTimeline(timelineJson: {}) -> str:
    """Show the timeline as html
    """
    if not timelineJson.get('orderedItems'):
        return ""
    tlStr=htmlHeader()
    for item in timelineJson['orderedItems']:
        if item['type']=='Create':
            tlStr+=individualPostAsHtml(item)
    tlStr+=htmlFooter()
    return tlStr

def htmlInbox(inboxJson: {}) -> str:
    """Show the inbox as html
    """
    return htmlTimeline(inboxJson)

def htmlOutbox(outboxJson: {}) -> str:
    """Show the Outbox as html
    """
    return htmlTimeline(outboxJson)

def htmlIndividualPost(postJsonObject: {}) -> str:
    """Show an individual post as html
    """
    return htmlHeader()+ \
        individualPostAsHtml(postJsonObject)+ \
        htmlFooter()

def htmlPostReplies(postJsonObject: {}) -> str:
    """Show the replies to an individual post as html
    """
    return htmlHeader()+"<h1>Replies</h1>"+htmlFooter()
