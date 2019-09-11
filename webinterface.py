__filename__ = "webinterface.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.0.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import json
import time
import os
import commentjson
from datetime import datetime
from dateutil.parser import parse
from shutil import copyfile
from pprint import pprint
from person import personBoxJson
from utils import getNicknameFromActor
from utils import getDomainFromActor
from utils import locatePost
from utils import noOfAccounts
from utils import isPublicPost
from utils import getDisplayName
from follow import isFollowingActor
from webfinger import webfingerHandle
from posts import isDM
from posts import getPersonBox
from posts import getUserUrl
from posts import parseUserFeed
from posts import populateRepliesJson
from posts import isModerator
from posts import outboxMessageCreateWrap
from session import getJson
from auth import createPassword
from like import likedByPerson
from like import noOfLikes
from announce import announcedByPerson
from blocking import isBlocked
from content import getMentionsFromHtml
from config import getConfigParam
from skills import getSkills
from cache import getPersonFromCache

def getPersonAvatarUrl(baseDir: str,personUrl: str,personCache: {}) -> str:
    """Returns the avatar url for the person
    """
    personJson = getPersonFromCache(baseDir,personUrl,personCache)
    if personJson:
        if personJson.get('icon'):
            if personJson['icon'].get('url'):
                return personJson['icon']['url']
    return None

def htmlSearchEmoji(translate: {},baseDir: str,searchStr: str) -> str:
    """Search results for emoji
    """

    if not os.path.isfile(baseDir+'/emoji/emoji.json'):
        copyfile(baseDir+'/emoji/default_emoji.json',baseDir+'/emoji/emoji.json')

    searchStr=searchStr.lower().replace(':','').strip('\n')
    cssFilename=baseDir+'/epicyon-profile.css'
    if os.path.isfile(baseDir+'/epicyon.css'):
        cssFilename=baseDir+'/epicyon.css'        
    with open(cssFilename, 'r') as cssFile:
        emojiCSS=cssFile.read()
        emojiLookupFilename=baseDir+'/emoji/emoji.json'

        # create header
        emojiForm=htmlHeader(cssFilename,emojiCSS)
        emojiForm+='<center><h1>'+translate['Emoji Search']+'</h1></center>'

        # does the lookup file exist?
        if not os.path.isfile(emojiLookupFilename):
            emojiForm+='<center><h5>'+translate['No results']+'</h5></center>'
            emojiForm+=htmlFooter()
            return emojiForm
        
        with open(emojiLookupFilename, 'r') as fp:
            emojiJson=commentjson.load(fp)
            results={}
            for emojiName,filename in emojiJson.items():
                if searchStr in emojiName:
                    results[emojiName] = filename+'.png'
            for emojiName,filename in emojiJson.items():
                if emojiName in searchStr:
                    results[emojiName] = filename+'.png'
            headingShown=False
            emojiForm+='<center>'
            for emojiName,filename in results.items():
                if os.path.isfile(baseDir+'/emoji/'+filename):
                    if not headingShown:
                        emojiForm+='<center><h5>'+translate['Copy the text then paste it into your post']+'</h5></center>'
                        headingShown=True
                    emojiForm+='<h3>:'+emojiName+':<img class="searchEmoji" src="/emoji/'+filename+'"/></h3>'
            emojiForm+='</center>'

        emojiForm+=htmlFooter()
    return emojiForm

def htmlSearchSharedItems(translate: {}, \
                          baseDir: str,searchStr: str, \
                          pageNumber: int, \
                          resultsPerPage: int, \
                          httpPrefix: str, \
                          domainFull: str,actor: str) -> str:
    """Search results for shared items
    """
    currPage=1
    ctr=0
    sharedItemsForm=''
    searchStrLower=searchStr.replace('%2B','+').replace('%40','@').replace('%3A',':').replace('%23','#').lower().strip('\n')
    searchStrLowerList=searchStrLower.split('+')
    cssFilename=baseDir+'/epicyon.css'
    if os.path.isfile(baseDir+'/epicyon.css'):
        cssFilename=baseDir+'/epicyon.css'        
    with open(cssFilename, 'r') as cssFile:
        sharedItemsCSS=cssFile.read()
        sharedItemsForm=htmlHeader(cssFilename,sharedItemsCSS)
        sharedItemsForm+='<center><h1>'+translate['Shared Items Search']+'</h1></center>'
        resultsExist=False
        for subdir, dirs, files in os.walk(baseDir+'/accounts'):
            for handle in dirs:
                if '@' not in handle:
                    continue
                contactNickname=handle.split('@')[0]
                sharesFilename=baseDir+'/accounts/'+handle+'/shares.json'
                if not os.path.isfile(sharesFilename):
                    continue
                with open(sharesFilename, 'r') as fp:
                    sharesJson=commentjson.load(fp)
                for name,sharedItem in sharesJson.items():
                    matched=True
                    for searchSubstr in searchStrLowerList:
                        subStrMatched=False
                        searchSubstr=searchSubstr.strip()
                        if searchSubstr in sharedItem['location'].lower():
                            subStrMatched=True
                        elif searchSubstr in sharedItem['summary'].lower():
                            subStrMatched=True
                        elif searchSubstr in sharedItem['displayName'].lower():
                            subStrMatched=True
                        elif searchSubstr in sharedItem['category'].lower():
                            subStrMatched=True
                        if not subStrMatched:
                            matched=False
                            break
                    if matched:
                        if currPage==pageNumber:
                            sharedItemsForm+='<div class="container">'
                            sharedItemsForm+='<p class="share-title">'+sharedItem['displayName']+'</p>'
                            if sharedItem.get('imageUrl'):
                                sharedItemsForm+='<a href="'+sharedItem['imageUrl']+'">'
                                sharedItemsForm+='<img src="'+sharedItem['imageUrl']+'" alt="Item image"></a>'
                            sharedItemsForm+='<p>'+sharedItem['summary']+'</p>'
                            sharedItemsForm+='<p><b>'+translate['Type']+':</b> '+sharedItem['itemType']+' '
                            sharedItemsForm+='<b>'+translate['Category']+':</b> '+sharedItem['category']+' '
                            sharedItemsForm+='<b>'+translate['Location']+':</b> '+sharedItem['location']+'</p>'
                            contactActor=httpPrefix+'://'+domainFull+'/users/'+contactNickname
                            sharedItemsForm+='<p><a href="'+actor+'?replydm=sharedesc:'+sharedItem['displayName']+'?mention='+contactActor+'"><button class="button">'+translate['Contact']+'</button></a>'
                            if actor.endswith('/users/'+contactNickname):
                                sharedItemsForm+=' <a href="'+actor+'?rmshare='+name+'"><button class="button">'+translate['Remove']+'</button></a>'
                            sharedItemsForm+='</p></div>'
                            if not resultsExist and currPage>1:
                                # previous page link, needs to be a POST
                                sharedItemsForm+= \
                                    '<form method="POST" action="'+actor+'/searchhandle?page='+str(pageNumber-1)+'">' \
                                    '  <input type="hidden" name="actor" value="'+actor+'">' \
                                    '  <input type="hidden" name="searchtext" value="'+searchStrLower+'"><br>' \
                                    '  <center><a href="'+actor+'" type="submit" name="submitSearch">' \
                                    '    <img class="pageicon" src="/icons/pageup.png" title="'+translate['Page up']+'" alt="'+translate['Page up']+'"/></a>' \
                                    '  </center>' \
                                    '</form>'
                            resultsExist=True
                        ctr+=1
                        if ctr>=resultsPerPage:
                            currPage+=1
                            if currPage>pageNumber:
                                # next page link, needs to be a POST
                                sharedItemsForm+= \
                                    '<form method="POST" action="'+actor+'/searchhandle?page='+str(pageNumber+1)+'">' \
                                    '  <input type="hidden" name="actor" value="'+actor+'">' \
                                    '  <input type="hidden" name="searchtext" value="'+searchStrLower+'"><br>' \
                                    '  <center><a href="'+actor+'" type="submit" name="submitSearch">' \
                                    '    <img class="pageicon" src="/icons/pagedown.png" title="'+translate['Page down']+'" alt="'+translate['Page down']+'"/></a>' \
                                    '  </center>' \
                                    '</form>'
                                break
                            ctr=0
        if not resultsExist:
            sharedItemsForm+='<center><h5>'+translate['No results']+'</h5></center>'
        sharedItemsForm+=htmlFooter()
    return sharedItemsForm    

def htmlModerationInfo(translate: {},baseDir: str) -> str:
    infoForm=''
    cssFilename=baseDir+'/epicyon-profile.css'
    if os.path.isfile(baseDir+'/epicyon.css'):
        cssFilename=baseDir+'/epicyon.css'        
    with open(cssFilename, 'r') as cssFile:
        infoCSS=cssFile.read()
        infoForm=htmlHeader(cssFilename,infoCSS)

        infoForm+='<center><h1>'+translate['Moderation Information']+'</h1></center>'

        infoShown=False        
        suspendedFilename=baseDir+'/accounts/suspended.txt'
        if os.path.isfile(suspendedFilename):
            with open(suspendedFilename, "r") as f:
                suspendedStr = f.read()
                infoForm+= \
                    '<div class="container">' \
                    '  <br><b>'+translate['Suspended accounts']+'</b>' \
                    '  <br>'+translate['These are currently suspended']+ \
                    '  <textarea id="message" name="suspended" style="height:200px">'+suspendedStr+'</textarea>' \
                    '</div>'
                infoShown=True

        blockingFilename=baseDir+'/accounts/blocking.txt'
        if os.path.isfile(blockingFilename):
            with open(blockingFilename, "r") as f:
                blockedStr = f.read()
                infoForm+= \
                    '<div class="container">' \
                    '  <br><b>'+translate['Blocked accounts and hashtags']+'</b>' \
                    '  <br>'+translate['These are globally blocked for all accounts on this instance']+ \
                    '  <textarea id="message" name="blocked" style="height:200px">'+blockedStr+'</textarea>' \
                    '</div>'        
                infoShown=True
        if not infoShown:
            infoForm+='<center><p>'+translate['Any blocks or suspensions made by moderators will be shown here.']+'</p></center>'
        infoForm+=htmlFooter()
    return infoForm    

def htmlHashtagSearch(translate: {}, \
                      baseDir: str,hashtag: str,pageNumber: int,postsPerPage: int, \
                      session,wfRequest: {},personCache: {}, \
                      httpPrefix: str,projectVersion: str) -> str:
    """Show a page containing search results for a hashtag
    """
    if hashtag.startswith('#'):
        hashtag=hashtag[1:]
    hashtagIndexFile=baseDir+'/tags/'+hashtag+'.txt'
    if not os.path.isfile(hashtagIndexFile):
        return None

    # read the index
    with open(hashtagIndexFile, "r") as f:
        lines = f.readlines()
    cssFilename=baseDir+'/epicyon-profile.css'
    if os.path.isfile(baseDir+'/epicyon.css'):
        cssFilename=baseDir+'/epicyon.css'        
    with open(cssFilename, 'r') as cssFile:
        hashtagSearchCSS = cssFile.read()

    startIndex=len(lines)-1-int(pageNumber*postsPerPage)
    if startIndex<0:
        startIndex=len(lines)-1
    endIndex=startIndex-postsPerPage
    if endIndex<0:
        endIndex=0
        
    hashtagSearchForm=htmlHeader(cssFilename,hashtagSearchCSS)
    hashtagSearchForm+='<center><h1>#'+hashtag+'</h1></center>'
    if startIndex!=len(lines)-1:
        # previous page link
        hashtagSearchForm+='<center><a href="/tags/'+hashtag+'?page='+str(pageNumber-1)+'"><img class="pageicon" src="/icons/pageup.png" title="'+translate['Page up']+'" alt="'+translate['Page up']+'"></a></center>'
    index=startIndex
    while index>=endIndex:
        postId=lines[index].strip('\n')
        nickname=getNicknameFromActor(postId)
        if not nickname:
            index-=1
            continue
        domain,port=getDomainFromActor(postId)
        if not domain:
            index-=1
            continue
        postFilename=locatePost(baseDir,nickname,domain,postId)
        if not postFilename:
            index-=1
            continue
        with open(postFilename, 'r') as fp:
            postJsonObject=commentjson.load(fp)
            if not isPublicPost(postJsonObject):
                index-=1
                continue
            hashtagSearchForm+= \
                individualPostAsHtml(translate,None, \
                                     baseDir,session,wfRequest,personCache, \
                                     nickname,domain,port,postJsonObject, \
                                     None,True,False, \
                                     httpPrefix,projectVersion, \
                                     False,False,False,False)
        index-=1

    if endIndex>0:
        # next page link
        hashtagSearchForm+='<center><a href="/tags/'+hashtag+'?page='+str(pageNumber+1)+'"><img class="pageicon" src="/icons/pagedown.png" title="'+translate['Page down']+'" alt="'+translate['Page down']+'"></a></center>'
    hashtagSearchForm+=htmlFooter()
    return hashtagSearchForm

