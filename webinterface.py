__filename__ = "webinterface.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import json
import time
import os
from datetime import datetime
from shutil import copyfile
from pprint import pprint
from person import personBoxJson
from utils import getNicknameFromActor
from utils import getDomainFromActor
from posts import getPersonBox
from follow import isFollowingActor
from webfinger import webfingerHandle
from posts import getUserUrl
from posts import parseUserFeed
from session import getJson
from auth import createPassword

def htmlGetLoginCredentials(loginParams: str,lastLoginTime: int) -> (str,str):
    """Receives login credentials via HTTPServer POST
    """
    if not loginParams.startswith('username='):
        return None,None
    # minimum time between login attempts
    currTime=int(time.time())
    if currTime<lastLoginTime+5:
        return None,None
    if '&' not in loginParams:
        return None,None
    loginArgs=loginParams.split('&')
    nickname=None
    password=None
    for arg in loginArgs:
        if '=' in arg:
            if arg.split('=',1)[0]=='username':
                nickname=arg.split('=',1)[1]
            elif arg.split('=',1)[0]=='password':
                password=arg.split('=',1)[1]
    return nickname,password

def htmlLogin(baseDir: str) -> str:
    if not os.path.isfile(baseDir+'/accounts/login.png'):
        copyfile(baseDir+'/img/login.png',baseDir+'/accounts/login.png')
    if os.path.isfile(baseDir+'/img/login-background.png'):
        if not os.path.isfile(baseDir+'/accounts/login-background.png'):
            copyfile(baseDir+'/img/login-background.png',baseDir+'/accounts/login-background.png')

    loginText='<p class="login-text">Welcome. Please enter your login details below.</p>'
    if os.path.isfile(baseDir+'/accounts/login.txt'):
        with open(baseDir+'/accounts/login.txt', 'r') as file:
            loginText = '<p class="login-text">'+file.read()+'</p>'    

    with open(baseDir+'/epicyon-login.css', 'r') as cssFile:
        loginCSS = cssFile.read()

    loginForm=htmlHeader(loginCSS)
    loginForm+= \
        '<form method="POST" action="/login">' \
        '  <div class="imgcontainer">' \
        '    <img src="login.png" alt="login image" class="loginimage">'+ \
        loginText+ \
        '  </div>' \
        '' \
        '  <div class="container">' \
        '    <label for="nickname"><b>Nickname</b></label>' \
        '    <input type="text" placeholder="Enter Nickname" name="username" required>' \
        '' \
        '    <label for="password"><b>Password</b></label>' \
        '    <input type="password" placeholder="Enter Password" name="password" required>' \
        '' \
        '    <button type="submit" name="submit">Login</button>' \
        '  </div>' \
        '</form>'
    loginForm+=htmlFooter()
    return loginForm

