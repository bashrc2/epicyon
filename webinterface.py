__filename__ = "webinterface.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import json
from pprint import pprint
from person import personBoxJson
from utils import getNicknameFromActor
from utils import getDomainFromActor
from posts import getPersonBox

def htmlHeader(css=None,lang='en') -> str:
    if not css:        
        htmlStr= \
            '<!DOCTYPE html>\n' \
            '<html lang="'+lang+'">\n' \
            '  <meta charset="utf-8">\n' \
            '  <style>\n' \
            '    @import url("epicyon.css");\n'+ \
            '  </style>\n' \
            '  <body>\n'
    else:
        htmlStr= \
            '<!DOCTYPE html>\n' \
            '<html lang="'+lang+'">\n' \
            '  <meta charset="utf-8">\n' \
            '  <style>\n'+css+'</style>\n' \
            '  <body>\n'        
    return htmlStr

def htmlFooter() -> str:
    htmlStr= \
        '  </body>\n' \
        '</html>\n'
    return htmlStr

def htmlProfilePosts(baseDir: str,httpPrefix: str, \
                     authorized: bool,ocapAlways: bool, \
                     nickname: str,domain: str,port: int, \
                     session,wfRequest: {},personCache: {}) -> str:
    """Shows posts on the profile screen
    """
    profileStr=''
    outboxFeed= \
        personBoxJson(baseDir,domain, \
                      port,'/users/'+nickname+'/outbox?page=1', \
                      httpPrefix, \
                      4, 'outbox', \
                      authorized, \
                      ocapAlways)
    for item in outboxFeed['orderedItems']:
        if item['type']=='Create':
            profileStr+= \
                individualPostAsHtml(session,wfRequest,personCache, \
                                     domain,item)
    return profileStr

def htmlProfileFollowing(baseDir: str,httpPrefix: str, \
                         authorized: bool,ocapAlways: bool, \
                         nickname: str,domain: str,port: int, \
                         session,wfRequest: {},personCache: {}, \
                         followingJson: {}) -> str:
    """Shows following on the profile screen
    """
    profileStr=''
    for item in followingJson['orderedItems']:
        profileStr+=individualFollowAsHtml(session,wfRequest,personCache,domain,item)
    return profileStr

def htmlProfileRoles(nickname: str,domain: str,rolesJson: {}) -> str:
    """Shows roles on the profile screen
    """
    profileStr=''
    for project,rolesList in rolesJson.items():
        profileStr+='<div class="roles"><h2>'+project+'</h2><div class="roles-inner">'
        for role in rolesList:
            profileStr+='<h3>'+role+'</h3>'
        profileStr+='</div></div>'
    if len(profileStr)==0:
        profileStr+='<p>@'+nickname+'@'+domain+' has no roles assigned</p>'
    else:
        profileStr='<div>'+profileStr+'</div>'
    return profileStr