def htmlSkillsSearch(translate: {},baseDir: str, \
                     skillsearch: str,instanceOnly: bool, \
                     postsPerPage: int) -> str:
    """Show a page containing search results for a skill
    """
    if skillsearch.startswith('*'):
        skillsearch=skillsearch[1:].strip()

    skillsearch=skillsearch.lower().strip('\n')

    results=[]
    # search instance accounts
    for subdir, dirs, files in os.walk(baseDir+'/accounts/'):
        for f in files:
            if not f.endswith('.json'):
                continue
            if '@' not in f:
                continue
            if f.startswith('inbox@'):
                continue
            actorFilename = os.path.join(subdir, f)
            with open(actorFilename, 'r') as fp:
                actorJson=commentjson.load(fp)
                if actorJson.get('id') and \
                   actorJson.get('skills') and \
                   actorJson.get('name') and \
                   actorJson.get('icon'):
                    actor=actorJson['id']
                    for skillName,skillLevel in actorJson['skills'].items():
                        skillName=skillName.lower()
                        if skillName in skillsearch or skillsearch in skillName:
                            skillLevelStr=str(skillLevel)
                            if skillLevel<100:
                                skillLevelStr='0'+skillLevelStr
                            if skillLevel<10:
                                skillLevelStr='0'+skillLevelStr
                            indexStr=skillLevelStr+';'+actor+';'+actorJson['name']+';'+actorJson['icon']['url']
                            if indexStr not in results:
                                results.append(indexStr)
    if not instanceOnly:
        # search actor cache
        for subdir, dirs, files in os.walk(baseDir+'/cache/actors/'):
            for f in files:
                if not f.endswith('.json'):
                    continue
                if '@' not in f:
                    continue
                if f.startswith('inbox@'):
                    continue
                actorFilename = os.path.join(subdir, f)
                with open(actorFilename, 'r') as fp:
                    cachedActorJson=commentjson.load(fp)
                    if cachedActorJson.get('actor'):
                        actorJson=cachedActorJson['actor']
                        if actorJson.get('id') and \
                           actorJson.get('skills') and \
                           actorJson.get('name') and \
                           actorJson.get('icon'):
                            actor=actorJson['id']
                            for skillName,skillLevel in actorJson['skills'].items():
                                skillName=skillName.lower()
                                if skillName in skillsearch or skillsearch in skillName:
                                    skillLevelStr=str(skillLevel)
                                    if skillLevel<100:
                                        skillLevelStr='0'+skillLevelStr
                                    if skillLevel<10:
                                        skillLevelStr='0'+skillLevelStr                                
                                    indexStr=skillLevelStr+';'+actor+';'+actorJson['name']+';'+actorJson['icon']['url']
                                    if indexStr not in results:
                                        results.append(indexStr)

    results.sort(reverse=True)

    cssFilename=baseDir+'/epicyon-profile.css'
    if os.path.isfile(baseDir+'/epicyon.css'):
        cssFilename=baseDir+'/epicyon.css'        
    with open(cssFilename, 'r') as cssFile:
        skillSearchCSS = cssFile.read()
        
    skillSearchForm=htmlHeader(cssFilename,skillSearchCSS)
    skillSearchForm+='<center><h1>'+translate['Skills search']+': '+skillsearch+'</h1></center>'

    if len(results)==0:
        skillSearchForm+='<center><h5>'+translate['No results']+'</h5></center>'
    else:
        skillSearchForm+='<center>'
        ctr=0
        for skillMatch in results:
            skillMatchFields=skillMatch.split(';')
            if len(skillMatchFields)==4:
                actor=skillMatchFields[1]
                actorName=skillMatchFields[2]
                avatarUrl=skillMatchFields[3]
                skillSearchForm+='<div class="search-result""><a href="'+actor+'/skills">'
                skillSearchForm+='<img src="'+avatarUrl+'"/><span class="search-result-text">'+actorName+'</span></a></div>'
                ctr+=1
                if ctr>=postsPerPage:
                    break
        skillSearchForm+='</center>'
    skillSearchForm+=htmlFooter()
    return skillSearchForm

def htmlEditProfile(translate: {},baseDir: str,path: str,domain: str,port: int) -> str:
    """Shows the edit profile screen
    """
    pathOriginal=path
    path=path.replace('/inbox','').replace('/outbox','').replace('/shares','')
    nickname=getNicknameFromActor(path)
    if not nickname:
        return ''
    domainFull=domain
    if port:
        if port!=80 and port!=443:
            if ':' not in domain:
                domainFull=domain+':'+str(port)

    actorFilename=baseDir+'/accounts/'+nickname+'@'+domain+'.json'
    if not os.path.isfile(actorFilename):
        return ''

    isBot=''
    displayNickname=nickname
    bioStr=''
    manuallyApprovesFollowers=''
    with open(actorFilename, 'r') as fp:
        actorJson=commentjson.load(fp)
        if actorJson.get('name'):
            displayNickname=actorJson['name']
        if actorJson.get('summary'):
            bioStr=actorJson['summary'].replace('<p>','').replace('</p>','')
        if actorJson.get('manuallyApprovesFollowers'):
            if actorJson['manuallyApprovesFollowers']:
                manuallyApprovesFollowers='checked'
            else:
                manuallyApprovesFollowers=''
        if actorJson.get('type'):
            if actorJson['type']=='Service':
                isBot='checked'
                
    filterStr=''
    filterFilename=baseDir+'/accounts/'+nickname+'@'+domain+'/filters.txt'
    if os.path.isfile(filterFilename):
        with open(filterFilename, 'r') as filterfile:
            filterStr=filterfile.read()

    blockedStr=''
    blockedFilename=baseDir+'/accounts/'+nickname+'@'+domain+'/blocking.txt'
    if os.path.isfile(blockedFilename):
        with open(blockedFilename, 'r') as blockedfile:
            blockedStr=blockedfile.read()

    allowedInstancesStr=''
    allowedInstancesFilename=baseDir+'/accounts/'+nickname+'@'+domain+'/allowedinstances.txt'
    if os.path.isfile(allowedInstancesFilename):
        with open(allowedInstancesFilename, 'r') as allowedInstancesFile:
            allowedInstancesStr=allowedInstancesFile.read()

    skills=getSkills(baseDir,nickname,domain)
    skillsStr=''
    skillCtr=1
    if skills:
        for skillDesc,skillValue in skills.items():
            skillsStr+='<p><input type="text" placeholder="'+translate['Skill']+' '+str(skillCtr)+'" name="skillName'+str(skillCtr)+'" value="'+skillDesc+'" style="width:40%">'
            skillsStr+='<input type="range" min="1" max="100" class="slider" name="skillValue'+str(skillCtr)+'" value="'+str(skillValue)+'"></p>'
            skillCtr+=1

    skillsStr+='<p><input type="text" placeholder="Skill '+str(skillCtr)+'" name="skillName'+str(skillCtr)+'" value="" style="width:40%">'
    skillsStr+='<input type="range" min="1" max="100" class="slider" name="skillValue'+str(skillCtr)+'" value="50"></p>' \

    cssFilename=baseDir+'/epicyon-profile.css'
    if os.path.isfile(baseDir+'/epicyon.css'):
        cssFilename=baseDir+'/epicyon.css'        
    with open(cssFilename, 'r') as cssFile:
        editProfileCSS = cssFile.read()

    moderatorsStr=''
    adminNickname=getConfigParam(baseDir,'admin')
    if path.startswith('/users/'+adminNickname+'/'):
        moderators=''
        moderatorsFile=baseDir+'/accounts/moderators.txt'
        if os.path.isfile(moderatorsFile):
            with open(moderatorsFile, "r") as f:
                moderators = f.read()
        moderatorsStr= \
            '<div class="container">' \
            '  <b>'+translate['Moderators']+'</b><br>' \
            '  '+translate['A list of moderator nicknames. One per line.']+ \
            '  <textarea id="message" name="moderators" placeholder="'+translate['List of moderator nicknames']+'..." style="height:200px">'+moderators+'</textarea>' \
            '</div>'
        
    editProfileForm=htmlHeader(cssFilename,editProfileCSS)
    editProfileForm+= \
        '<form enctype="multipart/form-data" method="POST" action="'+path+'/profiledata">' \
        '  <div class="vertical-center">' \
        '    <p class="new-post-text">'+translate['Profile for']+' '+nickname+'@'+domainFull+'</p>' \
        '    <div class="container">' \
        '      <input type="submit" name="submitProfile" value="'+translate['Submit']+'">' \
        '      <a href="'+pathOriginal+'"><button class="cancelbtn">'+translate['Cancel']+'</button></a>' \
        '    </div>'+ \
        '    <div class="container">' \
        '      <input type="text" placeholder="name" name="displayNickname" value="'+displayNickname+'">' \
        '      <textarea id="message" name="bio" placeholder="'+translate['Your bio']+'..." style="height:200px">'+bioStr+'</textarea>' \
        '    </div>' \
        '    <div class="container">' \
        '      '+translate['The files attached below should be no larger than 10MB in total uploaded at once.']+'<br>' \
        '      '+translate['Avatar image']+ \
        '      <input type="file" id="avatar" name="avatar"' \
        '            accept=".png">' \
        '      <br>'+translate['Background image']+ \
        '      <input type="file" id="image" name="image"' \
        '            accept=".png">' \
        '      <br>'+translate['Timeline banner image']+ \
        '      <input type="file" id="banner" name="banner"' \
        '            accept=".png">' \
        '    </div>' \
        '    <div class="container">' \
        '      <input type="checkbox" class=profilecheckbox" name="approveFollowers" '+manuallyApprovesFollowers+'>'+translate['Approve follower requests']+'<br>' \
        '      <input type="checkbox" class=profilecheckbox" name="isBot" '+isBot+'>'+translate['This is a bot account']+'<br>' \
        '      <br><b>'+translate['Filtered words']+'</b>' \
        '      <br>'+translate['One per line']+ \
        '      <textarea id="message" name="filteredWords" placeholder="" style="height:200px">'+filterStr+'</textarea>' \
        '      <br><b>'+translate['Blocked accounts']+'</b>' \
        '      <br>'+translate['Blocked accounts, one per line, in the form nickname@domain or *@blockeddomain']+ \
        '      <textarea id="message" name="blocked" placeholder="" style="height:200px">'+blockedStr+'</textarea>' \
        '      <br><b>'+translate['Federation list']+'</b>' \
        '      <br>'+translate['Federate only with a defined set of instances. One domain name per line.']+ \
        '      <textarea id="message" name="allowedInstances" placeholder="" style="height:200px">'+allowedInstancesStr+'</textarea>' \
        '    </div>' \
        '    <div class="container">' \
        '      <b>'+translate['Skills']+'</b><br>' \
        '      '+translate['If you want to participate within organizations then you can indicate some skills that you have and approximate proficiency levels. This helps organizers to construct teams with an appropriate combination of skills.']+ \
        skillsStr+moderatorsStr+ \
        '    </div>' \
        '  </div>' \
        '</form>'
    editProfileForm+=htmlFooter()
    return editProfileForm

def htmlGetLoginCredentials(loginParams: str,lastLoginTime: int) -> (str,str,bool):
    """Receives login credentials via HTTPServer POST
    """
    if not loginParams.startswith('username='):
        return None,None,None
    # minimum time between login attempts
    currTime=int(time.time())
    if currTime<lastLoginTime+10:
        return None,None,None
    if '&' not in loginParams:
        return None,None,None
    loginArgs=loginParams.split('&')
    nickname=None
    password=None
    register=False
    for arg in loginArgs:
        if '=' in arg:
            if arg.split('=',1)[0]=='username':
                nickname=arg.split('=',1)[1]
            elif arg.split('=',1)[0]=='password':
                password=arg.split('=',1)[1]
            elif arg.split('=',1)[0]=='register':
                register=True
    return nickname,password,register

def htmlLogin(translate: {},baseDir: str) -> str:
    """Shows the login screen
    """
    accounts=noOfAccounts(baseDir)

    if not os.path.isfile(baseDir+'/accounts/login.png'):
        copyfile(baseDir+'/img/login.png',baseDir+'/accounts/login.png')
    if os.path.isfile(baseDir+'/img/login-background.png'):
        if not os.path.isfile(baseDir+'/accounts/login-background.png'):
            copyfile(baseDir+'/img/login-background.png',baseDir+'/accounts/login-background.png')

    if accounts>0:
        loginText='<p class="login-text">'+translate['Welcome. Please enter your login details below.']+'</p>'
    else:
        loginText='<p class="login-text">'+translate['Please enter some credentials']+'</p>'
        loginText+='<p class="login-text">'+translate['You will become the admin of this site.']+'</p>'
    if os.path.isfile(baseDir+'/accounts/login.txt'):
        # custom login message
        with open(baseDir+'/accounts/login.txt', 'r') as file:
            loginText = '<p class="login-text">'+file.read()+'</p>'    

    cssFilename=baseDir+'/epicyon-login.css'
    if os.path.isfile(baseDir+'/login.css'):
        cssFilename=baseDir+'/login.css'
    with open(cssFilename, 'r') as cssFile:
        loginCSS = cssFile.read()

    # show the register button
    registerButtonStr=''
    if getConfigParam(baseDir,'registration')=='open':
        if int(getConfigParam(baseDir,'registrationsRemaining'))>0:
            if accounts>0:
                loginText='<p class="login-text">'+translate['Welcome. Please login or register a new account.']+'</p>'
            registerButtonStr='<button type="submit" name="register">Register</button>'

    TOSstr='<p class="login-text"><a href="/terms">'+translate['Terms of Service']+'</a></p>'
    TOSstr+='<p class="login-text"><a href="/about">'+translate['About this Instance']+'</a></p>'

    loginButtonStr=''
    if accounts>0:
        loginButtonStr='<button type="submit" name="submit">'+translate['Login']+'</button>'
            
    loginForm=htmlHeader(cssFilename,loginCSS)
    loginForm+= \
        '<form method="POST" action="/login">' \
        '  <div class="imgcontainer">' \
        '    <img src="login.png" alt="login image" class="loginimage">'+ \
        loginText+TOSstr+ \
        '  </div>' \
        '' \
        '  <div class="container">' \
        '    <label for="nickname"><b>'+translate['Nickname']+'</b></label>' \
        '    <input type="text" placeholder="'+translate['Enter Nickname']+'" name="username" required autofocus>' \
        '' \
        '    <label for="password"><b>'+translate['Password']+'</b></label>' \
        '    <input type="password" placeholder="'+translate['Enter Password']+'" name="password" required>'+ \
        registerButtonStr+loginButtonStr+ \
        '  </div>' \
        '</form>'
    loginForm+=htmlFooter()
    return loginForm

def htmlTermsOfService(baseDir: str,httpPrefix: str,domainFull: str) -> str:
    """Show the terms of service screen
    """
    adminNickname = getConfigParam(baseDir,'admin')
    if not os.path.isfile(baseDir+'/accounts/tos.txt'):
        copyfile(baseDir+'/default_tos.txt',baseDir+'/accounts/tos.txt')
    if os.path.isfile(baseDir+'/img/login-background.png'):
        if not os.path.isfile(baseDir+'/accounts/login-background.png'):
            copyfile(baseDir+'/img/login-background.png',baseDir+'/accounts/login-background.png')

    TOSText='Terms of Service go here.'
    if os.path.isfile(baseDir+'/accounts/tos.txt'):
        with open(baseDir+'/accounts/tos.txt', 'r') as file:
            TOSText = file.read()    

    TOSForm=''
    cssFilename=baseDir+'/epicyon-profile.css'
    if os.path.isfile(baseDir+'/epicyon.css'):
        cssFilename=baseDir+'/epicyon.css'        
    with open(cssFilename, 'r') as cssFile:
        termsCSS = cssFile.read()
            
        TOSForm=htmlHeader(cssFilename,termsCSS)
        TOSForm+='<div class="container">'+TOSText+'</div>'
        if adminNickname:
            adminActor=httpPrefix+'://'+domainFull+'/users/'+adminNickname
            TOSForm+='<div class="container"><center><p class="administeredby">Administered by <a href="'+adminActor+'">'+adminNickname+'</a></p></center></div>'
        TOSForm+=htmlFooter()
    return TOSForm