def htmlNewPost(baseDir: str,path: str,inReplyTo: str) -> str:
    replyStr=''
    if not path.endswith('/newshare'):
        if not inReplyTo:
            newPostText='<p class="new-post-text">Enter your post text below.</p>'
        else:
            newPostText='<p class="new-post-text">Enter your reply to <a href="'+inReplyTo+'">this post</a> below.</p>'
            replyStr='<input type="hidden" name="replyTo" value="'+inReplyTo+'">'
    else:
        newPostText='<p class="new-post-text">Enter the details for your shared item below.</p>'
        
    if os.path.isfile(baseDir+'/accounts/newpost.txt'):
        with open(baseDir+'/accounts/newpost.txt', 'r') as file:
            newPostText = '<p class="new-post-text">'+file.read()+'</p>'    

    with open(baseDir+'/epicyon-profile.css', 'r') as cssFile:
        newPostCSS = cssFile.read()

    pathBase=path.replace('/newpost','').replace('/newshare','').replace('/newunlisted','').replace('/newfollowers','').replace('/newdm','')

    scopeIcon='scope_public.png'
    scopeDescription='Public'
    placeholderSubject='Subject or Content Warning (optional)...'
    placeholderMessage='Write something...'
    extraFields=''
    endpoint='newpost'
    if path.endswith('/newunlisted'):
        scopeIcon='scope_unlisted.png'
        scopeDescription='Unlisted'
        endpoint='newunlisted'
    if path.endswith('/newfollowers'):
        scopeIcon='scope_followers.png'
        scopeDescription='Followers Only'
        endpoint='newfollowers'
    if path.endswith('/newdm'):
        scopeIcon='scope_dm.png'
        scopeDescription='Direct Message'
        endpoint='newdm'
    if path.endswith('/newshare'):
        scopeIcon='scope_share.png'
        scopeDescription='Shared Item'
        placeholderSubject='Name of the shared item...'
        placeholderMessage='Description of the item being shared...'
        endpoint='newshare'
        extraFields= \
            '<div class="container">' \
            '  <input type="text" class="itemType" placeholder="Type of shared item. eg. hat" name="itemType">' \
            '  <input type="text" class="category" placeholder="Category of shared item. eg. clothing" name="category">' \
            '  <label class="labels">Duration of listing in days:</label> <input type="number" name="duration" min="1" max="365" step="1" value="14">' \
            '</div>' \
            '<input type="text" placeholder="City or location of the shared item" name="location">'

    newPostForm=htmlHeader(newPostCSS)

    # only show the share option if this is not a reply
    shareOptionOnDropdown=''
    if not replyStr:
        shareOptionOnDropdown='<a href="'+pathBase+'/newshare"><img src="/icons/scope_share.png"/><b>Share</b><br>Describe a shared item</a>'
    newPostForm+= \
        '<form enctype="multipart/form-data" method="POST" action="'+path+'?'+endpoint+'">' \
        '  <div class="vertical-center">' \
        '    <label for="nickname"><b>'+newPostText+'</b></label>' \
        '    <div class="container">' \
        '      <div class="dropdown">' \
        '        <img src="/icons/'+scopeIcon+'"/><b class="scope-desc">'+scopeDescription+'</b>' \
        '        <div class="dropdown-content">' \
        '          <a href="'+pathBase+'/newpost"><img src="/icons/scope_public.png"/><b>Public</b><br>Visible to anyone</a>' \
        '          <a href="'+pathBase+'/newunlisted"><img src="/icons/scope_unlisted.png"/><b>Unlisted</b><br>Not on public timeline</a>' \
        '          <a href="'+pathBase+'/newfollowers"><img src="/icons/scope_followers.png"/><b>Followers Only</b><br>Only to followers</a>' \
        '          <a href="'+pathBase+'/newdm"><img src="/icons/scope_dm.png"/><b>Direct Message</b><br>Only to mentioned people</a>'+ \
        shareOptionOnDropdown+ \
        '        </div>' \
        '      </div>' \
        '      <input type="submit" name="submitPost" value="Submit">' \
        '      <a href="'+pathBase+'/outbox"><button class="cancelbtn">Cancel</button></a>' \
        '    </div>'+ \
        replyStr+ \
        '    <input type="text" placeholder="'+placeholderSubject+'" name="subject">' \
        '' \
        '    <textarea id="message" name="message" placeholder="'+placeholderMessage+'" style="height:200px"></textarea>' \
        ''+extraFields+ \
        '    <div class="container">' \
        '      <input type="text" placeholder="Image description" name="imageDescription">' \
        '      <input type="file" id="attachpic" name="attachpic"' \
        '            accept=".png, .jpg, .jpeg, .gif">' \
        '    </div>' \
        '  </div>' \
        '</form>'
    newPostForm+=htmlFooter()
    return newPostForm

def htmlHeader(css=None,lang='en') -> str:
    if not css:        
        htmlStr= \
            '<!DOCTYPE html>\n' \
            '<html lang="'+lang+'">\n' \
            '  <meta charset="utf-8">\n' \
            '  <style>\n' \
            '    @import url("epicyon-profile.css");\n'+ \
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
    profileStr+='<script>'+contentWarningScript()+'</script>'
    for item in outboxFeed['orderedItems']:
        if item['type']=='Create' or item['type']=='Announce':
            profileStr+= \
                individualPostAsHtml(baseDir,session,wfRequest,personCache, \
                                     nickname,domain,port,item,None,True,False)
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