def htmlProfile(baseDir: str,httpPrefix: str,authorized: bool, \
                ocapAlways: bool,profileJson: {},selected: str, \
                session,wfRequest: {},personCache: {}, \
                extraJson=None) -> str:
    """Show the profile page as html
    """
    nickname=profileJson['name']
    if not nickname:
        return ""
    preferredName=profileJson['preferredUsername']
    domain,port=getDomainFromActor(profileJson['id'])
    if not domain:
        return ""
    domainFull=domain
    if port:
        domainFull=domain+':'+str(port)
    profileDescription=profileJson['publicKey']['summary']
    profileDescription='A test description'
    postsButton='button'
    followingButton='button'
    followersButton='button'
    rolesButton='button'
    skillsButton='button'
    sharesButton='button'
    if selected=='posts':
        postsButton='buttonselected'
    elif selected=='following':
        followingButton='buttonselected'
    elif selected=='followers':
        followersButton='buttonselected'
    elif selected=='roles':
        rolesButton='buttonselected'
    elif selected=='skills':
        skillsButton='buttonselected'
    elif selected=='shares':
        sharesButton='buttonselected'
    actor=profileJson['id']
    profileStr= \
        ' <div class="hero-image">' \
        '  <div class="hero-text">' \
        '    <img src="'+profileJson['icon']['url']+'" alt="'+nickname+'@'+domainFull+'">' \
        '    <h1>'+preferredName+'</h1>' \
        '    <p><b>@'+nickname+'@'+domainFull+'</b></p>' \
        '    <p>'+profileDescription+'</p>' \
        '  </div>' \
        '</div>' \
        '<div class="container">\n' \
        '  <center>' \
        '    <a href="'+actor+'"><button class="'+postsButton+'"><span>Posts </span></button></a>' \
        '    <a href="'+actor+'/following"><button class="'+followingButton+'"><span>Following </span></button></a>' \
        '    <a href="'+actor+'/followers"><button class="'+followersButton+'"><span>Followers </span></button></a>' \
        '    <a href="'+actor+'/roles"><button class="'+rolesButton+'"><span>Roles </span></button></a>' \
        '    <a href="'+actor+'/skills"><button class="'+skillsButton+'"><span>Skills </span></button></a>' \
        '    <a href="'+actor+'/shares"><button class="'+sharesButton+'"><span>Shares </span></button></a>' \
        '  </center>' \
        '</div>'

    profileStyle= \
        'body, html {' \
        '  height: 100%;' \
        '  margin: 0;' \
        '  font-family: Arial, Helvetica, sans-serif;' \
        '}' \
        '' \
        '.hero-image {' \
        '  background-image: linear-gradient(rgba(0, 0, 0, 0.5), rgba(0, 0, 0, 0.5)), url("'+actor+'/image.png");' \
        '  height: 50%;' \
        '  background-position: center;' \
        '  background-repeat: no-repeat;' \
        '  background-size: cover;' \
        '  position: relative;' \
        '}' \
        '' \
        '.hero-text {' \
        '  text-align: center;' \
        '  position: absolute;' \
        '  top: 50%;' \
        '  left: 50%;' \
        '  transform: translate(-50%, -50%);' \
        '  color: white;' \
        '}' \
        '' \
        '.roles {' \
        '  text-align: center;' \
        '  left: 35%;' \
        '  background-color: #f1f1f1;' \
        '}' \
        '.roles-inner {' \
        '  padding: 10px 25px;' \
        '  background-color: #ffffff;' \
        '}' \
        '' \
        '.hero-text img {' \
        '  border-radius: 10%;' \
        '  width: 50%;' \
        '}' \
        '' \
        '.hero-text button {' \
        '  border: none;' \
        '  outline: 0;' \
        '  display: inline-block;' \
        '  padding: 10px 25px;' \
        '  color: black;' \
        '  background-color: #ddd;' \
        '  text-align: center;' \
        '  cursor: pointer;' \
        '}' \
        '' \
        '.hero-text button:hover {' \
        '  background-color: #555;' \
        '  color: white;' \
        '}' \
        '' \
        '.button {' \
        '  border-radius: 4px;' \
        '  background-color: #999;' \
        '  border: none;' \
        '  color: #FFFFFF;' \
        '  text-align: center;' \
        '  font-size: 18px;' \
        '  padding: 10px;' \
        '  width: 20%;' \
        '  max-width: 200px;' \
        '  min-width: 100px;' \
        '  transition: all 0.5s;' \
        '  cursor: pointer;' \
        '  margin: 5px;' \
        '}' \
        '' \
        '.button span {' \
        '  cursor: pointer;' \
        '  display: inline-block;' \
        '  position: relative;' \
        '  transition: 0.5s;' \
        '}' \
        '' \
        '.button span:after {' \
        "  content: '\\00bb';" \
        '  position: absolute;' \
        '  opacity: 0;' \
        '  top: 0;' \
        '  right: -20px;' \
        '  transition: 0.5s;' \
        '}' \
        '' \
        '.button:hover span {' \
        '  padding-right: 25px;' \
        '}' \
        '' \
        '.button:hover span:after {' \
        '  opacity: 1;' \
        '  right: 0;' \
        '}' \
        '.buttonselected {' \
        '  border-radius: 4px;' \
        '  background-color: #666;' \
        '  border: none;' \
        '  color: #FFFFFF;' \
        '  text-align: center;' \
        '  font-size: 18px;' \
        '  padding: 10px;' \
        '  width: 20%;' \
        '  max-width: 200px;' \
        '  min-width: 100px;' \
        '  transition: all 0.5s;' \
        '  cursor: pointer;' \
        '  margin: 5px;' \
        '}' \
        '' \
        '.buttonselected span {' \
        '  cursor: pointer;' \
        '  display: inline-block;' \
        '  position: relative;' \
        '  transition: 0.5s;' \
        '}' \
        '' \
        '.buttonselected span:after {' \
        "  content: '\\00bb';" \
        '  position: absolute;' \
        '  opacity: 0;' \
        '  top: 0;' \
        '  right: -20px;' \
        '  transition: 0.5s;' \
        '}' \
        '' \
        '.buttonselected:hover span {' \
        '  padding-right: 25px;' \
        '}' \
        '' \
        '.buttonselected:hover span:after {' \
        '  opacity: 1;' \
        '  right: 0;' \
        '}' \
        '.container {' \
        '    border: 2px solid #dedede;' \
        '    background-color: #f1f1f1;' \
        '    border-radius: 5px;' \
        '    padding: 10px;' \
        '    margin: 10px 0;' \
        '}' \
        '' \
        '.container {' \
        '    border: 2px solid #dedede;' \
        '    background-color: #f1f1f1;' \
        '    border-radius: 5px;' \
        '    padding: 10px;' \
        '    margin: 10px 0;' \
        '}' \
        '' \
        '.darker {' \
        '    border-color: #ccc;' \
        '    background-color: #ddd;' \
        '}' \
        '' \
        '.container::after {' \
        '    content: "";' \
        '    clear: both;' \
        '    display: table;' \
        '}' \
        '' \
        '.container img {' \
        '    float: left;' \
        '    max-width: 60px;' \
        '    width: 100%;' \
        '    margin-right: 20px;' \
        '    border-radius: 10%;' \
        '}' \
        '' \
        '.container img.attachment {' \
        '    max-width: 100%;' \
        '    margin-left: 25%;' \
        '    width: 50%;' \
        '    border-radius: 10%;' \
        '}' \
        '.container img.right {' \
        '    float: right;' \
        '    margin-left: 20px;' \
        '    margin-right:0;' \
        '}' \
        '' \
        '.time-right {' \
        '    float: right;' \
        '    color: #aaa;' \
        '}' \
        '' \
        '.time-left {' \
        '    float: left;' \
        '    color: #999;' \
        '}' \
        '' \
        '.post-title {' \
        '    margin-top: 0px;' \
        '    color: #999;' \
        '}'

    if selected=='posts':
        profileStr+= \
            htmlProfilePosts(baseDir,httpPrefix,authorized, \
                             ocapAlways,nickname,domain,port, \
                             session,wfRequest,personCache)
    if selected=='following' or selected=='followers':
        profileStr+= \
            htmlProfileFollowing(baseDir,httpPrefix, \
                                 authorized,ocapAlways,nickname, \
                                 domain,port,session, \
                                 wfRequest,personCache,extraJson)
    if selected=='roles':
        profileStr+= \
            htmlProfileRoles(nickname,domainFull,extraJson)
    profileStr=htmlHeader(profileStyle)+profileStr+htmlFooter()
    return profileStr