def htmlAbout(baseDir: str,httpPrefix: str,domainFull: str) -> str:
    """Show the about screen
    """
    adminNickname = getConfigParam(baseDir,'admin')
    if not os.path.isfile(baseDir+'/accounts/about.txt'):
        copyfile(baseDir+'/default_about.txt',baseDir+'/accounts/about.txt')
    if os.path.isfile(baseDir+'/img/login-background.png'):
        if not os.path.isfile(baseDir+'/accounts/login-background.png'):
            copyfile(baseDir+'/img/login-background.png',baseDir+'/accounts/login-background.png')

    aboutText='Information about this instance goes here.'
    if os.path.isfile(baseDir+'/accounts/about.txt'):
        with open(baseDir+'/accounts/about.txt', 'r') as file:
            aboutText = file.read()    

    aboutForm=''
    cssFilename=baseDir+'/epicyon-profile.css'
    if os.path.isfile(baseDir+'/epicyon.css'):
        cssFilename=baseDir+'/epicyon.css'        
    with open(cssFilename, 'r') as cssFile:
        termsCSS = cssFile.read()
            
        aboutForm=htmlHeader(cssFilename,termsCSS)
        aboutForm+='<div class="container">'+aboutText+'</div>'
        if adminNickname:
            adminActor=httpPrefix+'://'+domainFull+'/users/'+adminNickname
            aboutForm+='<div class="container"><center><p class="administeredby">Administered by <a href="'+adminActor+'">'+adminNickname+'</a></p></center></div>'
        aboutForm+=htmlFooter()
    return aboutForm

def htmlHashtagBlocked(baseDir: str) -> str:
    """Show the screen for a blocked hashtag
    """
    blockedHashtagForm=''
    cssFilename=baseDir+'/epicyon-suspended.css'
    if os.path.isfile(baseDir+'/suspended.css'):
        cssFilename=baseDir+'/suspended.css'
    with open(cssFilename, 'r') as cssFile:
        blockedHashtagCSS=cssFile.read()            
        blockedHashtagForm=htmlHeader(cssFilename,blockedHashtagCSS)
        blockedHashtagForm+='<div><center>'
        blockedHashtagForm+='  <p class="screentitle">Hashtag Blocked</p>'
        blockedHashtagForm+='  <p>See <a href="/terms">Terms of Service</a></p>'
        blockedHashtagForm+='</center></div>'
        blockedHashtagForm+=htmlFooter()
    return blockedHashtagForm
    
def htmlSuspended(baseDir: str) -> str:
    """Show the screen for suspended accounts
    """
    suspendedForm=''
    cssFilename=baseDir+'/epicyon-suspended.css'
    if os.path.isfile(baseDir+'/suspended.css'):
        cssFilename=baseDir+'/suspended.css'
    with open(cssFilename, 'r') as cssFile:
        suspendedCSS=cssFile.read()            
        suspendedForm=htmlHeader(cssFilename,suspendedCSS)
        suspendedForm+='<div><center>'
        suspendedForm+='  <p class="screentitle">Account Suspended</p>'
        suspendedForm+='  <p>See <a href="/terms">Terms of Service</a></p>'
        suspendedForm+='</center></div>'
        suspendedForm+=htmlFooter()
    return suspendedForm

def htmlNewPost(translate: {},baseDir: str, \
                path: str,inReplyTo: str, \
                mentions: [], \
                reportUrl: str,pageNumber: int) -> str:
    """New post screen
    """    
    replyStr=''
    if not path.endswith('/newshare'):
        if not path.endswith('/newreport'):
            if not inReplyTo:
                newPostText='<p class="new-post-text">'+translate['Write your post text below.']+'</p>'
            else:
                newPostText='<p class="new-post-text">'+translate['Write your reply to']+' <a href="'+inReplyTo+'">'+translate['this post']+'</a></p>'
                replyStr='<input type="hidden" name="replyTo" value="'+inReplyTo+'">'
        else:
            newPostText= \
                '<p class="new-post-text">'+translate['Write your report below.']+'</p>'

            # custom report header with any additional instructions
            if os.path.isfile(baseDir+'/accounts/report.txt'):
                with open(baseDir+'/accounts/report.txt', 'r') as file:
                    customReportText=file.read()
                    if '</p>' not in customReportText:
                        customReportText='<p class="login-subtext">'+customReportText+'</p>'
                        customReportText=customReportText.replace('<p>','<p class="login-subtext">')
                        newPostText+=customReportText

            newPostText+='<p class="new-post-subtext">'+translate['This message only goes to moderators, even if it mentions other fediverse addresses.']+'</p><p class="new-post-subtext">'+translate['Also see']+' <a href="/terms">'+translate['Terms of Service']+'</a></p>'
    else:
        newPostText='<p class="new-post-text">'+translate['Enter the details for your shared item below.']+'</p>'
        
    if os.path.isfile(baseDir+'/accounts/newpost.txt'):
        with open(baseDir+'/accounts/newpost.txt', 'r') as file:
            newPostText = '<p class="new-post-text">'+file.read()+'</p>'    

    cssFilename=baseDir+'/epicyon-profile.css'
    if os.path.isfile(baseDir+'/epicyon.css'):
        cssFilename=baseDir+'/epicyon.css'        
    with open(cssFilename, 'r') as cssFile:
        newPostCSS = cssFile.read()

    if '?' in path:
        path=path.split('?')[0]
    pathBase=path.replace('/newreport','').replace('/newpost','').replace('/newshare','').replace('/newunlisted','').replace('/newfollowers','').replace('/newdm','')

    scopeIcon='scope_public.png'
    scopeDescription=translate['Public']
    placeholderSubject=translate['Subject or Content Warning (optional)']+'...'
    placeholderMessage=translate['Write something']+'...'
    extraFields=''
    endpoint='newpost'
    if path.endswith('/newunlisted'):
        scopeIcon='scope_unlisted.png'
        scopeDescription=translate['Unlisted']
        endpoint='newunlisted'
    if path.endswith('/newfollowers'):
        scopeIcon='scope_followers.png'
        scopeDescription=translate['Followers']
        endpoint='newfollowers'
    if path.endswith('/newdm'):
        scopeIcon='scope_dm.png'
        scopeDescription=translate['DM']
        endpoint='newdm'
    if path.endswith('/newreport'):
        scopeIcon='scope_report.png'
        scopeDescription=translate['Report']
        endpoint='newreport'
    if path.endswith('/newshare'):
        scopeIcon='scope_share.png'
        scopeDescription=translate['Shared Item']
        placeholderSubject=translate['Name of the shared item']+'...'
        placeholderMessage=translate['Description of the item being shared']+'...'
        endpoint='newshare'
        extraFields= \
            '<div class="container">' \
            '  <input type="text" class="itemType" placeholder="'+translate['Type of shared item. eg. hat']+'" name="itemType">' \
            '  <input type="text" class="category" placeholder="'+translate['Category of shared item. eg. clothing']+'" name="category">' \
            '  <label class="labels">'+translate['Duration of listing in days']+':</label> <input type="number" name="duration" min="1" max="365" step="1" value="14">' \
            '</div>' \
            '<input type="text" placeholder="'+translate['City or location of the shared item']+'" name="location">'

    newPostForm=htmlHeader(cssFilename,newPostCSS)

    # only show the share option if this is not a reply
    shareOptionOnDropdown=''
    if not replyStr:
        shareOptionOnDropdown='<a href="'+pathBase+'/newshare"><img src="/icons/scope_share.png"/><b>Share</b><br>'+translate['Describe a shared item']+'</a>'

    mentionsStr=''
    for m in mentions:
        mentionNickname=getNicknameFromActor(m)
        if not mentionNickname:
            continue
        mentionDomain,mentionPort=getDomainFromActor(m)
        if not mentionDomain:
            continue
        if mentionPort:            
            mentionsStr+='@'+mentionNickname+'@'+mentionDomain+':'+str(mentionPort)+' '
        else:
            mentionsStr+='@'+mentionNickname+'@'+mentionDomain+' '

    # build suffixes so that any replies or mentions are preserved when switching between scopes
    dropdownNewPostSuffix='/newpost'
    dropdownUnlistedSuffix='/newunlisted'
    dropdownFollowersSuffix='/newfollowers'
    dropdownDMSuffix='/newdm'    
    dropdownReportSuffix='/newreport'    
    if inReplyTo or mentions:
        dropdownNewPostSuffix=''
        dropdownUnlistedSuffix=''
        dropdownFollowersSuffix=''
        dropdownDMSuffix=''        
        dropdownReportSuffix=''
    if inReplyTo:
        dropdownNewPostSuffix+='?replyto='+inReplyTo
        dropdownUnlistedSuffix+='?replyto='+inReplyTo
        dropdownFollowersSuffix+='?replyfollowers='+inReplyTo
        dropdownDMSuffix+='?replydm='+inReplyTo
    for mentionedActor in mentions:
        dropdownNewPostSuffix+='?mention='+mentionedActor
        dropdownUnlistedSuffix+='?mention='+mentionedActor
        dropdownFollowersSuffix+='?mention='+mentionedActor
        dropdownDMSuffix+='?mention='+mentionedActor
        dropdownReportSuffix+='?mention='+mentionedActor
        
    dropDownContent=''
    if not reportUrl:
        dropDownContent= \
            '        <div id="myDropdown" class="dropdown-content">' \
            '          <a href="'+pathBase+dropdownNewPostSuffix+'"><img src="/icons/scope_public.png"/><b>'+translate['Public']+'</b><br>'+translate['Visible to anyone']+'</a>' \
            '          <a href="'+pathBase+dropdownUnlistedSuffix+'"><img src="/icons/scope_unlisted.png"/><b>'+translate['Unlisted']+'</b><br>'+translate['Not on public timeline']+'</a>' \
            '          <a href="'+pathBase+dropdownFollowersSuffix+'"><img src="/icons/scope_followers.png"/><b>'+translate['Followers']+'</b><br>'+translate['Only to followers']+'</a>' \
            '          <a href="'+pathBase+dropdownDMSuffix+'"><img src="/icons/scope_dm.png"/><b>'+translate['DM']+'</b><br>'+translate['Only to mentioned people']+'</a>' \
            '          <a href="'+pathBase+dropdownReportSuffix+'"><img src="/icons/scope_report.png"/><b>'+translate['Report']+'</b><br>'+translate['Send to moderators']+'</a>'+ \
            shareOptionOnDropdown+ \
            '        </div>'
    else:
        mentionsStr='Re: '+reportUrl+'\n\n'+mentionsStr
        
    newPostForm+= \
        '<form enctype="multipart/form-data" method="POST" action="'+path+'?'+endpoint+'?page='+str(pageNumber)+'">' \
        '  <div class="vertical-center">' \
        '    <label for="nickname"><b>'+newPostText+'</b></label>' \
        '    <div class="container">' \
        '      <div class="dropbtn" onclick="dropdown()">' \
        '        <img src="/icons/'+scopeIcon+'"/><b class="scope-desc">'+scopeDescription+'</b>'+ \
        dropDownContent+ \
        '      </div>' \
        '      <input type="submit" name="submitPost" value="'+translate['Submit']+'">' \
        '      <a href="'+pathBase+'/inbox"><button class="cancelbtn">'+translate['Cancel']+'</button></a>' \
        '      <a href="'+pathBase+'/searchemoji"><img class="emojisearch" src="/emoji/1F601.png" title="'+translate['Search for emoji']+'" alt="'+translate['Search for emoji']+'"/></a>'+ \
        '    </div>'+ \
        replyStr+ \
        '    <input type="text" placeholder="'+placeholderSubject+'" name="subject">' \
        '' \
        '    <textarea id="message" name="message" placeholder="'+placeholderMessage+'" style="height:400px" autofocus>'+mentionsStr+'</textarea>' \
        ''+extraFields+ \
        '    <div class="container">' \
        '      <input type="text" placeholder="'+translate['Image description']+'" name="imageDescription">' \
        '      <input type="file" id="attachpic" name="attachpic"' \
        '            accept=".png, .jpg, .jpeg, .gif, .mp4, .webm, .ogv, .mp3, .ogg">' \
        '    </div>' \
        '  </div>' \
        '</form>'

    if not reportUrl:
        newPostForm+='<script>'+clickToDropDownScript()+'</script>'

    newPostForm+=htmlFooter()
    return newPostForm

def htmlHeader(cssFilename: str,css=None,refreshSec=0,lang='en') -> str:
    if refreshSec==0:
        meta='  <meta charset="utf-8">\n'
    else:
        meta='  <meta http-equiv="Refresh" content="'+str(refreshSec)+'" charset="utf-8">\n'

    if not css:
        if '/' in cssFilename:
            cssFilename=cssFilename.split('/')[-1]
        htmlStr= \
            '<!DOCTYPE html>\n' \
            '<html lang="'+lang+'">\n'+ \
            meta+ \
            '  <style>\n' \
            '    @import url("'+cssFilename+'");\n'+ \
            '    background-color: #282c37' \
            '  </style>\n' \
            '  <body>\n'
    else:
        htmlStr= \
            '<!DOCTYPE html>\n' \
            '<html lang="'+lang+'">\n'+ \
            meta+ \
            '  <style>\n'+css+'</style>\n' \
            '  <body>\n'        
    return htmlStr

def htmlFooter() -> str:
    htmlStr= \
        '  </body>\n' \
        '</html>\n'
    return htmlStr