def htmlProfileSkills(nickname: str,domain: str,skillsJson: {}) -> str:
    """Shows skills on the profile screen
    """
    profileStr=''
    for skill,level in skillsJson.items():
        profileStr+='<div>'+skill+'<br><div id="myProgress"><div id="myBar" style="width:'+str(level)+'%"></div></div></div><br>'
    if len(profileStr)==0:
        profileStr+='<p>@'+nickname+'@'+domain+' has no skills assigned</p>'
    else:
        profileStr='<center><div class="skill-title">'+profileStr+'</div></center>'
    return profileStr

def htmlProfileShares(nickname: str,domain: str,sharesJson: {}) -> str:
    """Shows shares on the profile screen
    """
    profileStr=''
    for item in sharesJson['orderedItems']:
        profileStr+='<div class="container">'
        profileStr+='<p class="share-title">'+item['displayName']+'</p>'
        profileStr+='<a href="'+item['imageUrl']+'">'
        profileStr+='<img src="'+item['imageUrl']+'" alt="Item image"></a>'
        profileStr+='<p>'+item['summary']+'</p>'
        profileStr+='<p><b>Type:</b> '+item['itemType']+' '
        profileStr+='<b>Category:</b> '+item['category']+' '
        profileStr+='<b>Location:</b> '+item['location']+'</p>'
        profileStr+='</div>'
    if len(profileStr)==0:
        profileStr+='<p>@'+nickname+'@'+domain+' is not sharing any items</p>'
    else:
        profileStr='<div class="share-title">'+profileStr+'</div>'
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
    profileDescription=profileJson['summary']
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
    loginButton=''

    followApprovalsSection=''
    followApprovals=''
    linkToTimelineStart=''
    linkToTimelineEnd=''

    if not authorized:
        loginButton='<br><a href="/login"><button class="loginButton">Login</button></a>'
    else:
        linkToTimelineStart='<a href="/users/'+nickname+'/inbox" title="Switch to timeline view" alt="Switch to timeline view">'
        linkToTimelineEnd='</a>'
        # are there any follow requests?
        followRequestsFilename=baseDir+'/accounts/'+nickname+'@'+domain+'/followrequests.txt'
        if os.path.isfile(followRequestsFilename):
            with open(followRequestsFilename,'r') as f:
                for line in f:
                    if len(line)>0:
                        # show a star on the followers tab
                        followApprovals='<img class="highlight" src="/icons/new.png"/>'
                        break
        if selected=='followers':
            if len(followApprovals)>0:
                with open(followRequestsFilename,'r') as f:
                    for followerHandle in f:
                        if len(line)>0:
                            if '://' in followerHandle:
                                followerActor=followerHandle
                            else:
                                followerActor=httpPrefix+'://'+followerHandle.split('@')[1]+'/users/'+followerHandle.split('@')[0]
                            basePath=httpPrefix+'://'+domainFull+'/users/'+nickname
                            followApprovalsSection+='<div class="container">'
                            followApprovalsSection+='<a href="'+followerActor+'">'
                            followApprovalsSection+='<span class="followRequestHandle">'+followerHandle+'</span></a>'
                            followApprovalsSection+='<a href="'+basePath+'/followapprove='+followerHandle+'">'
                            followApprovalsSection+='<button class="followApprove">Approve</button></a>'
                            followApprovalsSection+='<a href="'+basePath+'/followdeny='+followerHandle+'">'
                            followApprovalsSection+='<button class="followDeny">Deny</button></a>'
                            followApprovalsSection+='</div>'

    actor=profileJson['id']
    profileStr= \
        linkToTimelineStart+ \
        ' <div class="hero-image">' \
        '  <div class="hero-text">' \
        '    <img src="'+profileJson['icon']['url']+'" alt="'+nickname+'@'+domainFull+'">' \
        '    <h1>'+preferredName+'</h1>' \
        '    <p><b>@'+nickname+'@'+domainFull+'</b></p>' \
        '    <p>'+profileDescription+'</p>'+ \
        loginButton+ \
        '  </div>' \
        '</div>'+ \
        linkToTimelineEnd+ \
        '<div class="container">\n' \
        '  <center>' \
        '    <a href="'+actor+'"><button class="'+postsButton+'"><span>Posts </span></button></a>' \
        '    <a href="'+actor+'/following"><button class="'+followingButton+'"><span>Following </span></button></a>' \
        '    <a href="'+actor+'/followers"><button class="'+followersButton+'"><span>Followers </span>'+followApprovals+'</button></a>' \
        '    <a href="'+actor+'/roles"><button class="'+rolesButton+'"><span>Roles </span></button></a>' \
        '    <a href="'+actor+'/skills"><button class="'+skillsButton+'"><span>Skills </span></button></a>' \
        '    <a href="'+actor+'/shares"><button class="'+sharesButton+'"><span>Shares </span></button></a>' \
        '  </center>' \
        '</div>'

    profileStr+=followApprovalsSection
    
    with open(baseDir+'/epicyon-profile.css', 'r') as cssFile:
        profileStyle = cssFile.read().replace('image.png',actor+'/image.png')

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
        if selected=='skills':
            profileStr+= \
                htmlProfileSkills(nickname,domainFull,extraJson)
        if selected=='shares':
            profileStr+= \
                htmlProfileShares(nickname,domainFull,extraJson)
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