def individualFollowAsHtml(session,wfRequest: {}, \
                           personCache: {},domain: str, \
                           followUrl: str) -> str:
    nickname=getNicknameFromActor(followUrl)
    domain,port=getDomainFromActor(followUrl)
    titleStr='@'+nickname+'@'+domain
    avatarUrl=followUrl+'/avatar.png'
    if domain not in followUrl:
        inboxUrl,pubKeyId,pubKey,fromPersonId,sharedInbox,capabilityAcquisition,avatarUrl2,preferredName = \
            getPersonBox(session,wfRequest,personCache,'outbox')
        if avatarUrl2:
            avatarUrl=avatarUrl2
        if preferredName:
            titleStr=preferredName+' '+titleStr
    return \
        '<div class="container">\n' \
        '<a href="'+followUrl+'">' \
        '<img src="'+avatarUrl+'" alt="Avatar">\n'+ \
        '<p>'+titleStr+'</p></a>'+ \
        '</div>\n'

def individualPostAsHtml(session,wfRequest: {},personCache: {}, \
                         domain: str,postJsonObject: {}) -> str:
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

    avatarUrl=postJsonObject['actor']+'/avatar.png'
    if domain not in postJsonObject['actor']:
        inboxUrl,pubKeyId,pubKey,fromPersonId,sharedInbox,capabilityAcquisition,avatarUrl2,preferredName = \
            getPersonBox(session,wfRequest,personCache,'outbox')
        if avatarUrl2:
            avatarUrl=avatarUrl2
        if preferredName:
            titleStr=preferredName+' '+titleStr

    return \
        '<div class="'+containerClass+'">\n' \
        '<a href="'+postJsonObject['actor']+'">' \
        '<img src="'+avatarUrl+'" alt="Avatar"'+avatarPosition+'></a>\n'+ \
        '<p class="post-title">'+titleStr+'</p>'+ \
        postJsonObject['object']['content']+'\n'+ \
        attachmentStr+ \
        '<span class="'+timeClass+'">'+postJsonObject['object']['published']+'</span>\n'+ \
        '</div>\n'

def htmlTimeline(session,wfRequest: {},personCache: {}, \
                 domain: str,timelineJson: {}) -> str:
    """Show the timeline as html
    """
    if not timelineJson.get('orderedItems'):
        return ""
    tlStr=htmlHeader()
    for item in timelineJson['orderedItems']:
        if item['type']=='Create':
            tlStr+=individualPostAsHtml(session,wfRequest,personCache, \
                                        domain,item)
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

def htmlIndividualPost(session,wfRequest: {},personCache: {}, \
                       domain: str,postJsonObject: {}) -> str:
    """Show an individual post as html
    """
    return htmlHeader()+ \
        individualPostAsHtml(session,wfRequest,personCache, \
                             domain,postJsonObject)+ \
        htmlFooter()

def htmlPostReplies(postJsonObject: {}) -> str:
    """Show the replies to an individual post as html
    """
    return htmlHeader()+"<h1>Replies</h1>"+htmlFooter()