def htmlProfilePosts(translate: {}, \
                     baseDir: str,httpPrefix: str, \
                     authorized: bool,ocapAlways: bool, \
                     nickname: str,domain: str,port: int, \
                     session,wfRequest: {},personCache: {}, \
                     projectVersion: str) -> str:
    """Shows posts on the profile screen
    These should only be public posts
    """
    profileStr=''
    maxItems=4
    profileStr+='<script>'+contentWarningScript()+'</script>'
    ctr=0
    currPage=1
    while ctr<maxItems and currPage<4:
        outboxFeed= \
            personBoxJson(baseDir,domain, \
                          port,'/users/'+nickname+'/outbox?page='+str(currPage), \
                          httpPrefix, \
                          10, 'outbox', \
                          authorized, \
                          ocapAlways)
        if not outboxFeed:
            break
        if len(outboxFeed['orderedItems'])==0:
            break
        for item in outboxFeed['orderedItems']:
            if item['type']=='Create':
                postStr=individualPostAsHtml(translate,None, \
                                             baseDir,session,wfRequest,personCache, \
                                             nickname,domain,port,item,None,True,False, \
                                             httpPrefix,projectVersion, \
                                             False,False,False,True)
                if postStr:
                    profileStr+=postStr
                    ctr+=1
                    if ctr>=maxItems:
                        break
        currPage+=1
    return profileStr

def htmlProfileFollowing(translate: {},baseDir: str,httpPrefix: str, \
                         authorized: bool,ocapAlways: bool, \
                         nickname: str,domain: str,port: int, \
                         session,wfRequest: {},personCache: {}, \
                         followingJson: {},projectVersion: str, \
                         buttons: [], \
                         feedName: str,actor: str, \
                         pageNumber: int, \
                         maxItemsPerPage: int) -> str:
    """Shows following on the profile screen
    """
    profileStr=''

    if authorized and pageNumber:
        if authorized and pageNumber>1:
            # page up arrow
            profileStr+= \
                '<center><a href="'+actor+'/'+feedName+'?page='+str(pageNumber-1)+'"><img class="pageicon" src="/icons/pageup.png" title="'+translate['Page up']+'" alt="'+translate['Page up']+'"></a></center>'
        
    for item in followingJson['orderedItems']:
        profileStr+= \
            individualFollowAsHtml(translate,baseDir,session, \
                                   wfRequest,personCache, \
                                   domain,item,authorized,nickname, \
                                   httpPrefix,projectVersion, \
                                   buttons)
    if authorized and maxItemsPerPage and pageNumber:
        if len(followingJson['orderedItems'])>=maxItemsPerPage:
            # page down arrow
            profileStr+= \
                '<center><a href="'+actor+'/'+feedName+'?page='+str(pageNumber+1)+'"><img class="pageicon" src="/icons/pagedown.png" title="'+translate['Page down']+'" alt="'+translate['Page down']+'"></a></center>'
    return profileStr

def htmlProfileRoles(translate: {},nickname: str,domain: str,rolesJson: {}) -> str:
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

def htmlProfileSkills(translate: {},nickname: str,domain: str,skillsJson: {}) -> str:
    """Shows skills on the profile screen
    """
    profileStr=''
    for skill,level in skillsJson.items():
        profileStr+='<div>'+skill+'<br><div id="myProgress"><div id="myBar" style="width:'+str(level)+'%"></div></div></div><br>'
    if len(profileStr)>0:
        profileStr='<center><div class="skill-title">'+profileStr+'</div></center>'
    return profileStr

def htmlProfileShares(translate: {},nickname: str,domain: str,sharesJson: {}) -> str:
    """Shows shares on the profile screen
    """
    profileStr=''
    for item in sharesJson['orderedItems']:
        profileStr+='<div class="container">'
        profileStr+='<p class="share-title">'+item['displayName']+'</p>'
        if item.get('imageUrl'):
            profileStr+='<a href="'+item['imageUrl']+'">'
            profileStr+='<img src="'+item['imageUrl']+'" alt="'+translate['Item image']+'"></a>'
        profileStr+='<p>'+item['summary']+'</p>'
        profileStr+='<p><b>'+translate['Type']+':</b> '+item['itemType']+' '
        profileStr+='<b>'+translate['Category']+':</b> '+item['category']+' '
        profileStr+='<b>'+translate['Location']+':</b> '+item['location']+'</p>'
        profileStr+='</div>'
    if len(profileStr)>0:
        profileStr='<div class="share-title">'+profileStr+'</div>'
    return profileStr

def htmlProfile(translate: {},projectVersion: str, \
                baseDir: str,httpPrefix: str,authorized: bool, \
                ocapAlways: bool,profileJson: {},selected: str, \
                session,wfRequest: {},personCache: {}, \
                extraJson=None, \
                pageNumber=None,maxItemsPerPage=None) -> str:
    """Show the profile page as html
    """
    nickname=profileJson['preferredUsername']
    if not nickname:
        return ""
    displayName=profileJson['name']
    domain,port=getDomainFromActor(profileJson['id'])
    if not domain:
        return ""
    domainFull=domain
    if port:
        domainFull=domain+':'+str(port)
    profileDescription=profileJson['summary']
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
    followApprovals=False
    linkToTimelineStart=''
    linkToTimelineEnd=''
    editProfileStr=''
    actor=profileJson['id']

    if not authorized:
        loginButton='<br><a href="/login"><button class="loginButton">'+translate['Login']+'</button></a>'
    else:
        editProfileStr='<a href="'+actor+'/editprofile"><button class="button"><span>'+translate['Edit']+' </span></button></a>'
        linkToTimelineStart='<a href="/users/'+nickname+'/inbox" title="'+translate['Switch to timeline view']+'" alt="'+translate['Switch to timeline view']+'">'
        linkToTimelineEnd='</a>'
        # are there any follow requests?
        followRequestsFilename=baseDir+'/accounts/'+nickname+'@'+domain+'/followrequests.txt'
        if os.path.isfile(followRequestsFilename):
            with open(followRequestsFilename,'r') as f:
                for line in f:
                    if len(line)>0:
                        followApprovals=True
                        followersButton='buttonhighlighted'
                        if selected=='followers':
                            followersButton='buttonselectedhighlighted'
                        break
        if selected=='followers':
            if followApprovals:
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
                            followApprovalsSection+='<button class="followApprove">'+translate['Approve']+'</button></a>'
                            followApprovalsSection+='<a href="'+basePath+'/followdeny='+followerHandle+'">'
                            followApprovalsSection+='<button class="followDeny">'+translate['Deny']+'</button></a>'
                            followApprovalsSection+='</div>'

    profileStr= \
        linkToTimelineStart+ \
        ' <div class="hero-image">' \
        '  <div class="hero-text">'+ \
        '    <img src="'+profileJson['icon']['url']+'" alt="'+nickname+'@'+domainFull+'">' \
        '    <h1>'+displayName+'</h1>' \
        '    <p><b>@'+nickname+'@'+domainFull+'</b></p>' \
        '    <p>'+profileDescription+'</p>'+ \
        loginButton+ \
        '  </div>' \
        '</div>'+ \
        linkToTimelineEnd+ \
        '<div class="container">\n' \
        '  <center>' \
        '    <a href="'+actor+'"><button class="'+postsButton+'"><span>'+translate['Posts']+' </span></button></a>' \
        '    <a href="'+actor+'/following"><button class="'+followingButton+'"><span>'+translate['Following']+' </span></button></a>' \
        '    <a href="'+actor+'/followers"><button class="'+followersButton+'"><span>'+translate['Followers']+' </span></button></a>' \
        '    <a href="'+actor+'/roles"><button class="'+rolesButton+'"><span>'+translate['Roles']+' </span></button></a>' \
        '    <a href="'+actor+'/skills"><button class="'+skillsButton+'"><span>'+translate['Skills']+' </span></button></a>' \
        '    <a href="'+actor+'/shares"><button class="'+sharesButton+'"><span>'+translate['Shares']+' </span></button></a>'+ \
        editProfileStr+ \
        '  </center>' \
        '</div>'

    profileStr+=followApprovalsSection
    
    cssFilename=baseDir+'/epicyon-profile.css'
    if os.path.isfile(baseDir+'/epicyon.css'):
        cssFilename=baseDir+'/epicyon.css'        
    with open(cssFilename, 'r') as cssFile:
        profileStyle = cssFile.read().replace('image.png',actor+'/image.png')

        if selected=='posts':
            profileStr+= \
                htmlProfilePosts(translate, \
                                 baseDir,httpPrefix,authorized, \
                                 ocapAlways,nickname,domain,port, \
                                 session,wfRequest,personCache, \
                                 projectVersion)
        if selected=='following':
            profileStr+= \
                htmlProfileFollowing(translate,baseDir,httpPrefix, \
                                     authorized,ocapAlways,nickname, \
                                     domain,port,session, \
                                     wfRequest,personCache,extraJson, \
                                     projectVersion, \
                                     ["unfollow"], \
                                     selected,actor, \
                                     pageNumber,maxItemsPerPage)
        if selected=='followers':
            profileStr+= \
                htmlProfileFollowing(translate,baseDir,httpPrefix, \
                                     authorized,ocapAlways,nickname, \
                                     domain,port,session, \
                                     wfRequest,personCache,extraJson, \
                                     projectVersion, \
                                     ["block"], \
                                     selected,actor, \
                                     pageNumber,maxItemsPerPage)
        if selected=='roles':
            profileStr+= \
                htmlProfileRoles(translate,nickname,domainFull,extraJson)
        if selected=='skills':
            profileStr+= \
                htmlProfileSkills(translate,nickname,domainFull,extraJson)
        if selected=='shares':
            profileStr+= \
                htmlProfileShares(translate,nickname,domainFull,extraJson)
        profileStr=htmlHeader(cssFilename,profileStyle)+profileStr+htmlFooter()
    return profileStr

def individualFollowAsHtml(translate: {}, \
                           baseDir: str,session,wfRequest: {}, \
                           personCache: {},domain: str, \
                           followUrl: str, \
                           authorized: bool, \
                           actorNickname: str, \
                           httpPrefix: str, \
                           projectVersion: str, \
                           buttons=[]) -> str:
    nickname=getNicknameFromActor(followUrl)
    domain,port=getDomainFromActor(followUrl)
    titleStr='@'+nickname+'@'+domain
    avatarUrl=getPersonAvatarUrl(baseDir,followUrl,personCache)
    if not avatarUrl:
        avatarUrl=followUrl+'/avatar.png'
    if domain not in followUrl:
        inboxUrl,pubKeyId,pubKey,fromPersonId,sharedInbox,capabilityAcquisition,avatarUrl2,displayName = \
            getPersonBox(baseDir,session,wfRequest,personCache, \
                         projectVersion,httpPrefix,domain,'outbox')
        if avatarUrl2:
            avatarUrl=avatarUrl2
        if displayName:
            titleStr=displayName+' '+titleStr

    buttonsStr=''
    if authorized:
        for b in buttons:
            if b=='block':
                buttonsStr+='<a href="/users/'+actorNickname+'?block='+followUrl+';'+avatarUrl+'"><button class="buttonunfollow">'+translate['Block']+'</button></a>'
            if b=='unfollow':
                buttonsStr+='<a href="/users/'+actorNickname+'?unfollow='+followUrl+';'+avatarUrl+'"><button class="buttonunfollow">'+translate['Unfollow']+'</button></a>'

    return \
        '<div class="container">\n' \
        '<a href="'+followUrl+'">' \
        '<p><img src="'+avatarUrl+'" alt="Avatar">\n'+ \
        titleStr+'</a>'+buttonsStr+'</p>' \
        '</div>\n'

def clickToDropDownScript() -> str:
    """Function run onclick to create a dropdown
    """
    script= \
        'function dropdown() {' \
        '  document.getElementById("myDropdown").classList.toggle("show");' \
        '}'
        #'window.onclick = function(event) {' \
        #"  if (!event.target.matches('.dropbtn')) {" \
        #'    var dropdowns = document.getElementsByClassName("dropdown-content");' \
        #'    var i;' \
        #'    for (i = 0; i < dropdowns.length; i++) {' \
        #'      var openDropdown = dropdowns[i];' \
        #"      if (openDropdown.classList.contains('show')) {" \
        #"        openDropdown.classList.remove('show');" \
        #'      }' \
        #'    }' \
        #'  }' \
        #'}'
    return script

def contentWarningScript() -> str:
    """Returns a script used for content warnings
    """
    script= \
        'function showContentWarning(postID) {' \
        '  var x = document.getElementById(postID);' \
        '  if (x.style.display !== "block") {' \
        '    x.style.display = "block";' \
        '  } else {' \
        '    x.style.display = "none";' \
        '  }' \
        '}'
    return script

def htmlRemplaceEmojiFromTags(content: str,tag: {}) -> str:
    """Uses the tags to replace :emoji: with html image markup
    """
    for tagItem in tag:
        if not tagItem.get('type'):
            continue
        if tagItem['type']!='Emoji':
            continue
        if not tagItem.get('name'):
            continue
        if not tagItem.get('icon'):
            continue
        if not tagItem['icon'].get('url'):
            continue
        if tagItem['name'] not in content:
            continue
        emojiHtml="<img src=\""+tagItem['icon']['url']+"\" alt=\""+tagItem['name'].replace(':','')+"\" align=\"middle\" class=\"emoji\"/>"
        content=content.replace(tagItem['name'],emojiHtml)
    return content

def addEmbeddedAudio(translate: {},content: str) -> str:
    """Adds embedded audio for mp3/ogg
    """
    if not ('.mp3' in content or '.ogg' in content):
        return content

    if '<audio ' in content:
        return content

    extension='.mp3'
    if '.ogg' in content:
        extension='.ogg'

    words=content.strip('\n').split(' ')
    for w in words:
        if extension not in w:
            continue
        w=w.replace('href="','').replace('">','')
        if w.endswith('.'):
            w=w[:-1]
        if w.endswith('"'):
            w=w[:-1]
        if w.endswith(';'):
            w=w[:-1]
        if w.endswith(':'):
            w=w[:-1]
        if not w.endswith(extension):
            continue
            
        if not (w.startswith('http') or w.startswith('dat:') or '/' in w):
            continue
        url=w
        content+='<center><audio controls>'
        content+='<source src="'+url+'" type="audio/'+extension.replace('.','')+'">'
        content+=translate['Your browser does not support the audio element.']
        content+='</audio></center>'
    return content