def contentWarningScript() -> str:
    """Returns a script used for content warnings
    """
    script= \
        'function showContentWarning(postID) {' \
        '  var x = document.getElementById(postID);' \
        '  if (x.style.display === "none") {' \
        '    x.style.display = "block";' \
        '  } else {' \
        '    x.style.display = "none";' \
        '  }' \
        '}'
    return script

def individualPostAsHtml(baseDir: str, \
                         session,wfRequest: {},personCache: {}, \
                         nickname: str,domain: str,port: int, \
                         postJsonObject: {}, \
                         avatarUrl: str, showAvatarDropdown: bool,
                         showIcons=False) -> str:
    """ Shows a single post as html
    """
    titleStr=''
    if postJsonObject['type']=='Announce':
        if postJsonObject.get('object'):
            if isinstance(postJsonObject['object'], str):
                # get the announced post
                asHeader = {'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"'}
                announcedJson = getJson(session,postJsonObject['object'],asHeader,None)
                if announcedJson:
                    if not announcedJson.get('type'):
                        return ''
                    if announcedJson['type']!='Create':
                        return ''
                    actorNickname=getNicknameFromActor(postJsonObject['actor'])
                    actorDomain,actorPort=getDomainFromActor(postJsonObject['actor'])
                    titleStr+='@'+actorNickname+'@'+actorDomain+' announced:<br>'
                    postJsonObject=announcedJson
                else:
                    return ''
            else:
                return ''
    if not isinstance(postJsonObject['object'], dict):
        return ''
    avatarPosition=''
    containerClass='container'
    containerClassIcons='containericons'
    timeClass='time-right'
    actorNickname=getNicknameFromActor(postJsonObject['actor'])
    actorDomain,actorPort=getDomainFromActor(postJsonObject['actor'])
    titleStr+='@'+actorNickname+'@'+actorDomain
    if postJsonObject['object']['inReplyTo']:
        containerClassIcons='containericons darker'
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

    if not avatarUrl:
        avatarUrl=postJsonObject['actor']+'/avatar.png'

    fullDomain=domain
    if port!=80 and port!=443:
        fullDomain=domain+':'+str(port)
        
    if fullDomain not in postJsonObject['actor']:
        inboxUrl,pubKeyId,pubKey,fromPersonId,sharedInbox,capabilityAcquisition,avatarUrl2,preferredName = \
            getPersonBox(session,wfRequest,personCache,'outbox')
        if avatarUrl2:
            avatarUrl=avatarUrl2
        if preferredName:
            titleStr=preferredName+' '+titleStr

    avatarDropdown= \
        '    <a href="'+postJsonObject['actor']+'">' \
        '    <img src="'+avatarUrl+'" title="Show profile" alt="Avatar"'+avatarPosition+'/></a>'

    if showAvatarDropdown and fullDomain+'/users/'+nickname not in postJsonObject['actor']:
        # if not following then show "Follow" in the dropdown
        followUnfollowStr='<a href="/users/'+nickname+'?follow='+postJsonObject['actor']+';'+avatarUrl+'">Follow</a>'
        # if following then show "Unfollow" in the dropdown
        if isFollowingActor(baseDir,nickname,domain,postJsonObject['actor']):
            followUnfollowStr='<a href="/users/'+nickname+'?unfollow='+postJsonObject['actor']+';'+avatarUrl+'">Unfollow</a>'

        avatarDropdown= \
            '  <div class="dropdown-timeline">' \
            '    <img src="'+avatarUrl+'" '+avatarPosition+'/>' \
            '    <div class="dropdown-timeline-content">' \
            '      <a href="'+postJsonObject['actor']+'">Visit</a>'+ \
            followUnfollowStr+ \
            '      <a href="/users/'+nickname+'?block='+postJsonObject['actor']+';'+avatarUrl+'">Block</a>' \
            '      <a href="/users/'+nickname+'?report='+postJsonObject['actor']+';'+avatarUrl+'">Report</a>' \
            '    </div>' \
            '  </div>'

    publishedStr=postJsonObject['object']['published']
    datetimeObject = datetime.strptime(publishedStr,"%Y-%m-%dT%H:%M:%SZ")
    publishedStr=datetimeObject.strftime("%a %b %d, %H:%M")
    footerStr='<span class="'+timeClass+'">'+publishedStr+'</span>\n'
    if showIcons:
        footerStr='<div class="'+containerClassIcons+'">'
        footerStr+='<a href="/users/'+nickname+'?replyto='+postJsonObject['object']['id']+'" title="Reply to this post">'
        footerStr+='<img src="/icons/reply.png"/></a>'
        footerStr+='<a href="/users/'+nickname+'?repeat='+postJsonObject['object']['id']+'" title="Repeat this post">'
        footerStr+='<img src="/icons/repeat_inactive.png"/></a>'
        footerStr+='<a href="/users/'+nickname+'?like='+postJsonObject['object']['id']+'" title="Like this post">'
        footerStr+='<img src="/icons/like_inactive.png"/></a>'
        footerStr+='<span class="'+timeClass+'">'+publishedStr+'</span>'
        footerStr+='</div>'

    if not postJsonObject['object']['sensitive']:
        contentStr=postJsonObject['object']['content']+attachmentStr
    else:
        postID='post'+str(createPassword(8))
        contentStr=''
        if postJsonObject['object'].get('summary'):
            contentStr+='<b>'+postJsonObject['object']['summary']+'</b> '
        else:
            contentStr+='<b>Sensitive</b> '
        contentStr+='<button class="cwButton" onclick="showContentWarning('+"'"+postID+"'"+')">SHOW MORE</button>'
        contentStr+='<div class="cwText" id="'+postID+'">'
        contentStr+=postJsonObject['object']['content']+attachmentStr
        contentStr+='</div>'

    return \
        '<div class="'+containerClass+'">\n'+ \
        avatarDropdown+ \
        '<p class="post-title">'+titleStr+'</p>'+ \
        contentStr+footerStr+ \
        '</div>\n'

def htmlTimeline(session,baseDir: str,wfRequest: {},personCache: {}, \
                 nickname: str,domain: str,port: int,timelineJson: {}, \
                 boxName: str) -> str:
    """Show the timeline as html
    """
    with open(baseDir+'/epicyon-profile.css', 'r') as cssFile:
        profileStyle = \
            cssFile.read().replace('banner.png', \
                                   '/users/'+nickname+'/banner.png')

    inboxButton='button'
    sentButton='button'
    if boxName=='inbox':
        inboxButton='buttonselected'
    elif boxName=='outbox':
        sentButton='buttonselected'
    actor='/users/'+nickname

    showIndividualPostIcons=True
    if boxName=='inbox':
        showIndividualPostIcons=True
    
    followApprovals=''
    followRequestsFilename=baseDir+'/accounts/'+nickname+'@'+domain+'/followrequests.txt'
    if os.path.isfile(followRequestsFilename):
        with open(followRequestsFilename,'r') as f:
            for line in f:
                if len(line)>0:
                    # show follow approvals icon
                    followApprovals='<a href="'+actor+'/followers"><img class="right" alt="Approve follow requests" title="Approve follow requests" src="/icons/person.png"/></a>'
                    break

    tlStr=htmlHeader(profileStyle)
    tlStr+= \
        '<a href="/users/'+nickname+'" title="Switch to profile view" alt="Switch to profile view">' \
        '<div class="timeline-banner">' \
        '</div></a>' \
        '<div class="container">\n'+ \
        '    <a href="'+actor+'/inbox"><button class="'+inboxButton+'"><span>Inbox </span></button></a>' \
        '    <a href="'+actor+'/outbox"><button class="'+sentButton+'"><span>Sent </span></button></a>' \
        '    <a href="'+actor+'/newpost"><img src="/icons/newpost.png" title="Create a new post" alt="Create a new post" class="right"/></a>'+ \
        '    <a href="'+actor+'/search"><img src="/icons/search.png" title="Search and follow" alt="Search and follow" class="right"/></a>'+ \
        followApprovals+ \
        '</div>'
    tlStr+='<script>'+contentWarningScript()+'</script>'
    for item in timelineJson['orderedItems']:
        if item['type']=='Create' or item['type']=='Announce':
            tlStr+=individualPostAsHtml(baseDir,session,wfRequest,personCache, \
                                        nickname,domain,port,item,None,True,showIndividualPostIcons)
    tlStr+=htmlFooter()
    return tlStr