def addEmbeddedVideo(translate: {},content: str,width=400,height=300) -> str:
    """Adds embedded video for mp4/webm/ogv
    """
    if not ('.mp4' in content or '.webm' in content or '.ogv' in content):
        return content

    if '<video ' in content:
        return content

    extension='.mp4'
    if '.webm' in content:
        extension='.webm'
    elif '.ogv' in content:
        extension='.ogv'

    words=content.strip('\n').split(' ')
    for w in words:
        if extension not in w:
            continue
        w=w.replace('href="','').replace('">','')
        if w.endswith('.'):
            w=w[:-1]
        if w.endswith('"'):
            w=w[:-1]
        if w.endswith(';'):
            w=w[:-1]
        if w.endswith(':'):
            w=w[:-1]
        if not w.endswith(extension):
            continue
        if not (w.startswith('http') or w.startswith('dat:') or '/' in w):
            continue
        url=w
        content+='<center><video width="'+str(width)+'" height="'+str(height)+'" controls>'
        content+='<source src="'+url+'" type="video/'+extension.replace('.','')+'">'
        content+=translate['Your browser does not support the video element.']
        content+='</video></center>'
    return content

def addEmbeddedVideoFromSites(translate: {},content: str,width=400,height=300) -> str:
    """Adds embedded videos
    """
    if '>vimeo.com/' in content:
        url=content.split('>vimeo.com/')[1]
        if '<' in url:
            url=url.split('<')[0]
            content=content+"<center><iframe src=\"https://player.vimeo.com/video/"+url+"\" width=\""+str(width)+"\" height=\""+str(height)+"\" frameborder=\"0\" allow=\"autoplay; fullscreen\" allowfullscreen></iframe></center>"
            return content

    videoSite='https://www.youtube.com'
    if '"'+videoSite in content:
        url=content.split('"'+videoSite)[1]
        if '"' in url:
            url=url.split('"')[0].replace('/watch?v=','/embed/')
            content=content+"<center><iframe src=\""+videoSite+url+"\" width=\""+str(width)+"\" height=\""+str(height)+"\" frameborder=\"0\" allow=\"autoplay; fullscreen\" allowfullscreen></iframe></center>"
            return content

    videoSite='https://media.ccc.de'
    if '"'+videoSite in content:
        url=content.split('"'+videoSite)[1]
        if '"' in url:
            url=url.split('"')[0]
            if not url.endswith('/oembed'):
                url=url+'/oembed'
            content=content+"<center><iframe src=\""+videoSite+url+"\" width=\""+str(width)+"\" height=\""+str(height)+"\" frameborder=\"0\" allow=\"fullscreen\" allowfullscreen></iframe></center>"
            return content

    # A selection of the current larger peertube sites, mostly French and German language
    # These have been chosen based on reported numbers of users and the content of each has not been reviewed, so mileage could vary
    peerTubeSites=['peertube.mastodon.host','open.tube','share.tube','tube.tr4sk.me','videos.elbinario.net','hkvideo.live','peertube.snargol.com','tube.22decembre.eu','tube.fabrigli.fr','libretube.net','libre.video','peertube.linuxrocks.online','spacepub.space','video.ploud.jp','video.omniatv.com','peertube.servebeer.com','tube.tchncs.de','tubee.fr','video.alternanet.fr','devtube.dev-wiki.de','video.samedi.pm','https://video.irem.univ-paris-diderot.fr','peertube.openstreetmap.fr','video.antopie.org','scitech.video','tube.4aem.com','video.ploud.fr','peervideo.net','video.valme.io','videos.pair2jeux.tube','vault.mle.party','hostyour.tv','diode.zone','visionon.tv','artitube.artifaille.fr','peertube.fr','peertube.live','tube.ac-lyon.fr','www.yiny.org','betamax.video','tube.piweb.be','pe.ertu.be','peertube.social','videos.lescommuns.org','peertube.nogafa.org','skeptikon.fr','video.tedomum.net','tube.p2p.legal','sikke.fi','exode.me','peertube.video']
    for site in peerTubeSites:
        if '"https://'+site in content:
            url=content.split('"https://'+site)[1]
            if '"' in url:
                url=url.split('"')[0].replace('/watch/','/embed/')            
                content=content+"<center><iframe sandbox=\"allow-same-origin allow-scripts\" src=\"https://"+site+url+"\" width=\""+str(width)+"\" height=\""+str(height)+"\" frameborder=\"0\" allow=\"autoplay; fullscreen\" allowfullscreen></iframe></center>"
                return content
    return content

def addEmbeddedElements(translate: {},content: str) -> str:
    """Adds embedded elements for various media types
    """
    content=addEmbeddedVideoFromSites(translate,content)
    content=addEmbeddedAudio(translate,content)
    return addEmbeddedVideo(translate,content)

def followerApprovalActive(baseDir: str,nickname: str,domain: str) -> bool:
    """Returns true if the given account requires follower approval
    """
    manuallyApprovesFollowers=False
    actorFilename=baseDir+'/accounts/'+nickname+'@'+domain+'.json'
    if os.path.isfile(actorFilename):
        with open(actorFilename, 'r') as fp:
            actorJson=commentjson.load(fp)
            if actorJson.get('manuallyApprovesFollowers'):
                manuallyApprovesFollowers=actorJson['manuallyApprovesFollowers']
    return manuallyApprovesFollowers

def insertQuestion(translate: {}, \
                   nickname: str,content: str, \
                   postJsonObject: {},pageNumber: int) -> str:
    """ Inserts question selection into a post
    """
    if not isQuestion(postJsonObject):
        return content
    if len(postJsonObject['object']['oneOf'])==0:
        return content
    pageNumberStr=''
    if pageNumber:
        pageNumberStr='?page='+str(pageNumber)
    content+='<div class="question">'
    content+='<form method="POST" action="/users/'+nickname+'/question'+pageNumberStr+'">'
    content+='<input type="hidden" name="messageId" value="'+postJsonObject['id']+'"><br>'
    for choice in postJsonObject['object']['oneOf']:
        if not choice.get('type'):
            continue
        if not choice.get('name'):
            continue
        content+='<input type="radio" name="answer" value="'+choice['name']+'"> '+choice['name']+'<br><br>'
    content+='<input type="submit" value="'+translate['Vote']+'" class="vote"><br><br>'
    content+='</form></div>'
    return content

def rejectAnnounce(announceFilename: str):
    """Marks an announce as rejected
    """
    if not os.path.isfile(announceFilename+'.reject'):
        rejectAnnounceFile=open(announceFilename+'.reject', "w+")
        rejectAnnounceFile.write('\n')
        rejectAnnounceFile.close()

def individualPostAsHtml(translate: {}, \
                         pageNumber: int,baseDir: str, \
                         session,wfRequest: {},personCache: {}, \
                         nickname: str,domain: str,port: int, \
                         postJsonObject: {}, \
                         avatarUrl: str, showAvatarDropdown: bool,
                         allowDeletion: bool, \
                         httpPrefix: str, projectVersion: str, \
                         showRepeats=True, \
                         showIcons=False, \
                         manuallyApprovesFollowers=False, \
                         showPublicOnly=False) -> str:
    """ Shows a single post as html
    """
    # If this is the inbox timeline then don't show the repeat icon on any DMs
    showRepeatIcon=showRepeats
    showDMicon=False
    if showRepeats:
        if isDM(postJsonObject):
            showRepeatIcon=False
            showDMicon=True
    
    titleStr=''
    isAnnounced=False
    if postJsonObject['type']=='Announce':
        if postJsonObject.get('object'):
            if isinstance(postJsonObject['object'], str):
                # get the announced post
                announceCacheDir=baseDir+'/cache/announce/'+nickname
                if not os.path.isdir(announceCacheDir):
                    os.mkdir(announceCacheDir)
                announceFilename=announceCacheDir+'/'+postJsonObject['object'].replace('/','#')+'.json'
                print('announceFilename: '+announceFilename)
                if not os.path.isfile(announceFilename+'.reject'):
                    if os.path.isfile(announceFilename):
                        print('Reading cached Announce content for '+postJsonObject['object'])
                        with open(announceFilename, 'r') as fp:
                            postJsonObject=commentjson.load(fp)
                            isAnnounced=True
                    else:
                        print('Downloading Announce content for '+postJsonObject['object'])
                        asHeader={'Accept': 'application/activity+json; profile="https://www.w3.org/ns/activitystreams"'}
                        actorNickname=getNicknameFromActor(postJsonObject['actor'])
                        actorDomain,actorPort=getDomainFromActor(postJsonObject['actor'])
                        announcedJson=getJson(session,postJsonObject['object'],asHeader,None,projectVersion,httpPrefix,domain)
                        if announcedJson:
                            if not announcedJson.get('id'):
                                rejectAnnounce(announceFilename)
                                pprint(announcedJson)
                                return ''
                            if '/statuses/' not in announcedJson['id']:
                                rejectAnnounce(announceFilename)
                                return ''
                            if '/users/' not in announcedJson['id'] and '/profile/' not in announcedJson['id']:
                                rejectAnnounce(announceFilename)
                                return ''
                            if not announcedJson.get('type'):
                                rejectAnnounce(announceFilename)
                                pprint(announcedJson)
                                return ''
                            if announcedJson['type']!='Note':
                                rejectAnnounce(announceFilename)
                                pprint(announcedJson)
                                return ''
                            # wrap in create to be consistent with other posts
                            announcedJson= \
                                outboxMessageCreateWrap(httpPrefix, \
                                                        actorNickname,actorDomain,actorPort, \
                                                        announcedJson)
                            if announcedJson['type']!='Create':
                                rejectAnnounce(announceFilename)
                                pprint(announcedJson)
                                return ''
                            # set the id to the original status
                            announcedJson['id']=postJsonObject['object']
                            announcedJson['object']['id']=postJsonObject['object']
                            # check that the repeat isn't for a blocked account
                            attributedNickname=getNicknameFromActor(announcedJson['object']['id'])
                            attributedDomain,attributedPort=getDomainFromActor(announcedJson['object']['id'])
                            if attributedNickname and attributedDomain:
                                if attributedPort:
                                    if attributedPort!=80 and attributedPort!=443:
                                        attributedDomain=attributedDomain+':'+str(attributedPort)
                                if isBlocked(baseDir,nickname,domain,attributedNickname,attributedDomain):
                                    rejectAnnounce(announceFilename)
                                    return ''                                        
                            postJsonObject=announcedJson
                            with open(announceFilename, 'w') as fp:
                                commentjson.dump(postJsonObject, fp, indent=4, sort_keys=False)
                                isAnnounced=True
                        else:
                            return ''
                else:
                    return ''
            else:
                return ''
    if not isinstance(postJsonObject['object'], dict):
        return ''

    # if this post should be public then check its recipients
    if showPublicOnly:
        if postJsonObject['object'].get('to'):
            containsPublic=False
            for toAddress in postJsonObject['object']['to']:
                if toAddress.endswith('#Public'):
                    containsPublic=True
                    break
            if not containsPublic:
                if postJsonObject['object'].get('cc'):
                    for toAddress in postJsonObject['object']['cc']:
                        if toAddress.endswith('#Public'):
                            containsPublic=True
                            break
            if not containsPublic:
                return ''
        
    isModerationPost=False
    if postJsonObject['object'].get('moderationStatus'):
        isModerationPost=True
    avatarPosition=''
    containerClass='container'
    containerClassIcons='containericons'
    timeClass='time-right'
    actorNickname=getNicknameFromActor(postJsonObject['actor'])
    actorDomain,actorPort=getDomainFromActor(postJsonObject['actor'])
    messageId=''
    if postJsonObject.get('id'):
        messageId=postJsonObject['id'].replace('/activity','')

    displayName=getDisplayName(postJsonObject['actor'],personCache)
    if displayName:
        titleStr+='<a href="'+messageId+'">'+displayName+'</a>'
    else:
        titleStr+='<a href="'+messageId+'">@'+actorNickname+'@'+actorDomain+'</a>'

    # Show a DM icon for DMs in the inbox timeline
    if showDMicon:
        titleStr=titleStr+' <img src="/icons/dm.png" class="DMicon"/>'

    if showRepeatIcon:
        if isAnnounced:
            if postJsonObject['object'].get('attributedTo'):
                announceNickname=getNicknameFromActor(postJsonObject['object']['attributedTo'])
                if announceNickname:
                    announceDomain,announcePort=getDomainFromActor(postJsonObject['object']['attributedTo'])
                    announceDisplayName=getDisplayName(postJsonObject['object']['attributedTo'],personCache)
                    if announceDisplayName:
                        titleStr+=' <img src="/icons/repeat_inactive.png" class="announceOrReply"/> <a href="'+postJsonObject['object']['id']+'">'+announceDisplayName+'</a>'
                    else:
                        titleStr+=' <img src="/icons/repeat_inactive.png" class="announceOrReply"/> <a href="'+postJsonObject['object']['id']+'">@'+announceNickname+'@'+announceDomain+'</a>'
                else:
                    titleStr+=' <img src="/icons/repeat_inactive.png" class="announceOrReply"/> <a href="'+postJsonObject['object']['id']+'">@unattributed</a>'
            else:
                titleStr+=' <img src="/icons/repeat_inactive.png" class="announceOrReply"/> <a href="'+postJsonObject['object']['id']+'">@unattributed</a>'
        else:
            if postJsonObject['object'].get('inReplyTo'):
                containerClassIcons='containericons darker'
                containerClass='container darker'
                #avatarPosition=' class="right"'
                if '/statuses/' in postJsonObject['object']['inReplyTo']:
                    replyNickname=getNicknameFromActor(postJsonObject['object']['inReplyTo'])
                    if replyNickname:
                        replyDomain,replyPort=getDomainFromActor(postJsonObject['object']['inReplyTo'])
                        if replyNickname and replyDomain:
                            replyDisplayName=getDisplayName(postJsonObject['object']['inReplyTo'],personCache)
                            if replyDisplayName:
                                titleStr+=' <img src="/icons/reply.png" class="announceOrReply"/> <a href="'+postJsonObject['object']['inReplyTo']+'">'+replyDisplayName+'</a>'
                            else:
                                titleStr+=' <img src="/icons/reply.png" class="announceOrReply"/> <a href="'+postJsonObject['object']['inReplyTo']+'">@'+replyNickname+'@'+replyDomain+'</a>'
                    else:
                        titleStr+=' <img src="/icons/reply.png" class="announceOrReply"/> <a href="'+postJsonObject['object']['inReplyTo']+'">@unknown</a>'
                else:
                    postDomain=postJsonObject['object']['inReplyTo'].replace('https://','').replace('http://','').replace('dat://','')
                    if '/' in postDomain:
                        postDomain=postDomain.split('/',1)[0]
                    if postDomain:
                        titleStr+=' <img src="/icons/reply.png" class="announceOrReply"/> <a href="'+postJsonObject['object']['inReplyTo']+'">'+postDomain+'</a>'
    attachmentStr=''
    if postJsonObject['object'].get('attachment'):
        if isinstance(postJsonObject['object']['attachment'], list):
            attachmentCtr=0
            attachmentStr+='<div class="media">'
            for attach in postJsonObject['object']['attachment']:
                if attach.get('mediaType') and attach.get('url'):
                    mediaType=attach['mediaType']
                    imageDescription=''
                    if attach.get('name'):
                        imageDescription=attach['name'].replace('"',"'")
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
                    elif mediaType=='video/mp4' or \
                         mediaType=='video/webm' or \
                         mediaType=='video/ogv':
                        extension='.mp4'
                        if attach['url'].endswith('.webm'):
                            extension='.webm'
                        elif attach['url'].endswith('.ogv'):
                            extension='.ogv'
                        if attach['url'].endswith(extension):
                            if attachmentCtr>0:
                                attachmentStr+='<br>'
                            attachmentStr+= \
                                '<center><video width="400" height="300" controls>' \
                                '<source src="'+attach['url']+'" alt="'+imageDescription+'" title="'+imageDescription+'" class="attachment" type="video/'+extension.replace('.','')+'">'+ \
                                translate['Your browser does not support the video tag.']+ \
                                '</video></center>'
                            attachmentCtr+=1
                    elif mediaType=='audio/mpeg' or \
                         mediaType=='audio/ogg':
                        extension='.mp3'
                        if attach['url'].endswith('.ogg'):
                            extension='.ogg'                            
                        if attach['url'].endswith(extension):
                            if attachmentCtr>0:
                                attachmentStr+='<br>'
                            attachmentStr+= \
                                '<center><audio controls>' \
                                '<source src="'+attach['url']+'" alt="'+imageDescription+'" title="'+imageDescription+'" class="attachment" type="audio/'+extension.replace('.','')+'">'+ \
                                translate['Your browser does not support the audio tag.']+ \
                                '</audio></center>'
                            attachmentCtr+=1
            attachmentStr+='</div>'

    if not avatarUrl:
        avatarUrl=getPersonAvatarUrl(baseDir,postJsonObject['actor'],personCache)
    if not avatarUrl:
        avatarUrl=postJsonObject['actor']+'/avatar.png'

    fullDomain=domain
    if port:
        if port!=80 and port!=443:
            if ':' not in domain:
                fullDomain=domain+':'+str(port)
        
    if fullDomain not in postJsonObject['actor']:
        inboxUrl,pubKeyId,pubKey,fromPersonId,sharedInbox,capabilityAcquisition,avatarUrl2,displayName = \
            getPersonBox(baseDir,session,wfRequest,personCache, \
                         projectVersion,httpPrefix,domain,'outbox')
        if avatarUrl2:
            avatarUrl=avatarUrl2
        if displayName:
            titleStr=displayName+' '+titleStr

    avatarImageInPost= \
        '  <div class="timeline-avatar">' \
        '    <a href="'+postJsonObject['actor']+'">' \
        '    <img src="'+avatarUrl+'" title="'+translate['Show profile']+'" alt="Avatar"'+avatarPosition+'/></a>' \
        '  </div>'

    messageIdStr=''
    if messageId:
        messageIdStr=';'+messageId
    
    if showAvatarDropdown and fullDomain+'/users/'+nickname not in postJsonObject['actor']:
        avatarImageInPost= \
            '  <div class="timeline-avatar">' \
            '    <a href="/users/'+nickname+'?options='+postJsonObject['actor']+';'+str(pageNumber)+';'+avatarUrl+messageIdStr+'">' \
            '    <img title="'+translate['Show options for this person']+'" src="'+avatarUrl+'" '+avatarPosition+'/></a>' \
            '  </div>'

    publishedStr=postJsonObject['object']['published']
    if '.' not in publishedStr:
        if '+' not in publishedStr:
            datetimeObject = datetime.strptime(publishedStr,"%Y-%m-%dT%H:%M:%SZ")
        else:
            datetimeObject = datetime.strptime(publishedStr.split('+')[0]+'Z',"%Y-%m-%dT%H:%M:%SZ")
    else:
        publishedStr=publishedStr.replace('T',' ').split('.')[0]
        datetimeObject = parse(publishedStr)
    publishedStr=datetimeObject.strftime("%a %b %d, %H:%M")
    footerStr='<span class="'+timeClass+'">'+publishedStr+'</span>\n'

    pageNumberParam=''
    if pageNumber:
        pageNumberParam='?page='+str(pageNumber)

    announceStr=''
    if not isModerationPost and showRepeatIcon:
        # don't allow announce/repeat of your own posts
        announceIcon='repeat_inactive.png'
        announceLink='repeat'
        announceTitle=translate['Repeat this post']
        if announcedByPerson(postJsonObject,nickname,fullDomain):
            announceIcon='repeat.png'
            announceLink='unrepeat'
            announceTitle=translate['Undo the repeat']
        announceStr= \
            '<a href="/users/'+nickname+'?'+announceLink+'='+postJsonObject['object']['id']+pageNumberParam+'" title="'+announceTitle+'">' \
            '<img src="/icons/'+announceIcon+'"/></a>'

    likeStr=''
    if not isModerationPost:
        likeIcon='like_inactive.png'
        likeLink='like'
        likeTitle=translate['Like this post']
        if noOfLikes(postJsonObject)>0:
            likeIcon='like.png'
            likeLink='unlike'
            likeTitle=translate['Undo the like']
        likeStr= \
            '<a href="/users/'+nickname+'?'+likeLink+'='+postJsonObject['object']['id']+pageNumberParam+'" title="'+likeTitle+'">' \
            '<img src="/icons/'+likeIcon+'"/></a>'

    deleteStr=''
    if allowDeletion or \
       ('/'+fullDomain+'/' in postJsonObject['actor'] and \
        postJsonObject['object']['id'].startswith(postJsonObject['actor'])):
        if '/users/'+nickname+'/' in postJsonObject['object']['id']:
            deleteStr= \
                '<a href="/users/'+nickname+'?delete='+postJsonObject['object']['id']+pageNumberParam+'" title="'+translate['Delete this post']+'">' \
                '<img src="/icons/delete.png"/></a>'

    # change the background color for DMs in inbox timeline
    if showDMicon:
        containerClassIcons='containericons dm'
        containerClass='container dm'

    if showIcons:
        replyToLink=postJsonObject['object']['id']
        if postJsonObject['object'].get('attributedTo'):
            replyToLink+='?mention='+postJsonObject['object']['attributedTo']
        if postJsonObject['object'].get('content'):
            mentionedActors=getMentionsFromHtml(postJsonObject['object']['content'])
            if mentionedActors:
                for actorUrl in mentionedActors:
                    if '?mention='+actorUrl not in replyToLink:
                        replyToLink+='?mention='+actorUrl
                        if len(replyToLink)>500:
                            break
        replyToLink+=pageNumberParam
                        
        footerStr='<div class="'+containerClassIcons+'">'
        if not isModerationPost and showRepeatIcon:
            if not manuallyApprovesFollowers:
                footerStr+='<a href="/users/'+nickname+'?replyto='+replyToLink+'" title="'+translate['Reply to this post']+'">'
            else:
                footerStr+='<a href="/users/'+nickname+'?replyfollowers='+replyToLink+'" title="'+translate['Reply to this post']+'">'
        else:
            footerStr+='<a href="/users/'+nickname+'?replydm='+replyToLink+'" title="'+translate['Reply to this post']+'">'
        footerStr+='<img src="/icons/reply.png"/></a>'
        footerStr+=announceStr+likeStr+deleteStr
        footerStr+='<span class="'+timeClass+'">'+publishedStr+'</span>'
        footerStr+='</div>'

    if not postJsonObject['object']['sensitive']:
        contentStr=postJsonObject['object']['content']+attachmentStr
        contentStr=addEmbeddedElements(translate,contentStr)
        contentStr=insertQuestion(translate,nickname,contentStr,postJsonObject,pageNumber)
    else:
        postID='post'+str(createPassword(8))
        contentStr=''
        if postJsonObject['object'].get('summary'):
            contentStr+='<b>'+postJsonObject['object']['summary']+'</b> '
            if isModerationPost:
                containerClass='container report'
        else:
            contentStr+='<b>Sensitive</b> '
        contentStr+='<button class="cwButton" onclick="showContentWarning('+"'"+postID+"'"+')">'+translate['SHOW MORE']+'</button>'
        contentStr+='<div class="cwText" id="'+postID+'">'
        contentStr+=postJsonObject['object']['content']+attachmentStr
        contentStr=addEmbeddedElements(translate,contentStr)
        contentStr=insertQuestion(translate,nickname,contentStr,postJsonObject,pageNumber)
        contentStr+='</div>'

    if postJsonObject['object'].get('tag'):
        contentStr=htmlRemplaceEmojiFromTags(contentStr,postJsonObject['object']['tag'])

    contentStr='<div class="message">'+contentStr+'</div>'

    return \
        '<div class="'+containerClass+'">\n'+ \
        avatarImageInPost+ \
        '<p class="post-title">'+titleStr+'</p>'+ \
        contentStr+footerStr+ \
        '</div>\n'

def isQuestion(postObjectJson: {}) -> bool:
    """ is the given post a question?
    """
    if postObjectJson['type']=='Create':
        if isinstance(postObjectJson['object'], dict):
            if postObjectJson['object'].get('type'):
                if postObjectJson['object']['type']=='Question':
                    if postObjectJson['object'].get('oneOf'):
                        if isinstance(postObjectJson['object']['oneOf'], list):
                            return True
    return False 

def htmlTimeline(translate: {},pageNumber: int, \
                 itemsPerPage: int,session,baseDir: str, \
                 wfRequest: {},personCache: {}, \
                 nickname: str,domain: str,port: int,timelineJson: {}, \
                 boxName: str,allowDeletion: bool, \
                 httpPrefix: str,projectVersion: str, \
                 manuallyApproveFollowers: bool) -> str:
    """Show the timeline as html
    """
    cssFilename=baseDir+'/epicyon-profile.css'
    if os.path.isfile(baseDir+'/epicyon.css'):
        cssFilename=baseDir+'/epicyon.css'        
    with open(cssFilename, 'r') as cssFile:
        profileStyle = \
            cssFile.read().replace('banner.png', \
                                   '/users/'+nickname+'/banner.png')

    moderator=isModerator(baseDir,nickname)

    inboxButton='button'
    dmButton='button'
    sentButton='button'
    moderationButton='button'
    if boxName=='inbox':
        inboxButton='buttonselected'
    elif boxName=='dm':
        dmButton='buttonselected'
    elif boxName=='outbox':
        sentButton='buttonselected'
    elif boxName=='moderation':
        moderationButton='buttonselected'
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
                    followApprovals='<a href="'+actor+'/followers"><img class="right" alt="'+translate['Approve follow requests']+'" title="'+translate['Approve follow requests']+'" src="/icons/person.png"/></a>'
                    break

    moderationButtonStr=''
    if moderator:
        moderationButtonStr='<a href="'+actor+'/moderation"><button class="'+moderationButton+'"><span>'+translate['Mod']+' </span></button></a>'

    tlStr=htmlHeader(cssFilename,profileStyle)
    #if (boxName=='inbox' or boxName=='dm') and pageNumber==1:
        # refresh if on the first page of the inbox and dm timeline
        #tlStr=htmlHeader(cssFilename,profileStyle,240)

    if boxName!='dm':
        if not manuallyApproveFollowers:
            newPostButtonStr='<a href="'+actor+'/newpost"><img src="/icons/newpost.png" title="'+translate['Create a new post']+'" alt="'+translate['Create a new post']+'" class="right"/></a>'
        else:
            newPostButtonStr='<a href="'+actor+'/newfollowers"><img src="/icons/newpost.png" title="'+translate['Create a new post']+'" alt="'+translate['Create a new post']+'" class="right"/></a>'
    else:
        newPostButtonStr='<a href="'+actor+'/newdm"><img src="/icons/newpost.png" title="'+translate['Create a new DM']+'" alt="'+translate['Create a new DM']+'" class="right"/></a>'

    # banner and row of buttons
    tlStr+= \
        '<a href="/users/'+nickname+'" title="'+translate['Switch to profile view']+'" alt="'+translate['Switch to profile view']+'">' \
        '<div class="timeline-banner">' \
        '</div></a>' \
        '<div class="container">\n'+ \
        '    <a href="'+actor+'/inbox"><button class="'+inboxButton+'"><span>'+translate['Inbox']+'</span></button></a>' \
        '    <a href="'+actor+'/dm"><button class="'+dmButton+'"><span>'+translate['DM']+'</span></button></a>' \
        '    <a href="'+actor+'/outbox"><button class="'+sentButton+'"><span>'+translate['Outbox']+'</span></button></a>'+ \
        moderationButtonStr+newPostButtonStr+ \
        '    <a href="'+actor+'/search"><img src="/icons/search.png" title="'+translate['Search and follow']+'" alt="'+translate['Search and follow']+'" class="right"/></a>'+ \
        '    <a href="'+actor+'/'+boxName+'"><img src="/icons/refresh.png" title="'+translate['Refresh']+'" alt="'+translate['Refresh']+'" class="right"/></a>'+ \
        followApprovals+ \
        '</div>'

    # second row of buttons for moderator actions
    if moderator and boxName=='moderation':
        tlStr+= \
            '<form method="POST" action="/users/'+nickname+'/moderationaction">' \
            '<div class="container">\n'+ \
            '    <input type="text" placeholder="'+translate['Nickname or URL. Block using *@domain or nickname@domain']+'" name="moderationAction" value="">' \
            '    <input type="submit" title="'+translate['Remove the above item']+'" name="submitRemove" value="'+translate['Remove']+'">' \
            '    <input type="submit" title="'+translate['Suspend the above account nickname']+'" name="submitSuspend" value="'+translate['Suspend']+'">' \
            '    <input type="submit" title="'+translate['Remove a suspension for an account nickname']+'" name="submitUnsuspend" value="'+translate['Unsuspend']+'">' \
            '    <input type="submit" title="'+translate['Block an account on another instance']+'" name="submitBlock" value="'+translate['Block']+'">' \
            '    <input type="submit" title="'+translate['Unblock an account on another instance']+'" name="submitUnblock" value="'+translate['Unblock']+'">' \
            '    <input type="submit" title="'+translate['Information about current blocks/suspensions']+'" name="submitInfo" value="'+translate['Info']+'">' \
            '</div></form>'

    # add the javascript for content warnings
    tlStr+='<script>'+contentWarningScript()+clickToDropDownScript()+'</script>'

    # page up arrow
    if pageNumber>1:
        tlStr+='<center><a href="'+actor+'/'+boxName+'?page='+str(pageNumber-1)+'"><img class="pageicon" src="/icons/pageup.png" title="'+translate['Page up']+'" alt="'+translate['Page up']+'"></a></center>'

    # show the posts
    itemCtr=0
    for item in timelineJson['orderedItems']:
        if item['type']=='Create' or item['type']=='Announce':
            itemCtr+=1
            avatarUrl=getPersonAvatarUrl(baseDir,item['actor'],personCache)
            tlStr+= \
                individualPostAsHtml(translate,pageNumber, \
                                     baseDir,session,wfRequest,personCache, \
                                     nickname,domain,port,item,avatarUrl,True, \
                                     allowDeletion, \
                                     httpPrefix,projectVersion, \
                                     boxName!='dm', \
                                     showIndividualPostIcons, \
                                     manuallyApproveFollowers,False)

    # page down arrow
    if itemCtr>=itemsPerPage:
        tlStr+='<center><a href="'+actor+'/'+boxName+'?page='+str(pageNumber+1)+'"><img class="pageicon" src="/icons/pagedown.png" title="'+translate['Page down']+'" alt="'+translate['Page down']+'"></a></center>'
    tlStr+=htmlFooter()
    return tlStr