def htmlInbox(session,baseDir: str,wfRequest: {},personCache: {}, \
              nickname: str,domain: str,port: int,inboxJson: {}) -> str:
    """Show the inbox as html
    """
    return htmlTimeline(session,baseDir,wfRequest,personCache, \
                        nickname,domain,port,inboxJson,'inbox')

def htmlOutbox(session,baseDir: str,wfRequest: {},personCache: {}, \
               nickname: str,domain: str,port: int,outboxJson: {}) -> str:
    """Show the Outbox as html
    """
    return htmlTimeline(session,baseDir,wfRequest,personCache, \
                        nickname,domain,port,outboxJson,'outbox')

def htmlIndividualPost(baseDir: str,session,wfRequest: {},personCache: {}, \
                       nickname: str,domain: str,port: int,postJsonObject: {}) -> str:
    """Show an individual post as html
    """
    return htmlHeader()+ \
        individualPostAsHtml(baseDir,session,wfRequest,personCache, \
                             nickname,domain,port,postJsonObject,None,True,False)+ \
        htmlFooter()

def htmlPostReplies(postJsonObject: {}) -> str:
    """Show the replies to an individual post as html
    """
    return htmlHeader()+"<h1>Replies</h1>"+htmlFooter()

def htmlFollowConfirm(baseDir: str,originPathStr: str,followActor: str,followProfileUrl: str) -> str:
    """Asks to confirm a follow
    """
    followDomain,port=getDomainFromActor(followActor)
    
    if os.path.isfile(baseDir+'/img/follow-background.png'):
        if not os.path.isfile(baseDir+'/accounts/follow-background.png'):
            copyfile(baseDir+'/img/follow-background.png',baseDir+'/accounts/follow-background.png')

    with open(baseDir+'/epicyon-follow.css', 'r') as cssFile:
        profileStyle = cssFile.read()
    followStr=htmlHeader(profileStyle)
    followStr+='<div class="follow">'
    followStr+='  <div class="followAvatar">'
    followStr+='  <center>'
    followStr+='  <a href="'+followActor+'">'
    followStr+='  <img src="'+followProfileUrl+'"/></a>'
    followStr+='  <p class="followText">Follow '+getNicknameFromActor(followActor)+'@'+followDomain+' ?</p>'
    followStr+= \
        '  <form method="POST" action="'+originPathStr+'/followconfirm">' \
        '    <input type="hidden" name="actor" value="'+followActor+'">' \
        '    <button type="submit" class="button" name="submitYes">Yes</button>' \
        '    <a href="'+originPathStr+'"><button class="button">No</button></a>' \
        '  </form>'
    followStr+='</center>'
    followStr+='</div>'
    followStr+='</div>'
    followStr+=htmlFooter()
    return followStr