def htmlInbox(translate: {},pageNumber: int,itemsPerPage: int, \
              session,baseDir: str,wfRequest: {},personCache: {}, \
              nickname: str,domain: str,port: int,inboxJson: {}, \
              allowDeletion: bool, \
              httpPrefix: str,projectVersion: str) -> str:
    """Show the inbox as html
    """
    manuallyApproveFollowers= \
        followerApprovalActive(baseDir,nickname,domain)

    return htmlTimeline(translate,pageNumber, \
                        itemsPerPage,session,baseDir,wfRequest,personCache, \
                        nickname,domain,port,inboxJson,'inbox',allowDeletion, \
                        httpPrefix,projectVersion,manuallyApproveFollowers)

def htmlInboxDMs(translate: {},pageNumber: int,itemsPerPage: int, \
                 session,baseDir: str,wfRequest: {},personCache: {}, \
                 nickname: str,domain: str,port: int,inboxJson: {}, \
                 allowDeletion: bool, \
                 httpPrefix: str,projectVersion: str) -> str:
    """Show the DM timeline as html
    """
    return htmlTimeline(translate,pageNumber, \
                        itemsPerPage,session,baseDir,wfRequest,personCache, \
                        nickname,domain,port,inboxJson,'dm',allowDeletion, \
                        httpPrefix,projectVersion,False)

def htmlModeration(translate: {},pageNumber: int,itemsPerPage: int, \
                   session,baseDir: str,wfRequest: {},personCache: {}, \
                   nickname: str,domain: str,port: int,inboxJson: {}, \
                   allowDeletion: bool, \
                   httpPrefix: str,projectVersion: str) -> str:
    """Show the moderation feed as html
    """
    return htmlTimeline(translate,pageNumber, \
                        itemsPerPage,session,baseDir,wfRequest,personCache, \
                        nickname,domain,port,inboxJson,'moderation',allowDeletion, \
                        httpPrefix,projectVersion,True)

def htmlOutbox(translate: {},pageNumber: int,itemsPerPage: int, \
               session,baseDir: str,wfRequest: {},personCache: {}, \
               nickname: str,domain: str,port: int,outboxJson: {}, \
               allowDeletion: bool,
               httpPrefix: str,projectVersion: str) -> str:
    """Show the Outbox as html
    """
    manuallyApproveFollowers= \
        followerApprovalActive(baseDir,nickname,domain)
    return htmlTimeline(translate,pageNumber, \
                        itemsPerPage,session,baseDir,wfRequest,personCache, \
                        nickname,domain,port,outboxJson,'outbox',allowDeletion, \
                        httpPrefix,projectVersion,manuallyApproveFollowers)

def htmlIndividualPost(translate: {}, \
                       baseDir: str,session,wfRequest: {},personCache: {}, \
                       nickname: str,domain: str,port: int,authorized: bool, \
                       postJsonObject: {},httpPrefix: str,projectVersion: str) -> str:
    """Show an individual post as html
    """
    postStr='<script>'+contentWarningScript()+'</script>'    
    postStr+= \
        individualPostAsHtml(translate,None,baseDir,session,wfRequest,personCache, \
                             nickname,domain,port,postJsonObject,None,True,False, \
                             httpPrefix,projectVersion,False,authorized,False,False)
    messageId=postJsonObject['id'].replace('/activity','')

    # show the previous posts
    while postJsonObject['object'].get('inReplyTo'):
        postFilename=locatePost(baseDir,nickname,domain,postJsonObject['object']['inReplyTo'])
        if not postFilename:
            break
        with open(postFilename, 'r') as fp:
            postJsonObject=commentjson.load(fp)
            postStr= \
                individualPostAsHtml(translate,None, \
                                     baseDir,session,wfRequest,personCache, \
                                     nickname,domain,port,postJsonObject, \
                                     None,True,False, \
                                     httpPrefix,projectVersion, \
                                     False,authorized,False,False)+postStr

    # show the following posts
    postFilename=locatePost(baseDir,nickname,domain,messageId)
    if postFilename:
        # is there a replies file for this post?
        repliesFilename=postFilename.replace('.json','.replies')
        if os.path.isfile(repliesFilename):
            # get items from the replies file
            repliesJson={'orderedItems': []}
            populateRepliesJson(baseDir,nickname,domain,repliesFilename,authorized,repliesJson)
            # add items to the html output
            for item in repliesJson['orderedItems']:
                postStr+= \
                    individualPostAsHtml(translate,None, \
                                         baseDir,session,wfRequest,personCache, \
                                         nickname,domain,port,item,None,True,False, \
                                         httpPrefix,projectVersion, \
                                         False,authorized,False,False)
    cssFilename=baseDir+'/epicyon-profile.css'
    return htmlHeader(cssFilename)+postStr+htmlFooter()

def htmlPostReplies(translate: {},baseDir: str, \
                    session,wfRequest: {},personCache: {}, \
                    nickname: str,domain: str,port: int,repliesJson: {}, \
                    httpPrefix: str,projectVersion: str) -> str:
    """Show the replies to an individual post as html
    """
    repliesStr=''
    if repliesJson.get('orderedItems'):
        for item in repliesJson['orderedItems']:
            repliesStr+= \
                individualPostAsHtml(translate,None, \
                                     baseDir,session,wfRequest,personCache, \
                                     nickname,domain,port,item,None,True,False, \
                                     httpPrefix,projectVersion, \
                                     False,False,False,False)

    cssFilename=baseDir+'/epicyon-profile.css'
    return htmlHeader(cssFilename)+repliesStr+htmlFooter()

def htmlRemoveSharedItem(translate: {},baseDir: str,actor: str,shareName: str) -> str:
    """Shows a screen asking to confirm the removal of a shared item
    """
    nickname=getNicknameFromActor(actor)
    domain,port=getDomainFromActor(actor)
    sharesFile=baseDir+'/accounts/'+nickname+'@'+domain+'/shares.json'
    if not os.path.isfile(sharesFile):
        return None
    sharesJson=None
    with open(sharesFile, 'r') as fp:
        sharesJson=commentjson.load(fp)
    if not sharesJson:
        return None
    if not sharesJson.get(shareName):
        return None
    sharedItemDisplayName=sharesJson[shareName]['displayName']
    sharedItemImageUrl=None
    if sharesJson[shareName].get('imageUrl'):
        sharedItemImageUrl=sharesJson[shareName]['imageUrl']

    if os.path.isfile(baseDir+'/img/shares-background.png'):
        if not os.path.isfile(baseDir+'/accounts/shares-background.png'):
            copyfile(baseDir+'/img/shares-background.png',baseDir+'/accounts/shares-background.png')

    cssFilename=baseDir+'/epicyon-follow.css'
    if os.path.isfile(baseDir+'/follow.css'):
        cssFilename=baseDir+'/follow.css'        
    with open(cssFilename, 'r') as cssFile:
        profileStyle = cssFile.read()
    sharesStr=htmlHeader(cssFilename,profileStyle)
    sharesStr+='<div class="follow">'
    sharesStr+='  <div class="followAvatar">'
    sharesStr+='  <center>'
    if sharedItemImageUrl:
        sharesStr+='  <img src="'+sharedItemImageUrl+'"/>'
    sharesStr+='  <p class="followText">'+translate['Remove']+' '+sharedItemDisplayName+' ?</p>'
    sharesStr+= \
        '  <form method="POST" action="'+actor+'/rmshare">' \
        '    <input type="hidden" name="actor" value="'+actor+'">' \
        '    <input type="hidden" name="shareName" value="'+shareName+'">' \
        '    <button type="submit" class="button" name="submitYes">'+translate['Yes']+'</button>' \
        '    <a href="'+actor+'/inbox'+'"><button class="button">'+translate['No']+'</button></a>' \
        '  </form>'
    sharesStr+='  </center>'
    sharesStr+='  </div>'
    sharesStr+='</div>'
    sharesStr+=htmlFooter()
    return sharesStr

def htmlDeletePost(translate,pageNumber: int, \
                   session,baseDir: str,messageId: str, \
                   httpPrefix: str,projectVersion: str, \
                   wfRequest: {},personCache: {}) -> str:
    """Shows a screen asking to confirm the deletion of a post
    """
    if '/statuses/' not in messageId:
        return None

    actor=messageId.split('/statuses/')[0]
    nickname=getNicknameFromActor(actor)
    domain,port=getDomainFromActor(actor)

    postFilename=locatePost(baseDir,nickname,domain,messageId)
    if not postFilename:
        return None
    with open(postFilename, 'r') as fp:
        postJsonObject=commentjson.load(fp)

    if os.path.isfile(baseDir+'/img/delete-background.png'):
        if not os.path.isfile(baseDir+'/accounts/delete-background.png'):
            copyfile(baseDir+'/img/delete-background.png', \
                     baseDir+'/accounts/delete-background.png')

    deletePostStr=None
    cssFilename=baseDir+'/epicyon-profile.css'
    if os.path.isfile(baseDir+'/epicyon.css'):
        cssFilename=baseDir+'/epicyon.css'        
    with open(cssFilename, 'r') as cssFile:
        profileStyle = cssFile.read()
        deletePostStr=htmlHeader(cssFilename,profileStyle)
        deletePostStr+='<script>'+contentWarningScript()+'</script>'
        deletePostStr+= \
            individualPostAsHtml(translate,pageNumber, \
                                 baseDir,session,wfRequest,personCache, \
                                 nickname,domain,port,postJsonObject, \
                                 None,True,False, \
                                 httpPrefix,projectVersion, \
                                 False,False,False,False)
        deletePostStr+='<center>'
        deletePostStr+='  <p class="followText">'+translate['Delete this post?']+'</p>'
        deletePostStr+= \
            '  <form method="POST" action="'+actor+'/rmpost">' \
            '    <input type="hidden" name="pageNumber" value="'+str(pageNumber)+'">' \
            '    <input type="hidden" name="messageId" value="'+messageId+'">' \
            '    <button type="submit" class="button" name="submitYes">'+translate['Yes']+'</button>' \
            '    <a href="'+actor+'/inbox'+'"><button class="button">'+translate['No']+'</button></a>' \
            '  </form>'
        deletePostStr+='</center>'
        deletePostStr+=htmlFooter()
    return deletePostStr

def htmlFollowConfirm(translate: {},baseDir: str, \
                      originPathStr: str, \
                      followActor: str, \
                      followProfileUrl: str) -> str:
    """Asks to confirm a follow
    """
    followDomain,port=getDomainFromActor(followActor)
    
    if os.path.isfile(baseDir+'/img/follow-background.png'):
        if not os.path.isfile(baseDir+'/accounts/follow-background.png'):
            copyfile(baseDir+'/img/follow-background.png',baseDir+'/accounts/follow-background.png')

    cssFilename=baseDir+'/epicyon-follow.css'
    if os.path.isfile(baseDir+'/follow.css'):
        cssFilename=baseDir+'/follow.css'        
    with open(cssFilename, 'r') as cssFile:
        profileStyle = cssFile.read()
    followStr=htmlHeader(cssFilename,profileStyle)
    followStr+='<div class="follow">'
    followStr+='  <div class="followAvatar">'
    followStr+='  <center>'
    followStr+='  <a href="'+followActor+'">'
    followStr+='  <img src="'+followProfileUrl+'"/></a>'
    followStr+='  <p class="followText">'+translate['Follow']+' '+getNicknameFromActor(followActor)+'@'+followDomain+' ?</p>'
    followStr+= \
        '  <form method="POST" action="'+originPathStr+'/followconfirm">' \
        '    <input type="hidden" name="actor" value="'+followActor+'">' \
        '    <button type="submit" class="button" name="submitYes">'+translate['Yes']+'</button>' \
        '    <a href="'+originPathStr+'"><button class="button">'+translate['No']+'</button></a>' \
        '  </form>'
    followStr+='</center>'
    followStr+='</div>'
    followStr+='</div>'
    followStr+=htmlFooter()
    return followStr

def htmlUnfollowConfirm(translate: {},baseDir: str, \
                        originPathStr: str, \
                        followActor: str, \
                        followProfileUrl: str) -> str:
    """Asks to confirm unfollowing an actor
    """
    followDomain,port=getDomainFromActor(followActor)
    
    if os.path.isfile(baseDir+'/img/follow-background.png'):
        if not os.path.isfile(baseDir+'/accounts/follow-background.png'):
            copyfile(baseDir+'/img/follow-background.png',baseDir+'/accounts/follow-background.png')

    cssFilename=baseDir+'/epicyon-follow.css'
    if os.path.isfile(baseDir+'/follow.css'):
        cssFilename=baseDir+'/follow.css'        
    with open(cssFilename, 'r') as cssFile:
        profileStyle = cssFile.read()
    followStr=htmlHeader(cssFilename,profileStyle)
    followStr+='<div class="follow">'
    followStr+='  <div class="followAvatar">'
    followStr+='  <center>'
    followStr+='  <a href="'+followActor+'">'
    followStr+='  <img src="'+followProfileUrl+'"/></a>'
    followStr+='  <p class="followText">'+translate['Stop following']+' '+getNicknameFromActor(followActor)+'@'+followDomain+' ?</p>'
    followStr+= \
        '  <form method="POST" action="'+originPathStr+'/unfollowconfirm">' \
        '    <input type="hidden" name="actor" value="'+followActor+'">' \
        '    <button type="submit" class="button" name="submitYes">'+translate['Yes']+'</button>' \
        '    <a href="'+originPathStr+'"><button class="button">'+translate['No']+'</button></a>' \
        '  </form>'
    followStr+='</center>'
    followStr+='</div>'
    followStr+='</div>'
    followStr+=htmlFooter()
    return followStr

def htmlPersonOptions(translate: {},baseDir: str, \
                      domain: str,originPathStr: str, \
                      optionsActor: str, \
                      optionsProfileUrl: str, \
                      optionsLink: str, \
                      pageNumber: int) -> str:
    """Show options for a person: view/follow/block/report
    """
    optionsDomain,optionsPort=getDomainFromActor(optionsActor)
    
    if os.path.isfile(baseDir+'/img/options-background.png'):
        if not os.path.isfile(baseDir+'/accounts/options-background.png'):
            copyfile(baseDir+'/img/options-background.png',baseDir+'/accounts/options-background.png')

    followStr='Follow'
    blockStr='Block'
    if originPathStr.startswith('/users/'):
        nickname=originPathStr.split('/users/')[1]
        if '/' in nickname:
            nickname=nickname.split('/')[0]
        if '?' in nickname:
            nickname=nickname.split('?')[0]
        followerDomain,followerPort=getDomainFromActor(optionsActor)
        if isFollowingActor(baseDir,nickname,domain,optionsActor):
            followStr='Unfollow'

        optionsNickname=getNicknameFromActor(optionsActor)
        optionsDomainFull=optionsDomain
        if optionsPort:
            if optionsPort!=80 and optionsPort!=443:
                optionsDomainFull=optionsDomain+':'+str(optionsPort)
        if isBlocked(baseDir,nickname,domain,optionsNickname,optionsDomainFull):
            blockStr='Block'

    optionsLinkStr=''
    if optionsLink:
        optionsLinkStr='    <input type="hidden" name="postUrl" value="'+optionsLink+'">'
    cssFilename=baseDir+'/epicyon-follow.css'
    if os.path.isfile(baseDir+'/follow.css'):
        cssFilename=baseDir+'/follow.css'        
    with open(cssFilename, 'r') as cssFile:
        profileStyle = cssFile.read()
    optionsStr=htmlHeader(cssFilename,profileStyle)
    optionsStr+='<div class="options">'
    optionsStr+='  <div class="optionsAvatar">'
    optionsStr+='  <center>'
    optionsStr+='  <a href="'+optionsActor+'">'
    optionsStr+='  <img src="'+optionsProfileUrl+'"/></a>'
    optionsStr+='  <p class="optionsText">'+translate['Options for']+' @'+getNicknameFromActor(optionsActor)+'@'+optionsDomain+'</p>'
    optionsStr+= \
        '  <form method="POST" action="'+originPathStr+'/personoptions">' \
        '    <input type="hidden" name="pageNumber" value="'+str(pageNumber)+'">' \
        '    <input type="hidden" name="actor" value="'+optionsActor+'">' \
        '    <input type="hidden" name="avatarUrl" value="'+optionsProfileUrl+'">'+ \
        optionsLinkStr+ \
        '    <button type="submit" class="button" name="submitView">'+translate['View']+'</button>' \
        '    <button type="submit" class="button" name="submit'+followStr+'">'+translate[followStr]+'</button>' \
        '    <button type="submit" class="button" name="submit'+blockStr+'">'+translate[blockStr]+'</button>' \
        '    <button type="submit" class="button" name="submitDM">'+translate['DM']+'</button>' \
        '    <button type="submit" class="button" name="submitReport">'+translate['Report']+'</button>' \
        '  </form>'
    optionsStr+='</center>'
    optionsStr+='</div>'
    optionsStr+='</div>'
    optionsStr+=htmlFooter()
    return optionsStr

#def htmlBlockConfirm(translate: {},baseDir: str, \
#                     originPathStr: str, \
#                     blockActor: str, \
#                     blockProfileUrl: str) -> str:
#    """Asks to confirm a block
#    """
#    blockDomain,port=getDomainFromActor(blockActor)
#    
#    if os.path.isfile(baseDir+'/img/block-background.png'):
#        if not os.path.isfile(baseDir+'/accounts/block-background.png'):
#            copyfile(baseDir+'/img/block-background.png',baseDir+'/accounts/block-background.png')
#
#    with open(baseDir+'/epicyon-follow.css', 'r') as cssFile:
#        profileStyle = cssFile.read()
#    blockStr=htmlHeader(cssFilename,profileStyle)
#    blockStr+='<div class="block">'
#    blockStr+='  <div class="blockAvatar">'
#    blockStr+='  <center>'
#    blockStr+='  <a href="'+blockActor+'">'
#    blockStr+='  <img src="'+blockProfileUrl+'"/></a>'
#    blockStr+='  <p class="blockText">'+translate['Block']+' '+getNicknameFromActor(blockActor)+'@'+blockDomain+' ?</p>'
#    blockStr+= \
#        '  <form method="POST" action="'+originPathStr+'/blockconfirm">' \
#        '    <input type="hidden" name="actor" value="'+blockActor+'">' \
#        '    <button type="submit" class="button" name="submitYes">'+translate['Yes']+'</button>' \
#        '    <a href="'+originPathStr+'"><button class="button">'+translate['No']+'</button></a>' \
#        '  </form>'
#    blockStr+='</center>'
#    blockStr+='</div>'
#    blockStr+='</div>'
#    blockStr+=htmlFooter()
#    return blockStr

def htmlUnblockConfirm(translate: {},baseDir: str, \
                       originPathStr: str, \
                       blockActor: str, \
                       blockProfileUrl: str) -> str:
    """Asks to confirm unblocking an actor
    """
    blockDomain,port=getDomainFromActor(blockActor)
    
    if os.path.isfile(baseDir+'/img/block-background.png'):
        if not os.path.isfile(baseDir+'/accounts/block-background.png'):
            copyfile(baseDir+'/img/block-background.png',baseDir+'/accounts/block-background.png')

    cssFilename=baseDir+'/epicyon-follow.css'
    if os.path.isfile(baseDir+'/follow.css'):
        cssFilename=baseDir+'/follow.css'        
    with open(cssFilename, 'r') as cssFile:
        profileStyle = cssFile.read()
    blockStr=htmlHeader(cssFilename,profileStyle)
    blockStr+='<div class="block">'
    blockStr+='  <div class="blockAvatar">'
    blockStr+='  <center>'
    blockStr+='  <a href="'+blockActor+'">'
    blockStr+='  <img src="'+blockProfileUrl+'"/></a>'
    blockStr+='  <p class="blockText">'+translate['Stop blocking']+' '+getNicknameFromActor(blockActor)+'@'+blockDomain+' ?</p>'
    blockStr+= \
        '  <form method="POST" action="'+originPathStr+'/unblockconfirm">' \
        '    <input type="hidden" name="actor" value="'+blockActor+'">' \
        '    <button type="submit" class="button" name="submitYes">'+translate['Yes']+'</button>' \
        '    <a href="'+originPathStr+'"><button class="button">'+translate['No']+'</button></a>' \
        '  </form>'
    blockStr+='</center>'
    blockStr+='</div>'
    blockStr+='</div>'
    blockStr+=htmlFooter()
    return blockStr

def htmlSearchEmojiTextEntry(translate: {}, \
                             baseDir: str,path: str) -> str:
    """Search for an emoji by name
    """
    if not os.path.isfile(baseDir+'/emoji/emoji.json'):
        copyfile(baseDir+'/emoji/default_emoji.json',baseDir+'/emoji/emoji.json')

    actor=path.replace('/search','')
    nickname=getNicknameFromActor(actor)
    domain,port=getDomainFromActor(actor)
    
    if os.path.isfile(baseDir+'/img/search-background.png'):
        if not os.path.isfile(baseDir+'/accounts/search-background.png'):
            copyfile(baseDir+'/img/search-background.png',baseDir+'/accounts/search-background.png')

    cssFilename=baseDir+'/epicyon-follow.css'
    if os.path.isfile(baseDir+'/follow.css'):
        cssFilename=baseDir+'/follow.css'        
    with open(cssFilename, 'r') as cssFile:
        profileStyle = cssFile.read()
    emojiStr=htmlHeader(cssFilename,profileStyle)
    emojiStr+='<div class="follow">'
    emojiStr+='  <div class="followAvatar">'
    emojiStr+='  <center>'    
    emojiStr+='  <p class="followText">'+translate['Enter an emoji name to search for']+'</p>'
    emojiStr+= \
        '  <form method="POST" action="'+actor+'/searchhandleemoji">' \
        '    <input type="hidden" name="actor" value="'+actor+'">' \
        '    <input type="text" name="searchtext" autofocus><br>' \
        '    <button type="submit" class="button" name="submitSearch">'+translate['Submit']+'</button>' \
        '  </form>'
    emojiStr+='  </center>'
    emojiStr+='  </div>'
    emojiStr+='</div>'
    emojiStr+=htmlFooter()
    return emojiStr

def htmlSearch(translate: {}, \
               baseDir: str,path: str) -> str:
    """Search called from the timeline icon
    """
    actor=path.replace('/search','')
    nickname=getNicknameFromActor(actor)
    domain,port=getDomainFromActor(actor)
    
    if os.path.isfile(baseDir+'/img/search-background.png'):
        if not os.path.isfile(baseDir+'/accounts/search-background.png'):
            copyfile(baseDir+'/img/search-background.png',baseDir+'/accounts/search-background.png')

    cssFilename=baseDir+'/epicyon-follow.css'
    if os.path.isfile(baseDir+'/follow.css'):
        cssFilename=baseDir+'/follow.css'        
    with open(cssFilename, 'r') as cssFile:
        profileStyle = cssFile.read()
    followStr=htmlHeader(cssFilename,profileStyle)
    followStr+='<div class="follow">'
    followStr+='  <div class="followAvatar">'
    followStr+='  <center>'    
    followStr+='  <p class="followText">'+translate['Enter an address, shared item, #hashtag, *skill or :emoji: to search for']+'</p>'
    followStr+= \
        '  <form method="POST" action="'+actor+'/searchhandle">' \
        '    <input type="hidden" name="actor" value="'+actor+'">' \
        '    <input type="text" name="searchtext" autofocus><br>' \
        '    <button type="submit" class="button" name="submitSearch">'+translate['Submit']+'</button>' \
        '  </form>'
    followStr+='  </center>'
    followStr+='  </div>'
    followStr+='</div>'
    followStr+=htmlFooter()
    return followStr

def htmlProfileAfterSearch(translate: {}, \
                           baseDir: str,path: str,httpPrefix: str, \
                           nickname: str,domain: str,port: int, \
                           profileHandle: str, \
                           session,wfRequest: {},personCache: {},
                           debug: bool,projectVersion: str) -> str:
    """Show a profile page after a search for a fediverse address
    """
    if '/users/' in profileHandle or '/@' in profileHandle:
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
            if ':' not in searchDomain:
                searchDomainFull=searchDomain+':'+str(searchPort)
    
    profileStr=''
    cssFilename=baseDir+'/epicyon-profile.css'
    if os.path.isfile(baseDir+'/epicyon.css'):
        cssFilename=baseDir+'/epicyon.css'        
    with open(cssFilename, 'r') as cssFile:
        wf = webfingerHandle(session,searchNickname+'@'+searchDomainFull,httpPrefix,wfRequest, \
                             domain,projectVersion)
        if not wf:
            if debug:
                print('DEBUG: Unable to webfinger '+searchNickname+'@'+searchDomainFull)
            return None
        asHeader = {'Accept': 'application/activity+json; profile="https://www.w3.org/ns/activitystreams"'}
        personUrl = getUserUrl(wf)
        if not personUrl:
            if debug:
                print('DEBUG: Webfinger did not return an actor url')
            return None            
        profileJson = getJson(session,personUrl,asHeader,None,projectVersion,httpPrefix,domain)
        if not profileJson:
            if debug:
                print('DEBUG: No actor returned from '+personUrl)
            return None
        avatarUrl=''
        if profileJson.get('icon'):
            if profileJson['icon'].get('url'):
                avatarUrl=profileJson['icon']['url']
        if not avatarUrl:
            avatarUrl=getPersonAvatarUrl(baseDir,personUrl,personCache)
        displayName=searchNickname
        if profileJson.get('name'):
            displayName=profileJson['name']
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
            '    <h1>'+displayName+'</h1>' \
            '    <p><b>@'+searchNickname+'@'+searchDomainFull+'</b></p>' \
            '    <p>'+profileDescription+'</p>'+ \
            '  </div>' \
            '</div>'+ \
            '<div class="container">\n' \
            '  <form method="POST" action="'+backUrl+'/followconfirm">' \
            '    <center>' \
            '      <input type="hidden" name="actor" value="'+personUrl+'">' \
            '      <button type="submit" class="button" name="submitYes">'+translate['Follow']+'</button>' \
            '      <a href="'+backUrl+'"><button class="button">'+translate['Go Back']+'</button></a>' \
            '    </center>' \
            '  </form>' \
            '</div>'

        profileStr+='<script>'+contentWarningScript()+'</script>'

        result = []
        i = 0
        for item in parseUserFeed(session,outboxUrl,asHeader, \
                                  projectVersion,httpPrefix,domain):
            if not item.get('type'):
                continue
            if item['type']!='Create' and item['type']!='Announce':
                continue
            if not item.get('object'):
                continue
            profileStr+= \
                individualPostAsHtml(translate,None,baseDir, \
                                     session,wfRequest,personCache, \
                                     nickname,domain,port, \
                                     item,avatarUrl,False,False, \
                                     httpPrefix,projectVersion, \
                                     False,False,False,False)
            i+=1
            if i>=20:
                break

    return htmlHeader(cssFilename,profileStyle)+profileStr+htmlFooter()