def htmlUnfollowConfirm(baseDir: str,originPathStr: str,followActor: str,followProfileUrl: str) -> str:
    """Asks to confirm unfollowing an actor
    """
    followDomain,port=getDomainFromActor(followActor)
    
    if os.path.isfile(baseDir+'/img/follow-background.png'):
        if not os.path.isfile(baseDir+'/accounts/follow-background.png'):
            copyfile(baseDir+'/img/follow-background.png',baseDir+'/accounts/follow-background.png')

    with open(baseDir+'/epicyon-follow.css', 'r') as cssFile:
        profileStyle = cssFile.read()
    followStr=htmlHeader(profileStyle)
    followStr+='<div class="follow">'
    followStr+='  <div class="followAvatar">'
    followStr+='  <center>'
    followStr+='  <a href="'+followActor+'">'
    followStr+='  <img src="'+followProfileUrl+'"/></a>'
    followStr+='  <p class="followText">Stop following '+getNicknameFromActor(followActor)+'@'+followDomain+' ?</p>'
    followStr+= \
        '  <form method="POST" action="'+originPathStr+'/unfollowconfirm">' \
        '    <input type="hidden" name="actor" value="'+followActor+'">' \
        '    <button type="submit" class="button" name="submitYes">Yes</button>' \
        '    <a href="'+originPathStr+'"><button class="button">No</button></a>' \
        '  </form>'
    followStr+='</center>'
    followStr+='</div>'
    followStr+='</div>'
    followStr+=htmlFooter()
    return followStr

def htmlSearch(baseDir: str,path: str) -> str:
    """Search called from the timeline icon
    """
    actor=path.replace('/search','')
    nickname=getNicknameFromActor(actor)
    domain,port=getDomainFromActor(actor)
    
    if os.path.isfile(baseDir+'/img/search-background.png'):
        if not os.path.isfile(baseDir+'/accounts/search-background.png'):
            copyfile(baseDir+'/img/search-background.png',baseDir+'/accounts/search-background.png')

    with open(baseDir+'/epicyon-follow.css', 'r') as cssFile:
        profileStyle = cssFile.read()
    followStr=htmlHeader(profileStyle)
    followStr+='<div class="follow">'
    followStr+='  <div class="followAvatar">'
    followStr+='  <center>'    
    followStr+='  <p class="followText">Enter an address to search for</p>'
    followStr+= \
        '  <form method="POST" action="'+actor+'/searchhandle">' \
        '    <input type="hidden" name="actor" value="'+actor+'">' \
        '    <input type="text" name="searchtext" autofocus><br>' \
        '    <button type="submit" class="button" name="submitSearch">Submit</button>' \
        '    <a href="'+actor+'"><button class="button">Go Back</button></a>' \
        '  </form>'
    followStr+='  </center>'
    followStr+='  </div>'
    followStr+='</div>'
    followStr+=htmlFooter()
    return followStr

def htmlProfileAfterSearch(baseDir: str,path: str,httpPrefix: str, \
                           nickname: str,domain: str,port: int, \
                           profileHandle: str, \
                           session,wfRequest: {},personCache: {},
                           debug: bool) -> str:
    """Show a profile page after a search for a fediverse address
    """
    if '/users/' in profileHandle:
        searchNickname=getNicknameFromActor(profileHandle)
        searchDomain,searchPort=getDomainFromActor(profileHandle)
    else:
        if '@' not in profileHandle:
            if debug:
                print('DEBUG: no @ in '+profileHandle)
            return None
        if profileHandle.startswith('@'):
            profileHandle=profileHandle[1:]
        if '@' not in profileHandle:
            if debug:
                print('DEBUG: no @ in '+profileHandle)
            return None
        searchNickname=profileHandle.split('@')[0]
        searchDomain=profileHandle.split('@')[1]
        searchPort=None
        if ':' in searchDomain:
            searchPort=int(searchDomain.split(':')[1])
            searchDomain=searchDomain.split(':')[0]
    if not searchNickname:
        if debug:
            print('DEBUG: No nickname found in '+profileHandle)
        return None
    if not searchDomain:
        if debug:
            print('DEBUG: No domain found in '+profileHandle)
        return None
    searchDomainFull=searchDomain
    if searchPort:
        if searchPort!=80 and searchPort!=443:
            searchDomainFull=searchDomain+':'+str(searchPort)
    
    profileStr=''
    with open(baseDir+'/epicyon-profile.css', 'r') as cssFile:
        wf = webfingerHandle(session,searchNickname+'@'+searchDomain,httpPrefix,wfRequest)
        if not wf:
            if debug:
                print('DEBUG: Unable to webfinger '+searchNickname+'@'+searchDomain)
            return None
        asHeader = {'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"'}
        personUrl = getUserUrl(wf)
        profileJson = getJson(session,personUrl,asHeader,None)
        if not profileJson:
            if debug:
                print('DEBUG: No actor returned from '+personUrl)
            return None
        avatarUrl=''
        if profileJson.get('icon'):
            if profileJson['icon'].get('url'):
                avatarUrl=profileJson['icon']['url']
        preferredName=searchNickname
        if profileJson.get('preferredUsername'):
            preferredName=profileJson['preferredUsername']
        profileDescription=''
        if profileJson.get('summary'):
            profileDescription=profileJson['summary']
        outboxUrl=None
        if not profileJson.get('outbox'):
            if debug:
                pprint(profileJson)
                print('DEBUG: No outbox found')
            return None
        outboxUrl=profileJson['outbox']
        profileBackgroundImage=''
        if profileJson.get('image'):
            if profileJson['image'].get('url'):
                profileBackgroundImage=profileJson['image']['url']

        profileStyle = cssFile.read().replace('image.png',profileBackgroundImage)

        # url to return to
        backUrl=path
        if not backUrl.endswith('/inbox'):
            backUrl+='/inbox'

        profileStr= \
            ' <div class="hero-image">' \
            '  <div class="hero-text">' \
            '    <img src="'+avatarUrl+'" alt="'+searchNickname+'@'+searchDomainFull+'">' \
            '    <h1>'+preferredName+'</h1>' \
            '    <p><b>@'+searchNickname+'@'+searchDomainFull+'</b></p>' \
            '    <p>'+profileDescription+'</p>'+ \
            '  </div>' \
            '</div>'+ \
            '<div class="container">\n' \
            '  <form method="POST" action="'+backUrl+'/followconfirm">' \
            '    <center>' \
            '      <input type="hidden" name="actor" value="'+personUrl+'">' \
            '      <button type="submit" class="button" name="submitYes">Follow</button>' \
            '      <a href="'+backUrl+'"><button class="button">Go Back</button></a>' \
            '    </center>' \
            '  </form>' \
            '</div>'

        profileStr+='<script>'+contentWarningScript()+'</script>'

        result = []
        i = 0
        for item in parseUserFeed(session,outboxUrl,asHeader):
            if not item.get('type'):
                continue
            if item['type']!='Create' and item['type']!='Announce':
                continue
            if not item.get('object'):
                continue
            profileStr+= \
                individualPostAsHtml(baseDir, \
                                     session,wfRequest,personCache, \
                                     nickname,domain,port, \
                                     item,avatarUrl,False,False)
            i+=1
            if i>=20:
                break

    return htmlHeader(profileStyle)+profileStr+htmlFooter()
