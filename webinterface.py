__filename__ = "webinterface.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import json
import time
import os
from collections import OrderedDict
from datetime import datetime
from datetime import date
from dateutil.parser import parse
from shutil import copyfile
from shutil import copyfileobj
from pprint import pprint
from person import personBoxJson
from person import isPersonSnoozed
from pgp import getEmailAddress
from pgp import getPGPpubKey
from xmpp import getXmppAddress
from matrix import getMatrixAddress
from donate import getDonationUrl
from utils import updateRecentPostsCache
from utils import getNicknameFromActor
from utils import getDomainFromActor
from utils import locatePost
from utils import noOfAccounts
from utils import isPublicPost
from utils import isPublicPostFromUrl
from utils import getDisplayName
from utils import getCachedPostDirectory
from utils import getCachedPostFilename
from utils import loadJson
from utils import saveJson
from follow import isFollowingActor
from webfinger import webfingerHandle
from posts import isDM
from posts import getPersonBox
from posts import getUserUrl
from posts import parseUserFeed
from posts import populateRepliesJson
from posts import isModerator
from posts import outboxMessageCreateWrap
from posts import downloadAnnounce
from session import getJson
from auth import createPassword
from like import likedByPerson
from like import noOfLikes
from bookmarks import bookmarkedByPerson
from announce import announcedByPerson
from blocking import isBlocked
from blocking import isBlockedHashtag
from content import getMentionsFromHtml
from content import addHtmlTags
from content import replaceEmojiFromTags
from content import removeLongWords
from config import getConfigParam
from skills import getSkills
from cache import getPersonFromCache
from cache import storePersonInCache
from shares import getValidSharedItemID

def updateAvatarImageCache(session,baseDir: str,httpPrefix: str,actor: str,avatarUrl: str,personCache: {},force=False) -> str:
    """Updates the cached avatar for the given actor
    """
    if not avatarUrl:
        return None
    avatarImagePath=baseDir+'/cache/avatars/'+actor.replace('/','-')
    if avatarUrl.endswith('.png') or '.png?' in avatarUrl:
        sessionHeaders = {'Accept': 'image/png'}
        avatarImageFilename=avatarImagePath+'.png'
    elif avatarUrl.endswith('.jpg') or avatarUrl.endswith('.jpeg') or \
         '.jpg?' in avatarUrl or '.jpeg?' in avatarUrl:
        sessionHeaders = {'Accept': 'image/jpeg'}
        avatarImageFilename=avatarImagePath+'.jpg'
    elif avatarUrl.endswith('.gif') or '.gif?' in avatarUrl:
        sessionHeaders = {'Accept': 'image/gif'}
        avatarImageFilename=avatarImagePath+'.gif'
    elif avatarUrl.endswith('.webp') or '.webp?' in avatarUrl:
        sessionHeaders = {'Accept': 'image/webp'}
        avatarImageFilename=avatarImagePath+'.webp'
    else:
        return None
    if not os.path.isfile(avatarImageFilename) or force:
        try:
            print('avatar image url: '+avatarUrl)
            result=session.get(avatarUrl, headers=sessionHeaders, params=None)
            if result.status_code<200 or result.status_code>202:
                print('Avatar image download failed with status '+str(result.status_code))
                # remove partial download
                if os.path.isfile(avatarImageFilename):
                    os.remove(avatarImageFilename)
            else:
                with open(avatarImageFilename, 'wb') as f:
                    f.write(result.content)
                    print('avatar image downloaded for '+actor)
                    return avatarImageFilename.replace(baseDir+'/cache','')
        except Exception as e:            
            print('Failed to download avatar image: '+str(avatarUrl))
            print(e)
        if '/channel/' not in actor:
            sessionHeaders = {'Accept': 'application/activity+json; profile="https://www.w3.org/ns/activitystreams"'}
        else:
            sessionHeaders = {'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"'}
        personJson = getJson(session,actor,sessionHeaders,None,__version__,httpPrefix,None)
        if personJson:
            if not personJson.get('id'):
                return None
            if not personJson.get('publicKey'):
                return None
            if not personJson['publicKey'].get('publicKeyPem'):
                return None
            if personJson['id']!=actor:
                return None
            if not personCache.get(actor):
                return None
            if personCache[actor]['actor']['publicKey']['publicKeyPem']!=personJson['publicKey']['publicKeyPem']:
                print("ERROR: public keys don't match when downloading actor for "+actor)
                return None
            storePersonInCache(baseDir,actor,personJson,personCache)
            return getPersonAvatarUrl(baseDir,actor,personCache)
        return None
    return avatarImageFilename.replace(baseDir+'/cache','')

def getPersonAvatarUrl(baseDir: str,personUrl: str,personCache: {}) -> str:
    """Returns the avatar url for the person
    """
    personJson = getPersonFromCache(baseDir,personUrl,personCache)    
    if not personJson:
        return None
    # get from locally stored image
    actorStr=personJson['id'].replace('/','-')
    avatarImagePath=baseDir+'/cache/avatars/'+actorStr
    if os.path.isfile(avatarImagePath+'.png'):
        return '/avatars/'+actorStr+'.png'
    if os.path.isfile(avatarImagePath+'.jpg'):
        return '/avatars/'+actorStr+'.jpg'
    if os.path.isfile(avatarImagePath+'.gif'):
        return '/avatars/'+actorStr+'.gif'
    if os.path.isfile(avatarImagePath+'.webp'):
        return '/avatars/'+actorStr+'.webp'
    if os.path.isfile(avatarImagePath):
        return '/avatars/'+actorStr
        
    if personJson.get('icon'):
        if personJson['icon'].get('url'):
            return personJson['icon']['url']
    return None

def htmlSearchEmoji(translate: {},baseDir: str,httpPrefix: str,searchStr: str) -> str:
    """Search results for emoji
    """

    # emoji.json is generated so that it can be customized and the changes
    # will be retained even if default_emoji.json is subsequently updated                    
    if not os.path.isfile(baseDir+'/emoji/emoji.json'):
        copyfile(baseDir+'/emoji/default_emoji.json',baseDir+'/emoji/emoji.json')

    searchStr=searchStr.lower().replace(':','').strip('\n')
    cssFilename=baseDir+'/epicyon-profile.css'
    if os.path.isfile(baseDir+'/epicyon.css'):
        cssFilename=baseDir+'/epicyon.css'        
    with open(cssFilename, 'r') as cssFile:
        emojiCSS=cssFile.read()
        if httpPrefix!='https':
            emojiCSS=emojiCSS.replace('https://',httpPrefix+'://')
        emojiLookupFilename=baseDir+'/emoji/emoji.json'

        # create header
        emojiForm=htmlHeader(cssFilename,emojiCSS)
        emojiForm+='<center><h1>'+translate['Emoji Search']+'</h1></center>'

        # does the lookup file exist?
        if not os.path.isfile(emojiLookupFilename):
            emojiForm+='<center><h5>'+translate['No results']+'</h5></center>'
            emojiForm+=htmlFooter()
            return emojiForm

        emojiJson=loadJson(emojiLookupFilename)
        if emojiJson:
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
                    emojiForm+='<h3>:'+emojiName+':<img loading="lazy" class="searchEmoji" src="/emoji/'+filename+'"/></h3>'
            emojiForm+='</center>'

        emojiForm+=htmlFooter()
    return emojiForm

def getIconsDir(baseDir: str) -> str:
    """Returns the directory where icons exist
    """
    iconsDir='icons'
    theme=getConfigParam(baseDir,'theme')
    if theme:
        if os.path.isdir(baseDir+'/img/icons/'+theme):
            iconsDir='icons/'+theme
    return iconsDir

def htmlSearchSharedItems(translate: {}, \
                          baseDir: str,searchStr: str, \
                          pageNumber: int, \
                          resultsPerPage: int, \
                          httpPrefix: str, \
                          domainFull: str,actor: str) -> str:
    """Search results for shared items
    """
    iconsDir=getIconsDir(baseDir)
    currPage=1
    ctr=0
    sharedItemsForm=''
    searchStrLower=searchStr.replace('%2B','+').replace('%40','@').replace('%3A',':').replace('%23','#').lower().strip('\n')
    searchStrLowerList=searchStrLower.split('+')
    cssFilename=baseDir+'/epicyon-profile.css'
    if os.path.isfile(baseDir+'/epicyon.css'):
        cssFilename=baseDir+'/epicyon.css'

    with open(cssFilename, 'r') as cssFile:
        sharedItemsCSS=cssFile.read()
        if httpPrefix!='https':
            sharedItemsCSS=sharedItemsCSS.replace('https://',httpPrefix+'://')
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

                sharesJson=loadJson(sharesFilename)
                if not sharesJson:
                    continue
                
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
                                sharedItemsForm+='<img loading="lazy" src="'+sharedItem['imageUrl']+'" alt="Item image"></a>'
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
                                sharedItemsForm+='<form method="POST" action="'+actor+'/searchhandle?page='+str(pageNumber-1)+'">'
                                sharedItemsForm+='  <input type="hidden" name="actor" value="'+actor+'">'
                                sharedItemsForm+='  <input type="hidden" name="searchtext" value="'+searchStrLower+'"><br>'
                                sharedItemsForm+='  <center><a href="'+actor+'" type="submit" name="submitSearch">'
                                sharedItemsForm+='    <img loading="lazy" class="pageicon" src="/'+iconsDir+'/pageup.png" title="'+translate['Page up']+'" alt="'+translate['Page up']+'"/></a>'
                                sharedItemsForm+='  </center>'
                                sharedItemsForm+='</form>'
                                resultsExist=True
                        ctr+=1
                        if ctr>=resultsPerPage:
                            currPage+=1
                            if currPage>pageNumber:
                                # next page link, needs to be a POST
                                sharedItemsForm+='<form method="POST" action="'+actor+'/searchhandle?page='+str(pageNumber+1)+'">'
                                sharedItemsForm+='  <input type="hidden" name="actor" value="'+actor+'">'
                                sharedItemsForm+='  <input type="hidden" name="searchtext" value="'+searchStrLower+'"><br>'
                                sharedItemsForm+='  <center><a href="'+actor+'" type="submit" name="submitSearch">'
                                sharedItemsForm+='    <img loading="lazy" class="pageicon" src="/'+iconsDir+'/pagedown.png" title="'+translate['Page down']+'" alt="'+translate['Page down']+'"/></a>'
                                sharedItemsForm+='  </center>'
                                sharedItemsForm+='</form>'
                                break
                            ctr=0
        if not resultsExist:
            sharedItemsForm+='<center><h5>'+translate['No results']+'</h5></center>'
        sharedItemsForm+=htmlFooter()
    return sharedItemsForm    

def htmlModerationInfo(translate: {},baseDir: str,httpPrefix: str) -> str:
    infoForm=''
    cssFilename=baseDir+'/epicyon-profile.css'
    if os.path.isfile(baseDir+'/epicyon.css'):
        cssFilename=baseDir+'/epicyon.css'        
    with open(cssFilename, 'r') as cssFile:
        infoCSS=cssFile.read()
        if httpPrefix!='https':
            infoCSS=infoCSS.replace('https://',httpPrefix+'://')
        infoForm=htmlHeader(cssFilename,infoCSS)

        infoForm+='<center><h1>'+translate['Moderation Information']+'</h1></center>'

        infoShown=False        
        suspendedFilename=baseDir+'/accounts/suspended.txt'
        if os.path.isfile(suspendedFilename):
            with open(suspendedFilename, "r") as f:
                suspendedStr = f.read()
                infoForm+='<div class="container">'
                infoForm+='  <br><b>'+translate['Suspended accounts']+'</b>'
                infoForm+='  <br>'+translate['These are currently suspended']
                infoForm+='  <textarea id="message" name="suspended" style="height:200px">'+suspendedStr+'</textarea>'
                infoForm+='</div>'
                infoShown=True

        blockingFilename=baseDir+'/accounts/blocking.txt'
        if os.path.isfile(blockingFilename):
            with open(blockingFilename, "r") as f:
                blockedStr = f.read()
                infoForm+='<div class="container">'
                infoForm+='  <br><b>'+translate['Blocked accounts and hashtags']+'</b>'
                infoForm+='  <br>'+translate['These are globally blocked for all accounts on this instance']
                infoForm+='  <textarea id="message" name="blocked" style="height:400px">'+blockedStr+'</textarea>'
                infoForm+='</div>'        
                infoShown=True
        if not infoShown:
            infoForm+='<center><p>'+translate['Any blocks or suspensions made by moderators will be shown here.']+'</p></center>'
        infoForm+=htmlFooter()
    return infoForm    

def htmlHashtagSearch(nickname: str,domain: str,port: int, \
                      recentPostsCache: {},maxRecentPosts: int, \
                      translate: {}, \
                      baseDir: str,hashtag: str,pageNumber: int, \
                      postsPerPage: int, \
                      session,wfRequest: {},personCache: {}, \
                      httpPrefix: str,projectVersion: str) -> str:
    """Show a page containing search results for a hashtag
    """
    iconsDir=getIconsDir(baseDir)
    if hashtag.startswith('#'):
        hashtag=hashtag[1:]
    hashtagIndexFile=baseDir+'/tags/'+hashtag+'.txt'
    if not os.path.isfile(hashtagIndexFile):
        return None

    # check that the directory for the nickname exists
    if nickname:
        if not os.path.isdir(baseDir+'/accounts/'+nickname+'@'+domain):
            nickname=None

    # read the index
    with open(hashtagIndexFile, "r") as f:
        lines = f.readlines()

    # read the css
    cssFilename=baseDir+'/epicyon-profile.css'
    if os.path.isfile(baseDir+'/epicyon.css'):
        cssFilename=baseDir+'/epicyon.css'        
    with open(cssFilename, 'r') as cssFile:
        hashtagSearchCSS = cssFile.read()
        if httpPrefix!='https':
            hashtagSearchCSS=hashtagSearchCSS.replace('https://',httpPrefix+'://')

    # ensure that the page number is in bounds
    if not pageNumber:
        pageNumber=1
    elif pageNumber<1:
        pageNumber=1

    # get the start end end within the index file
    startIndex=int((pageNumber-1)*postsPerPage)
    endIndex=startIndex+postsPerPage
    noOfLines=len(lines)
    if endIndex>=noOfLines and noOfLines>0:        
        endIndex=noOfLines-1

    # add the page title
    hashtagSearchForm=htmlHeader(cssFilename,hashtagSearchCSS)
    hashtagSearchForm+='<script>'+contentWarningScript()+'</script>'
    hashtagSearchForm+='<center><h1>#'+hashtag+'</h1></center>'

    if startIndex>0:
        # previous page link
        hashtagSearchForm+= \
            '<center><a href="/tags/'+hashtag+'?page='+ \
            str(pageNumber-1)+'"><img loading="lazy" class="pageicon" src="/'+ \
            iconsDir+'/pageup.png" title="'+translate['Page up']+ \
            '" alt="'+translate['Page up']+'"></a></center>'
    index=startIndex
    while index<=endIndex:
        postId=lines[index].strip('\n')
        if '  ' not in postId:
            nickname=getNicknameFromActor(postId)
            if not nickname:
                index+=1
                continue
        else:
            postFields=postId.split('  ')
            if len(postFields)!=3:
                index=+1
                continue
            postDaysSinceEposh=int(postFields[0])
            nickname=postFields[1]
            postId=postFields[2]
        postFilename=locatePost(baseDir,nickname,domain,postId)
        if not postFilename:
            index+=1
            continue
        postJsonObject=loadJson(postFilename)
        if postJsonObject:
            if not isPublicPost(postJsonObject):
                index+=1
                continue            
            showIndividualPostIcons=False
            if nickname:
                showIndividualPostIcons=True
            allowDeletion=False
            hashtagSearchForm+= \
                individualPostAsHtml(recentPostsCache,maxRecentPosts, \
                                     iconsDir,translate,None, \
                                     baseDir,session,wfRequest,personCache, \
                                     nickname,domain,port,postJsonObject, \
                                     None,True,allowDeletion, \
                                     httpPrefix,projectVersion,'search', \
                                     showIndividualPostIcons, \
                                     showIndividualPostIcons, \
                                     False,False,False)
        index+=1

    if endIndex<noOfLines-1:
        # next page link
        hashtagSearchForm+= \
            '<center><a href="/tags/'+hashtag+'?page='+str(pageNumber+1)+ \
            '"><img loading="lazy" class="pageicon" src="/'+iconsDir+ \
            '/pagedown.png" title="'+translate['Page down']+ \
            '" alt="'+translate['Page down']+'"></a></center>'
    hashtagSearchForm+=htmlFooter()
    return hashtagSearchForm

def htmlSkillsSearch(translate: {},baseDir: str, \
                     httpPrefix: str, \
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
            actorJson=loadJson(actorFilename)
            if actorJson:
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
                cachedActorJson=loadJson(actorFilename)
                if cachedActorJson:
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
        if httpPrefix!='https':
            skillSearchCSS=skillSearchCSS.replace('https://',httpPrefix+'://')
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
                skillSearchForm+='<img loading="lazy" src="'+avatarUrl+'"/><span class="search-result-text">'+actorName+'</span></a></div>'
                ctr+=1
                if ctr>=postsPerPage:
                    break
        skillSearchForm+='</center>'
    skillSearchForm+=htmlFooter()
    return skillSearchForm

def htmlEditProfile(translate: {},baseDir: str,path: str,domain: str,port: int,httpPrefix: str) -> str:
    """Shows the edit profile screen
    """
    imageFormats='.png, .jpg, .jpeg, .gif, .webp'
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
    isGroup=''
    followDMs=''
    mediaInstanceStr=''
    displayNickname=nickname
    bioStr=''
    donateUrl=''
    emailAddress=''
    PGPpubKey=''
    xmppAddress=''
    matrixAddress=''
    manuallyApprovesFollowers=''
    actorJson=loadJson(actorFilename)
    if actorJson:
        donateUrl=getDonationUrl(actorJson)
        xmppAddress=getXmppAddress(actorJson)
        matrixAddress=getMatrixAddress(actorJson)
        emailAddress=getEmailAddress(actorJson)
        PGPpubKey=getPGPpubKey(actorJson)
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
                isGroup=''
            elif actorJson['type']=='Group':
                isGroup='checked'
                isBot=''
    if os.path.isfile(baseDir+'/accounts/'+nickname+'@'+domain+'/.followDMs'):
        followDMs='checked'

    mediaInstance=getConfigParam(baseDir,"mediaInstance")
    if mediaInstance:
        if mediaInstance==True:
            mediaInstanceStr='checked'
                
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
        if httpPrefix!='https':
            editProfileCSS=editProfileCSS.replace('https://',httpPrefix+'://')

    instanceStr=''
    moderatorsStr=''
    themesDropdown=''
    adminNickname=getConfigParam(baseDir,'admin')
    if path.startswith('/users/'+adminNickname+'/'):
        instanceDescription=getConfigParam(baseDir,'instanceDescription')
        instanceDescriptionShort=getConfigParam(baseDir,'instanceDescriptionShort')
        instanceTitle=getConfigParam(baseDir,'instanceTitle')
        instanceStr='<div class="container">'
        instanceStr+='  <label class="labels">'+translate['Instance Title']+'</label>'
        instanceStr+='  <input type="text" name="instanceTitle" value="'+instanceTitle+'"><br>'
        instanceStr+='  <label class="labels">'+translate['Instance Short Description']+'</label>'
        instanceStr+='  <input type="text" name="instanceDescriptionShort" value="'+instanceDescriptionShort+'"><br>'
        instanceStr+='  <label class="labels">'+translate['Instance Description']+'</label>'
        instanceStr+='  <textarea id="message" name="instanceDescription" style="height:200px">'+instanceDescription+'</textarea>'
        instanceStr+='  <label class="labels">'+translate['Instance Logo']+'</label>'
        instanceStr+='  <input type="file" id="instanceLogo" name="instanceLogo"'
        instanceStr+='      accept="'+imageFormats+'">'
        instanceStr+='</div>'
        
        moderators=''
        moderatorsFile=baseDir+'/accounts/moderators.txt'
        if os.path.isfile(moderatorsFile):
            with open(moderatorsFile, "r") as f:
                moderators = f.read()
        moderatorsStr='<div class="container">'
        moderatorsStr+='  <b>'+translate['Moderators']+'</b><br>'
        moderatorsStr+='  '+translate['A list of moderator nicknames. One per line.']
        moderatorsStr+='  <textarea id="message" name="moderators" placeholder="'+translate['List of moderator nicknames']+'..." style="height:200px">'+moderators+'</textarea>'
        moderatorsStr+='</div>'

        themesDropdown= '<div class="container">'
        themesDropdown+='  <b>'+translate['Theme']+'</b><br>'
        themesDropdown+='  <select id="themeDropdown" name="themeDropdown" class="theme">'
        themesDropdown+='    <option value="default">'+translate['Default']+'</option>'
        themesDropdown+='    <option value="light">'+translate['Light']+'</option>'
        themesDropdown+='    <option value="purple">'+translate['Purple']+'</option>'
        themesDropdown+='    <option value="hacker">'+translate['Hacker']+'</option>'
        themesDropdown+='    <option value="highvis">'+translate['HighVis']+'</option>'
        themesDropdown+='  </select><br>'
        themesDropdown+='</div>'
        themeName=getConfigParam(baseDir,'theme')
        themesDropdown=themesDropdown.replace('<option value="'+themeName+'">','<option value="'+themeName+'" selected>')

    editProfileForm=htmlHeader(cssFilename,editProfileCSS)
    editProfileForm+='<form enctype="multipart/form-data" method="POST" accept-charset="UTF-8" action="'+path+'/profiledata">'
    editProfileForm+='  <div class="vertical-center">'
    editProfileForm+='    <p class="new-post-text">'+translate['Profile for']+' '+nickname+'@'+domainFull+'</p>'
    editProfileForm+='    <div class="container">'
    editProfileForm+='      <input type="submit" name="submitProfile" value="'+translate['Submit']+'">'
    editProfileForm+='      <a href="'+pathOriginal+'"><button class="cancelbtn">'+translate['Cancel']+'</button></a>'
    editProfileForm+='    </div>'
    editProfileForm+='    <div class="container">'
    editProfileForm+='      <label class="labels">'+translate['Nickname']+'</label>'
    editProfileForm+='      <input type="text" name="displayNickname" value="'+displayNickname+'"><br>'
    editProfileForm+='      <label class="labels">'+translate['Your bio']+'</label>'
    editProfileForm+='      <textarea id="message" name="bio" style="height:200px">'+bioStr+'</textarea>'
    editProfileForm+='<label class="labels">'+translate['Donations link']+'</label><br>'
    editProfileForm+='      <input type="text" placeholder="https://..." name="donateUrl" value="'+donateUrl+'">'
    editProfileForm+='<label class="labels">'+translate['XMPP']+'</label><br>'
    editProfileForm+='      <input type="text" name="xmppAddress" value="'+xmppAddress+'">'
    editProfileForm+='<label class="labels">'+translate['Matrix']+'</label><br>'
    editProfileForm+='      <input type="text" name="matrixAddress" value="'+matrixAddress+'">'
    editProfileForm+='<label class="labels">'+translate['Email']+'</label><br>'
    editProfileForm+='      <input type="text" name="email" value="'+emailAddress+'">'
    editProfileForm+='<label class="labels">'+translate['PGP']+'</label><br>'
    editProfileForm+='      <textarea id="message" placeholder="-----BEGIN PGP PUBLIC KEY BLOCK-----" name="pgp" style="height:100px">'+PGPpubKey+'</textarea>'
    editProfileForm+='    </div>'
    editProfileForm+='    <div class="container">'
    editProfileForm+='      <label class="labels">'+translate['The files attached below should be no larger than 10MB in total uploaded at once.']+'</label><br><br>'
    editProfileForm+='      <label class="labels">'+translate['Avatar image']+'</label>'
    editProfileForm+='      <input type="file" id="avatar" name="avatar"'
    editProfileForm+='            accept="'+imageFormats+'">'
    editProfileForm+='      <br><label class="labels">'+translate['Background image']+'</label>'
    editProfileForm+='      <input type="file" id="image" name="image"'
    editProfileForm+='            accept="'+imageFormats+'">'
    editProfileForm+='      <br><label class="labels">'+translate['Timeline banner image']+'</label>'
    editProfileForm+='      <input type="file" id="banner" name="banner"'
    editProfileForm+='            accept="'+imageFormats+'">'
    editProfileForm+='    </div>'
    editProfileForm+='    <div class="container">'
    editProfileForm+='<label class="labels">'+translate['Change Password']+'</label><br>'
    editProfileForm+='      <input type="text" name="password" value=""><br>'
    editProfileForm+='<label class="labels">'+translate['Confirm Password']+'</label><br>'
    editProfileForm+='      <input type="text" name="passwordconfirm" value="">'
    editProfileForm+='    </div>'
    editProfileForm+='    <div class="container">'
    editProfileForm+='      <input type="checkbox" class=profilecheckbox" name="approveFollowers" '+manuallyApprovesFollowers+'>'+translate['Approve follower requests']+'<br>'
    editProfileForm+='      <input type="checkbox" class=profilecheckbox" name="isBot" '+isBot+'>'+translate['This is a bot account']+'<br>'
    editProfileForm+='      <input type="checkbox" class=profilecheckbox" name="isGroup" '+isGroup+'>'+translate['This is a group account']+'<br>'
    editProfileForm+='      <input type="checkbox" class=profilecheckbox" name="followDMs" '+followDMs+'>'+translate['Only people I follow can send me DMs']+'<br>'
    if path.startswith('/users/'+adminNickname+'/'):
        editProfileForm+='      <input type="checkbox" class=profilecheckbox" name="mediaInstance" '+mediaInstanceStr+'>'+translate['This is a media instance']+'<br>'
    editProfileForm+='      <br><b><label class="labels">'+translate['Filtered words']+'</label></b>'
    editProfileForm+='      <br><label class="labels">'+translate['One per line']+'</label>'
    editProfileForm+='      <textarea id="message" name="filteredWords" style="height:200px">'+filterStr+'</textarea>'
    editProfileForm+='      <br><b><label class="labels">'+translate['Blocked accounts']+'</label></b>'
    editProfileForm+='      <br><label class="labels">'+translate['Blocked accounts, one per line, in the form nickname@domain or *@blockeddomain']+'</label>'
    editProfileForm+='      <textarea id="message" name="blocked" style="height:200px">'+blockedStr+'</textarea>'
    editProfileForm+='      <br><b><label class="labels">'+translate['Federation list']+'</label></b>'
    editProfileForm+='      <br><label class="labels">'+translate['Federate only with a defined set of instances. One domain name per line.']+'</label>'
    editProfileForm+='      <textarea id="message" name="allowedInstances" style="height:200px">'+allowedInstancesStr+'</textarea>'
    editProfileForm+='    </div>'
    editProfileForm+='    <div class="container">'
    editProfileForm+='      <b><label class="labels">'+translate['Skills']+'</label></b><br>'
    editProfileForm+='      <label class="labels">'+translate['If you want to participate within organizations then you can indicate some skills that you have and approximate proficiency levels. This helps organizers to construct teams with an appropriate combination of skills.']+'</label>'
    editProfileForm+=skillsStr+themesDropdown+moderatorsStr
    editProfileForm+='    </div>'+instanceStr
    editProfileForm+='    <div class="container">'
    editProfileForm+='      <b><label class="labels">'+translate['Danger Zone']+'</label></b><br>'
    editProfileForm+='      <input type="checkbox" class=dangercheckbox" name="deactivateThisAccount">'+translate['Deactivate this account']+'<br>'
    editProfileForm+='    </div>'
    editProfileForm+='  </div>'
    editProfileForm+='</form>'
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

def htmlLogin(translate: {},baseDir: str,autocomplete=True) -> str:
    """Shows the login screen
    """
    accounts=noOfAccounts(baseDir)

    loginImage='login.png'
    loginImageFilename=None
    if os.path.isfile(baseDir+'/accounts/'+loginImage):
        loginImageFilename=baseDir+'/accounts/'+loginImage
    if os.path.isfile(baseDir+'/accounts/login.jpg'):
        loginImage='login.jpg'
        loginImageFilename=baseDir+'/accounts/'+loginImage
    if os.path.isfile(baseDir+'/accounts/login.jpeg'):
        loginImage='login.jpeg'
        loginImageFilename=baseDir+'/accounts/'+loginImage
    if os.path.isfile(baseDir+'/accounts/login.gif'):
        loginImage='login.gif'
        loginImageFilename=baseDir+'/accounts/'+loginImage
    if os.path.isfile(baseDir+'/accounts/login.webp'):
        loginImage='login.webp'
        loginImageFilename=baseDir+'/accounts/'+loginImage

    if not loginImageFilename:
        loginImageFilename=baseDir+'/accounts/'+loginImage
        copyfile(baseDir+'/img/login.png',loginImageFilename)
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

    autocompleteStr=''
    if not autocomplete:
        autocompleteStr='autocomplete="off" value=""'

        
    loginForm=htmlHeader(cssFilename,loginCSS)
    loginForm+='<form method="POST" action="/login">'
    loginForm+='  <div class="imgcontainer">'
    loginForm+='    <img loading="lazy" src="'+loginImage+'" alt="login image" class="loginimage">'
    loginForm+=loginText+TOSstr
    loginForm+='  </div>'
    loginForm+=''
    loginForm+='  <div class="container">'
    loginForm+='    <label for="nickname"><b>'+translate['Nickname']+'</b></label>'
    loginForm+='    <input type="text" '+autocompleteStr+' placeholder="'+translate['Enter Nickname']+'" name="username" required autofocus>'
    loginForm+=''
    loginForm+='    <label for="password"><b>'+translate['Password']+'</b></label>'
    loginForm+='    <input type="password" '+autocompleteStr+' placeholder="'+translate['Enter Password']+'" name="password" required>'
    loginForm+=registerButtonStr+loginButtonStr
    loginForm+='  </div>'
    loginForm+='</form>'
    loginForm+='<a href="https://gitlab.com/bashrc2/epicyon"><img loading="lazy" class="license" title="'+translate['Get the source code']+'" alt="'+translate['Get the source code']+'" src="/icons/agpl.png" /></a>'
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
        if httpPrefix!='https':
            termsCSS=termsCSS.replace('https://',httpPrefix+'://')
            
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
        if httpPrefix!='http':
            termsCSS=termsCSS.replace('https://',httpPrefix+'://')

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

def htmlNewPost(mediaInstance: bool,translate: {}, \
                baseDir: str,httpPrefix: str, \
                path: str,inReplyTo: str, \
                mentions: [], \
                reportUrl: str,pageNumber: int, \
                nickname: str,domain: str) -> str:
    """New post screen
    """
    iconsDir=getIconsDir(baseDir)
    replyStr=''

    showPublicOnDropdown=True

    if not path.endswith('/newshare'):
        if not path.endswith('/newreport'):
            if not inReplyTo:
                newPostText='<p class="new-post-text">'+translate['Write your post text below.']+'</p>'
            else:
                newPostText='<p class="new-post-text">'+translate['Write your reply to']+' <a href="'+inReplyTo+'">'+translate['this post']+'</a></p>'
                replyStr='<input type="hidden" name="replyTo" value="'+inReplyTo+'">'

                # if replying to a non-public post then also make this post non-public
                if not isPublicPostFromUrl(baseDir,nickname,domain,inReplyTo):
                    newPostPath=path
                    if '?' in newPostPath:
                        newPostPath=newPostPath.split('?')[0]
                    if newPostPath.endswith('/newpost'):
                        path=path.replace('/newpost','/newfollowers')
                    elif newPostPath.endswith('/newunlisted'):
                        path=path.replace('/newunlisted','/newfollowers')
                    showPublicOnDropdown=False
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

    if path.endswith('/newquestion'):
        newPostText='<p class="new-post-text">'+translate['Enter the choices for your question below.']+'</p>'

    if os.path.isfile(baseDir+'/accounts/newpost.txt'):
        with open(baseDir+'/accounts/newpost.txt', 'r') as file:
            newPostText = '<p class="new-post-text">'+file.read()+'</p>'    

    cssFilename=baseDir+'/epicyon-profile.css'
    if os.path.isfile(baseDir+'/epicyon.css'):
        cssFilename=baseDir+'/epicyon.css'        
    with open(cssFilename, 'r') as cssFile:
        newPostCSS = cssFile.read()
        if httpPrefix!='https':
            newPostCSS=newPostCSS.replace('https://',httpPrefix+'://')

    if '?' in path:
        path=path.split('?')[0]
    pathBase=path.replace('/newreport','').replace('/newpost','').replace('/newshare','').replace('/newunlisted','').replace('/newfollowers','').replace('/newdm','')

    newPostImageSection ='    <div class="container">'
    newPostImageSection+='      <label class="labels">'+translate['Image description']+'</label>'
    newPostImageSection+='      <input type="text" name="imageDescription">'
    newPostImageSection+='      <input type="file" id="attachpic" name="attachpic"'
    newPostImageSection+='            accept=".png, .jpg, .jpeg, .gif, .webp, .mp4, .webm, .ogv, .mp3, .ogg">'
    newPostImageSection+='    </div>'
    
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
    if path.endswith('/newquestion'):
        scopeIcon='scope_question.png'
        scopeDescription=translate['Question']
        placeholderMessage=translate['Enter your question']+'...'
        endpoint='newquestion'
        extraFields='<div class="container">'
        extraFields+='  <label class="labels">'+translate['Possible answers']+':</label><br>'
        for questionCtr in range(8):
            extraFields+='  <input type="text" class="questionOption" placeholder="'+str(questionCtr+1)+'" name="questionOption'+str(questionCtr)+'"><br>'
        extraFields+='  <label class="labels">'+translate['Duration of listing in days']+':</label> <input type="number" name="duration" min="1" max="365" step="1" value="14"><br>'
        extraFields+='</div>'
    if path.endswith('/newshare'):
        scopeIcon='scope_share.png'
        scopeDescription=translate['Shared Item']
        placeholderSubject=translate['Name of the shared item']+'...'
        placeholderMessage=translate['Description of the item being shared']+'...'
        endpoint='newshare'        
        extraFields='<div class="container">'
        extraFields+='  <label class="labels">'+translate['Type of shared item. eg. hat']+':</label>'
        extraFields+='  <input type="text" class="itemType" name="itemType">'
        extraFields+='  <br><label class="labels">'+translate['Category of shared item. eg. clothing']+':</label>'
        extraFields+='  <input type="text" class="category" name="category">'
        extraFields+='  <br><label class="labels">'+translate['Duration of listing in days']+':</label>'
        extraFields+='  <input type="number" name="duration" min="1" max="365" step="1" value="14">'
        extraFields+='</div>'
        extraFields+='<div class="container">'
        extraFields+='<label class="labels">'+translate['City or location of the shared item']+':</label>'
        extraFields+='<input type="text" name="location">'
        extraFields+='</div>'

    dateAndLocation=''
    if endpoint!='newshare' and endpoint!='newreport' and endpoint!='newquestion':
        dateAndLocation='<div class="container">'
        dateAndLocation+='<p><img loading="lazy" alt="" title="" class="emojicalendar" src="/'+iconsDir+'/calendar.png"/>'
        dateAndLocation+='<label class="labels">'+translate['Date']+': </label>'
        dateAndLocation+='<input type="date" name="eventDate">'
        dateAndLocation+='<label class="labelsright">'+translate['Time']+':'
        dateAndLocation+='<input type="time" name="eventTime"></label></p>'
        dateAndLocation+='</div>'
        dateAndLocation+='<div class="container">'
        dateAndLocation+='<br><label class="labels">'+translate['Location']+': </label>'
        dateAndLocation+='<input type="text" name="location">'
        dateAndLocation+='</div>'

    newPostForm=htmlHeader(cssFilename,newPostCSS)

    # only show the share option if this is not a reply
    shareOptionOnDropdown=''
    questionOptionOnDropdown=''
    if not replyStr:
        shareOptionOnDropdown='<a href="'+pathBase+'/newshare"><img loading="lazy" alt="" title="" src="/'+iconsDir+'/scope_share.png"/><b>'+translate['Shares']+'</b><br>'+translate['Describe a shared item']+'</a>'
        questionOptionOnDropdown='<a href="'+pathBase+'/newquestion"><img loading="lazy" alt="" title="" src="/'+iconsDir+'/scope_question.png"/><b>'+translate['Question']+'</b><br>'+translate['Ask a question']+'</a>'

    mentionsStr=''
    for m in mentions:
        mentionNickname=getNicknameFromActor(m)
        if not mentionNickname:
            continue
        mentionDomain,mentionPort=getDomainFromActor(m)
        if not mentionDomain:
            continue
        if mentionPort:
            mentionsHandle='@'+mentionNickname+'@'+mentionDomain+':'+str(mentionPort)
        else:
            mentionsHandle='@'+mentionNickname+'@'+mentionDomain
        if mentionsHandle not in mentionsStr:
            mentionsStr+=mentionsHandle+' '

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
        dropDownContent+='        <div id="myDropdown" class="dropdown-content">'
        if showPublicOnDropdown:
            dropDownContent+='          <a href="'+pathBase+dropdownNewPostSuffix+'"><img loading="lazy" alt="" title="" src="/'+iconsDir+'/scope_public.png"/><b>'+translate['Public']+'</b><br>'+translate['Visible to anyone']+'</a>'
            dropDownContent+='          <a href="'+pathBase+dropdownUnlistedSuffix+'"><img loading="lazy" alt="" title="" src="/'+iconsDir+'/scope_unlisted.png"/><b>'+translate['Unlisted']+'</b><br>'+translate['Not on public timeline']+'</a>'
        dropDownContent+='          <a href="'+pathBase+dropdownFollowersSuffix+'"><img loading="lazy" alt="" title="" src="/'+iconsDir+'/scope_followers.png"/><b>'+translate['Followers']+'</b><br>'+translate['Only to followers']+'</a>'
        dropDownContent+='          <a href="'+pathBase+dropdownDMSuffix+'"><img loading="lazy" alt="" title="" src="/'+iconsDir+'/scope_dm.png"/><b>'+translate['DM']+'</b><br>'+translate['Only to mentioned people']+'</a>'
        dropDownContent+='          <a href="'+pathBase+dropdownReportSuffix+'"><img loading="lazy" alt="" title="" src="/'+iconsDir+'/scope_report.png"/><b>'+translate['Report']+'</b><br>'+translate['Send to moderators']+'</a>'
        dropDownContent+=questionOptionOnDropdown+shareOptionOnDropdown
        dropDownContent+='        </div>'
    else:
        mentionsStr='Re: '+reportUrl+'\n\n'+mentionsStr
    
    newPostForm+='<form enctype="multipart/form-data" method="POST" accept-charset="UTF-8" action="'+path+'?'+endpoint+'?page='+str(pageNumber)+'">'
    newPostForm+='  <div class="vertical-center">'
    newPostForm+='    <label for="nickname"><b>'+newPostText+'</b></label>'
    newPostForm+='    <div class="container">'
    newPostForm+='      <div class="dropbtn" onclick="dropdown()">'
    newPostForm+='        <img loading="lazy" alt="" title="" src="/'+iconsDir+'/'+scopeIcon+'"/><b class="scope-desc">'+scopeDescription+'</b>'
    newPostForm+=dropDownContent
    newPostForm+='      </div>'
    newPostForm+='      <a href="'+pathBase+'/searchemoji"><img loading="lazy" class="emojisearch" src="/emoji/1F601.png" title="'+translate['Search for emoji']+'" alt="'+translate['Search for emoji']+'"/></a>'
    newPostForm+='    </div>'
    newPostForm+='    <div class="container"><center>'
    newPostForm+='      <a href="'+pathBase+'/inbox"><button class="cancelbtn">'+translate['Cancel']+'</button></a>'
    newPostForm+='      <input type="submit" name="submitPost" value="'+translate['Submit']+'">'
    newPostForm+='    </center></div>'
    newPostForm+=replyStr
    if mediaInstance and not replyStr:
        newPostForm+=newPostImageSection
    newPostForm+='    <label class="labels">'+placeholderSubject+'</label><br>'
    newPostForm+='    <input type="text" name="subject">'
    newPostForm+=''
    newPostForm+='    <br><label class="labels">'+placeholderMessage+'</label>'
    messageBoxHeight=400
    if mediaInstance:
        messageBoxHeight=200
    if endpoint=='newquestion':
        messageBoxHeight=100
    newPostForm+='    <textarea id="message" name="message" style="height:'+str(messageBoxHeight)+'px">'+mentionsStr+'</textarea>'
    newPostForm+=extraFields+dateAndLocation
    if not mediaInstance or replyStr:
        newPostForm+=newPostImageSection
    newPostForm+='  </div>'
    newPostForm+='</form>'

    if not reportUrl:
        newPostForm+='<script>'+clickToDropDownScript()+cursorToEndOfMessageScript()+'</script>'
        newPostForm=newPostForm.replace('<body>','<body onload="focusOnMessage()">')

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
        htmlStr='<!DOCTYPE html>\n'
        htmlStr+='<html lang="'+lang+'">\n'
        htmlStr+=meta
        htmlStr+='  <style>\n'
        htmlStr+='    @import url("'+cssFilename+'");\n'
        htmlStr+='    background-color: #282c37'
        htmlStr+='  </style>\n'
        htmlStr+='  <body>\n'
    else:
        htmlStr='<!DOCTYPE html>\n'
        htmlStr+='<html lang="'+lang+'">\n'
        htmlStr+=meta
        htmlStr+='  <style>\n'+css+'</style>\n'
        htmlStr+='  <body>\n'        
    return htmlStr

def htmlFooter() -> str:
    htmlStr='  </body>\n'
    htmlStr+='</html>\n'
    return htmlStr

def htmlProfilePosts(recentPostsCache: {},maxRecentPosts: int, \
                     translate: {}, \
                     baseDir: str,httpPrefix: str, \
                     authorized: bool,ocapAlways: bool, \
                     nickname: str,domain: str,port: int, \
                     session,wfRequest: {},personCache: {}, \
                     projectVersion: str) -> str:
    """Shows posts on the profile screen
    These should only be public posts
    """
    iconsDir=getIconsDir(baseDir)
    profileStr=''
    maxItems=4
    profileStr+='<script>'+contentWarningScript()+'</script>'
    ctr=0
    currPage=1
    while ctr<maxItems and currPage<4:
        outboxFeed= \
            personBoxJson({},session,baseDir,domain, \
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
                postStr= \
                    individualPostAsHtml(recentPostsCache,maxRecentPosts, \
                                         iconsDir,translate,None, \
                                         baseDir,session,wfRequest,personCache, \
                                         nickname,domain,port,item,None,True,False, \
                                         httpPrefix,projectVersion,'inbox', \
                                         False,False,False,True,False)
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

    iconsDir=getIconsDir(baseDir)
    if authorized and pageNumber:
        if authorized and pageNumber>1:
            # page up arrow
            profileStr+= \
                '<center><a href="'+actor+'/'+feedName+'?page='+str(pageNumber-1)+'"><img loading="lazy" class="pageicon" src="/'+iconsDir+'/pageup.png" title="'+translate['Page up']+'" alt="'+translate['Page up']+'"></a></center>'
        
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
                '<center><a href="'+actor+'/'+feedName+'?page='+str(pageNumber+1)+'"><img loading="lazy" class="pageicon" src="/'+iconsDir+'/pagedown.png" title="'+translate['Page down']+'" alt="'+translate['Page down']+'"></a></center>'
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

def htmlIndividualShare(actor: str,item: {},translate: {},showContact: bool,removeButton: bool) -> str:
    """Returns an individual shared item as html
    """
    profileStr='<div class="container">'
    profileStr+='<p class="share-title">'+item['displayName']+'</p>'
    if item.get('imageUrl'):
        profileStr+='<a href="'+item['imageUrl']+'">'
        profileStr+='<img loading="lazy" src="'+item['imageUrl']+'" alt="'+translate['Item image']+'"></a>'
    profileStr+='<p>'+item['summary']+'</p>'
    profileStr+='<p><b>'+translate['Type']+':</b> '+item['itemType']+' '
    profileStr+='<b>'+translate['Category']+':</b> '+item['category']+' '
    profileStr+='<b>'+translate['Location']+':</b> '+item['location']+'</p>'
    if showContact:
        contactActor=item['actor']
        profileStr+='<p><a href="'+actor+'?replydm=sharedesc:'+item['displayName']+'?mention='+contactActor+'"><button class="button">'+translate['Contact']+'</button></a>'
    if removeButton:
        profileStr+=' <a href="'+actor+'?rmshare='+item['displayName']+'"><button class="button">'+translate['Remove']+'</button></a>'
    profileStr+='</div>'
    return profileStr

def htmlProfileShares(actor: str,translate: {},nickname: str,domain: str,sharesJson: {}) -> str:
    """Shows shares on the profile screen
    """
    profileStr=''
    for item in sharesJson['orderedItems']:
        profileStr+=htmlIndividualShare(actor,item,translate,False,False)
    if len(profileStr)>0:
        profileStr='<div class="share-title">'+profileStr+'</div>'
    return profileStr

def sharesTimelineJson(actor: str,pageNumber: int,itemsPerPage: int, \
                       baseDir: str,maxSharesPerAccount: int) -> ({},bool):
    """Get a page on the shared items timeline as json
    maxSharesPerAccount helps to avoid one person dominating the timeline
    by sharing a large number of things
    """
    allSharesJson={}
    for subdir, dirs, files in os.walk(baseDir+'/accounts'):
        for handle in dirs:
            if '@' in handle:
                accountDir=baseDir+'/accounts/'+handle
                sharesFilename=accountDir+'/shares.json'
                if os.path.isfile(sharesFilename):
                    sharesJson=loadJson(sharesFilename)
                    if not sharesJson:
                        continue
                    nickname=handle.split('@')[0]
                    # actor who owns this share
                    owner=actor.split('/users/')[0]+'/users/'+nickname
                    ctr=0
                    for itemID,item in sharesJson.items():
                        # assign owner to the item
                        item['actor']=owner
                        allSharesJson[str(item['published'])]=item
                        ctr+=1
                        if ctr>=maxSharesPerAccount:
                            break
    # sort the shared items in descending order of publication date
    sharesJson=OrderedDict(sorted(allSharesJson.items(),reverse=True))
    lastPage=False
    startIndex=itemsPerPage*pageNumber
    maxIndex=len(sharesJson.items())
    if maxIndex<itemsPerPage:
        lastPage=True
    if startIndex>=maxIndex-itemsPerPage:
        lastPage=True
        startIndex=maxIndex-itemsPerPage
        if startIndex<0:
            startIndex=0
    ctr=0
    resultJson={}
    for published,item in sharesJson.items():
        if ctr>=startIndex+itemsPerPage:
            break        
        if ctr<startIndex:
            ctr+=1
            continue
        resultJson[published]=item
        ctr+=1
    return resultJson,lastPage

def htmlSharesTimeline(translate: {},pageNumber: int,itemsPerPage: int, \
                       baseDir: str,actor: str, \
                       nickname: str,domain: str,port: int, \
                       maxSharesPerAccount: int,httpPrefix: str) -> str:
    """Show shared items timeline as html
    """
    sharesJson,lastPage= \
        sharesTimelineJson(actor,pageNumber,itemsPerPage, \
                           baseDir,maxSharesPerAccount)
    domainFull=domain
    if port!=80 and port!=443:
        if ':' not in domain:
            domainFull=domain+':'+str(port)
    actor=httpPrefix+'://'+domainFull+'/users/'+nickname
    timelineStr=''

    if pageNumber>1:
        timelineStr+='<center><a href="'+actor+'/tlshares?page='+str(pageNumber-1)+'"><img loading="lazy" class="pageicon" src="/'+iconsDir+'/pageup.png" title="'+translate['Page up']+'" alt="'+translate['Page up']+'"></a></center>'

    for published,item in sharesJson.items():
        showContactButton=False
        if item['actor']!=actor:
            showContactButton=True
        showRemoveButton=False
        if item['actor']==actor:
            showRemoveButton=True
        timelineStr+=htmlIndividualShare(actor,item,translate,showContactButton,showRemoveButton)

    if not lastPage:
        timelineStr+='<center><a href="'+actor+'/tlshares?page='+str(pageNumber+1)+'"><img loading="lazy" class="pageicon" src="/'+iconsDir+'/pagedown.png" title="'+translate['Page down']+'" alt="'+translate['Page down']+'"></a></center>'
        
    return timelineStr

def htmlProfile(defaultTimeline: str, \
                recentPostsCache: {},maxRecentPosts: int, \
                translate: {},projectVersion: str, \
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
    domain,port=getDomainFromActor(profileJson['id'])
    if not domain:
        return ""
    displayName= \
        addEmojiToDisplayName(baseDir,httpPrefix, \
                              nickname,domain, \
                              profileJson['name'],True)    
    domainFull=domain
    if port:
        domainFull=domain+':'+str(port)
    profileDescription= \
        addEmojiToDisplayName(baseDir,httpPrefix, \
                              nickname,domain, \
                              profileJson['summary'],False)    
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
    logoutStr=''
    actor=profileJson['id']

    donateSection=''
    donateUrl=getDonationUrl(profileJson)
    PGPpubKey=getPGPpubKey(profileJson)
    emailAddress=getEmailAddress(profileJson)
    xmppAddress=getXmppAddress(profileJson)
    matrixAddress=getMatrixAddress(profileJson)
    if donateUrl or xmppAddress or matrixAddress or PGPpubKey or emailAddress:
        donateSection='<div class="container">\n'
        donateSection+='  <center>\n'
        if donateUrl:
            donateSection+='    <p><a href="'+donateUrl+'"><button class="donateButton">'+translate['Donate']+'</button></a></p>\n'
        if emailAddress:
            donateSection+='<p>'+translate['Email']+': '+emailAddress+'</p>\n'
        if xmppAddress:
            donateSection+='<p>'+translate['XMPP']+': '+xmppAddress+'</p>\n'
        if matrixAddress:
            donateSection+='<p>'+translate['Matrix']+': '+matrixAddress+'</p>\n'
        if PGPpubKey:
            donateSection+='<p class="pgp">'+PGPpubKey.replace('\n','<br>')+'</p>\n'
        donateSection+='  </center>\n'
        donateSection+='</div>\n'

    if not authorized:
        loginButton='<br><a href="/login"><button class="loginButton">'+translate['Login']+'</button></a>'
    else:
        editProfileStr='<a href="'+actor+'/editprofile"><button class="button"><span>'+translate['Edit']+' </span></button></a>'
        logoutStr='<a href="/logout"><button class="button"><span>'+translate['Logout']+' </span></button></a>'
        linkToTimelineStart='<a href="/users/'+nickname+'/'+defaultTimeline+'"><label class="transparent">'+translate['Switch to timeline view']+'</label></a>'
        linkToTimelineStart+='<a href="/users/'+nickname+'/'+defaultTimeline+'" title="'+translate['Switch to timeline view']+'" alt="'+translate['Switch to timeline view']+'">'
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

    profileDescriptionShort=profileDescription
    if '\n' in profileDescription:
        if len(profileDescription.split('\n'))>2:
            profileDescriptionShort=''
    else:
        if '<br>' in profileDescription:
            if len(profileDescription.split('<br>'))>2:
                profileDescriptionShort=''
                profileDescription=profileDescription.replace('<br>','\n')
    # keep the profile description short
    if len(profileDescriptionShort)>256:
        profileDescriptionShort=''
    # remove formatting from profile description used on title
    avatarDescription=''
    if profileJson.get('summary'):
        avatarDescription=profileJson['summary'].replace('<br>','\n').replace('<p>','').replace('</p>','')
    profileHeaderStr='<div class="hero-image">'
    profileHeaderStr+='  <div class="hero-text">'
    profileHeaderStr+='    <img loading="lazy" src="'+profileJson['icon']['url']+'" title="'+avatarDescription+'" alt="'+avatarDescription+'" class="title">'
    profileHeaderStr+='    <h1>'+displayName+'</h1>'
    profileHeaderStr+='    <p><b>@'+nickname+'@'+domainFull+'</b></p>'
    profileHeaderStr+='    <p>'+profileDescriptionShort+'</p>'
    profileHeaderStr+=loginButton
    profileHeaderStr+='  </div>'
    profileHeaderStr+='</div>'

    profileStr=linkToTimelineStart + profileHeaderStr + linkToTimelineEnd + donateSection
    profileStr+='<div class="container">\n'
    profileStr+='  <center>'
    profileStr+='    <a href="'+actor+'"><button class="'+postsButton+'"><span>'+translate['Posts']+' </span></button></a>'
    profileStr+='    <a href="'+actor+'/following"><button class="'+followingButton+'"><span>'+translate['Following']+' </span></button></a>'
    profileStr+='    <a href="'+actor+'/followers"><button class="'+followersButton+'"><span>'+translate['Followers']+' </span></button></a>'
    profileStr+='    <a href="'+actor+'/roles"><button class="'+rolesButton+'"><span>'+translate['Roles']+' </span></button></a>'
    profileStr+='    <a href="'+actor+'/skills"><button class="'+skillsButton+'"><span>'+translate['Skills']+' </span></button></a>'
    profileStr+='    <a href="'+actor+'/shares"><button class="'+sharesButton+'"><span>'+translate['Shares']+' </span></button></a>'
    profileStr+=editProfileStr+logoutStr
    profileStr+='  </center>'
    profileStr+='</div>'

    profileStr+=followApprovalsSection
    
    cssFilename=baseDir+'/epicyon-profile.css'
    if os.path.isfile(baseDir+'/epicyon.css'):
        cssFilename=baseDir+'/epicyon.css'        
    with open(cssFilename, 'r') as cssFile:
        profileStyle = cssFile.read().replace('image.png',profileJson['image']['url'])

        licenseStr='<a href="https://gitlab.com/bashrc2/epicyon"><img loading="lazy" class="license" alt="'+translate['Get the source code']+'" title="'+translate['Get the source code']+'" src="/icons/agpl.png" /></a>'

        if selected=='posts':
            profileStr+= \
                htmlProfilePosts(recentPostsCache,maxRecentPosts, \
                                 translate, \
                                 baseDir,httpPrefix,authorized, \
                                 ocapAlways,nickname,domain,port, \
                                 session,wfRequest,personCache, \
                                 projectVersion)+licenseStr
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
                htmlProfileShares(actor,translate,nickname,domainFull,extraJson)+licenseStr
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
                         projectVersion,httpPrefix,nickname,domain,'outbox')
        if avatarUrl2:
            avatarUrl=avatarUrl2
        if displayName:
            titleStr=displayName+' '+titleStr

    buttonsStr=''
    if authorized:
        for b in buttons:
            if b=='block':
                buttonsStr+='<a href="/users/'+actorNickname+'?options='+followUrl+';1;'+avatarUrl+'"><button class="buttonunfollow">'+translate['Block']+'</button></a>'
                #buttonsStr+='<a href="/users/'+actorNickname+'?block='+followUrl+';'+avatarUrl+'"><button class="buttonunfollow">'+translate['Block']+'</button></a>'
            if b=='unfollow':
                buttonsStr+='<a href="/users/'+actorNickname+'?options='+followUrl+';1;'+avatarUrl+'"><button class="buttonunfollow">'+translate['Unfollow']+'</button></a>'
                #buttonsStr+='<a href="/users/'+actorNickname+'?unfollow='+followUrl+';'+avatarUrl+'"><button class="buttonunfollow">'+translate['Unfollow']+'</button></a>'

    resultStr='<div class="container">\n'
    resultStr+='<a href="'+followUrl+'">'
    resultStr+='<p><img loading="lazy" src="'+avatarUrl+'" alt=" ">\n'
    resultStr+=titleStr+'</a>'+buttonsStr+'</p>'
    resultStr+='</div>\n'
    return resultStr

def clickToDropDownScript() -> str:
    """Function run onclick to create a dropdown
    """
    script='function dropdown() {\n'
    script+='  document.getElementById("myDropdown").classList.toggle("show");\n'
    script+='}\n'
    return script

def cursorToEndOfMessageScript() -> str:
    """Moves the cursor to the end of the text in a textarea
    This avoids the cursor being in the wrong position when replying
    """
    script='function focusOnMessage() {\n'
    script+="  var replyTextArea = document.getElementById('message');\n"
    script+='  val = replyTextArea.value;\n'
    script+='  if ((val.length>0) && (val.charAt(val.length-1) != " ")) {\n'
    script+='    val += " ";\n'
    script+='  }\n'
    script+='  replyTextArea.focus();\n'
    script+='  replyTextArea.value="";\n'
    script+='  replyTextArea.value=val;\n'
    script+='}\n'
    script+="var replyTextArea = document.getElementById('message')\n"
    script+='replyTextArea.onFocus = function() {\n'
    script+='  focusOnMessage();'
    script+='}\n'
    return script

def contentWarningScript() -> str:
    """Returns a script used for content warnings
    """
    script='function showContentWarning(postID) {\n'
    script+='  var x = document.getElementById(postID);\n'
    script+='  if (x.style.display !== "block") {\n'
    script+='    x.style.display = "block";\n'
    script+='  } else {\n'
    script+='    x.style.display = "none";\n'
    script+='  }\n'
    script+='}\n'
    return script

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
            content=content+"<center><iframe loading=\"lazy\" src=\"https://player.vimeo.com/video/"+url+"\" width=\""+str(width)+"\" height=\""+str(height)+"\" frameborder=\"0\" allow=\"autoplay; fullscreen\" allowfullscreen></iframe></center>"
            return content

    videoSite='https://www.youtube.com'
    if '"'+videoSite in content:
        url=content.split('"'+videoSite)[1]
        if '"' in url:
            url=url.split('"')[0].replace('/watch?v=','/embed/')
            if '&' in url:
                url=url.split('&')[0]
            content=content+"<center><iframe loading=\"lazy\" src=\""+videoSite+url+"\" width=\""+str(width)+"\" height=\""+str(height)+"\" frameborder=\"0\" allow=\"autoplay; fullscreen\" allowfullscreen></iframe></center>"
            return content

    invidiousSites=('https://invidio.us','axqzx4s6s54s32yentfqojs3x5i7faxza6xo3ehd4bzzsg2ii4fv2iid.onion')
    for videoSite in invidiousSites:
        if '"'+videoSite in content:
            url=content.split('"'+videoSite)[1]
            if '"' in url:
                url=url.split('"')[0].replace('/watch?v=','/embed/')
                if '&' in url:
                    url=url.split('&')[0]
                content=content+"<center><iframe loading=\"lazy\" src=\""+videoSite+url+"\" width=\""+str(width)+"\" height=\""+str(height)+"\" frameborder=\"0\" allow=\"autoplay; fullscreen\" allowfullscreen></iframe></center>"
                return content

    videoSite='https://media.ccc.de'
    if '"'+videoSite in content:
        url=content.split('"'+videoSite)[1]
        if '"' in url:
            url=url.split('"')[0]
            if not url.endswith('/oembed'):
                url=url+'/oembed'
            content=content+"<center><iframe loading=\"lazy\" src=\""+videoSite+url+"\" width=\""+str(width)+"\" height=\""+str(height)+"\" frameborder=\"0\" allow=\"fullscreen\" allowfullscreen></iframe></center>"
            return content

    if '"https://' in content:
        # A selection of the current larger peertube sites, mostly French and German language
        # These have been chosen based on reported numbers of users and the content of each has not been reviewed, so mileage could vary
        peerTubeSites=('peertube.mastodon.host','open.tube','share.tube','tube.tr4sk.me','videos.elbinario.net','hkvideo.live','peertube.snargol.com','tube.22decembre.eu','tube.fabrigli.fr','libretube.net','libre.video','peertube.linuxrocks.online','spacepub.space','video.ploud.jp','video.omniatv.com','peertube.servebeer.com','tube.tchncs.de','tubee.fr','video.alternanet.fr','devtube.dev-wiki.de','video.samedi.pm','video.irem.univ-paris-diderot.fr','peertube.openstreetmap.fr','video.antopie.org','scitech.video','tube.4aem.com','video.ploud.fr','peervideo.net','video.valme.io','videos.pair2jeux.tube','vault.mle.party','hostyour.tv','diode.zone','visionon.tv','artitube.artifaille.fr','peertube.fr','peertube.live','tube.ac-lyon.fr','www.yiny.org','betamax.video','tube.piweb.be','pe.ertu.be','peertube.social','videos.lescommuns.org','peertube.nogafa.org','skeptikon.fr','video.tedomum.net','tube.p2p.legal','sikke.fi','exode.me','peertube.video')
        for site in peerTubeSites:
            if '"https://'+site in content:
                url=content.split('"https://'+site)[1]
                if '"' in url:
                    url=url.split('"')[0].replace('/watch/','/embed/')            
                    content=content+"<center><iframe loading=\"lazy\" sandbox=\"allow-same-origin allow-scripts\" src=\"https://"+site+url+"\" width=\""+str(width)+"\" height=\""+str(height)+"\" frameborder=\"0\" allow=\"autoplay; fullscreen\" allowfullscreen></iframe></center>"
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
        actorJson=loadJson(actorFilename)
        if actorJson:
            if actorJson.get('manuallyApprovesFollowers'):
                manuallyApprovesFollowers=actorJson['manuallyApprovesFollowers']
    return manuallyApprovesFollowers

def insertQuestion(baseDir: str,translate: {}, \
                   nickname: str,domain: str,port: int, \
                   content: str, \
                   postJsonObject: {},pageNumber: int) -> str:
    """ Inserts question selection into a post
    """
    if not isQuestion(postJsonObject):
        return content
    if len(postJsonObject['object']['oneOf'])==0:
        return content
    messageId=postJsonObject['id'].replace('/activity','')
    if '#' in messageId:
        messageId=messageId.split('#',1)[0]
    pageNumberStr=''
    if pageNumber:
        pageNumberStr='?page='+str(pageNumber)

    votesFilename= \
        baseDir+'/accounts/'+nickname+'@'+domain+'/questions.txt'

    showQuestionResults=False
    if os.path.isfile(votesFilename):
        if messageId in open(votesFilename).read():
            showQuestionResults=True

    if not showQuestionResults:
        # show the question options
        content+='<div class="question">'
        content+='<form method="POST" action="/users/'+nickname+'/question'+pageNumberStr+'">'
        content+='<input type="hidden" name="messageId" value="'+messageId+'"><br>'
        for choice in postJsonObject['object']['oneOf']:
            if not choice.get('type'):
                continue
            if not choice.get('name'):
                continue
            content+='<input type="radio" name="answer" value="'+choice['name']+'"> '+choice['name']+'<br><br>'
        content+='<input type="submit" value="'+translate['Vote']+'" class="vote"><br><br>'
        content+='</form></div>'
    else:
        # show the responses to a question
        content+='<div class="questionresult">'

        # get the maximum number of votes
        maxVotes=1
        for questionOption in postJsonObject['object']['oneOf']:
            if not questionOption.get('name'):
                continue
            if not questionOption.get('replies'):
                continue
            votes=0
            try:
                votes=int(questionOption['replies']['totalItems'])
            except:
                pass
            if votes>maxVotes:
                maxVotes=int(votes+1)

        # show the votes as sliders
        questionCtr=1
        for questionOption in postJsonObject['object']['oneOf']:
            if not questionOption.get('name'):
                continue
            if not questionOption.get('replies'):
                continue
            votes=0
            try:
                votes=int(questionOption['replies']['totalItems'])
            except:
                pass
            votesPercent=str(int(votes*100/maxVotes))
            content+='<p><input type="text" title="'+str(votes)+'" name="skillName'+str(questionCtr)+'" value="'+questionOption['name']+' ('+str(votes)+')" style="width:40%">'
            content+='<input type="range" min="1" max="100" class="slider" title="'+str(votes)+'" name="skillValue'+str(questionCtr)+'" value="'+votesPercent+'"></p>'
            questionCtr+=1
        content+='</div>'
    return content

def addEmojiToDisplayName(baseDir: str,httpPrefix: str, \
                          nickname: str,domain: str, \
                          displayName: str,inProfileName: bool) -> str:
    """Adds emoji icons to display names on individual posts
    """
    if ':' not in displayName:
        return displayName

    displayName=displayName.replace('<p>','').replace('</p>','')
    emojiTags={}
    print('TAG: displayName before tags: '+displayName)
    displayName= \
        addHtmlTags(baseDir,httpPrefix, \
                    nickname,domain,displayName,[],emojiTags)
    displayName=displayName.replace('<p>','').replace('</p>','')
    print('TAG: displayName after tags: '+displayName)
    # convert the emoji dictionary to a list
    emojiTagsList=[]
    for tagName,tag in emojiTags.items():
        emojiTagsList.append(tag)
    print('TAG: emoji tags list: '+str(emojiTagsList))
    if not inProfileName:
        displayName=replaceEmojiFromTags(displayName,emojiTagsList,'post header')
    else:
        displayName=replaceEmojiFromTags(displayName,emojiTagsList,'profile')
    print('TAG: displayName after tags 2: '+displayName)

    # remove any stray emoji
    while ':' in displayName:
        if '://' in displayName:
            break
        emojiStr=displayName.split(':')[1]
        prevDisplayName=displayName
        displayName=displayName.replace(':'+emojiStr+':','').strip()
        if prevDisplayName==displayName:
            break
        print('TAG: displayName after tags 3: '+displayName)
    print('TAG: displayName after tag replacements: '+displayName)

    return displayName

def postContainsPublic(postJsonObject: {}) -> bool:
    """Does the given post contain #Public
    """
    containsPublic=False
    if not postJsonObject['object'].get('to'):
        return containsPublic
        
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
    return containsPublic

def loadIndividualPostAsHtmlFromCache(baseDir: str,nickname: str,domain: str, \
                                      postJsonObject: {}) -> str:
    """If a cached html version of the given post exists then load it and
    return the html text
    This is much quicker than generating the html from the json object
    """
    cachedPostFilename=getCachedPostFilename(baseDir,nickname,domain,postJsonObject)

    postHtml=''
    if not cachedPostFilename:
        return postHtml
        
    if not os.path.isfile(cachedPostFilename):
        return postHtml
    
    tries=0
    while tries<3:
        try:
            with open(cachedPostFilename, 'r') as file:
                postHtml = file.read()
                break
        except Exception as e:
            print(e)
            # no sleep
            tries+=1
    if postHtml:
        return postHtml

def saveIndividualPostAsHtmlToCache(baseDir: str,nickname: str,domain: str, \
                                    postJsonObject: {},postHtml: str) -> bool:
    """Saves the given html for a post to a cache file
    This is so that it can be quickly reloaded on subsequent refresh of the timeline
    """
    htmlPostCacheDir=getCachedPostDirectory(baseDir,nickname,domain)
    cachedPostFilename=getCachedPostFilename(baseDir,nickname,domain,postJsonObject)

    # create the cache directory if needed
    if not os.path.isdir(htmlPostCacheDir):
        os.mkdir(htmlPostCacheDir)

    try:
        with open(cachedPostFilename, 'w') as fp:
            fp.write(postHtml)
            return True
    except Exception as e:
        print('ERROR: saving post to cache '+str(e))
    return False

def preparePostFromHtmlCache(postHtml: str,boxName: str,pageNumber: int) -> str:
    """Sets the page number on a cached html post
    """
    # if on the bookmarks timeline then remain there
    if boxName=='tlbookmarks':
        postHtml=postHtml.replace('?tl=inbox','?tl=tlbookmarks')
    return postHtml.replace(';-999;',';'+str(pageNumber)+';').replace('?page=-999','?page='+str(pageNumber))

def postIsMuted(baseDir: str,nickname: str,domain: str, postJsonObject: {},messageId: str) -> bool:
    """ Returns true if the given post is muted
    """
    isMuted=postJsonObject.get('muted')
    if isMuted==True or isMuted==False:
        return isMuted
    postDir=baseDir+'/accounts/'+nickname+'@'+domain
    muteFilename=postDir+'/inbox/'+messageId.replace('/','#')+'.json.muted'
    if os.path.isfile(muteFilename):
        return True
    muteFilename=postDir+'/outbox/'+messageId.replace('/','#')+'.json.muted'
    if os.path.isfile(muteFilename):
        return True
    muteFilename=baseDir+'/accounts/cache/announce/'+nickname+'/'+messageId.replace('/','#')+'.json.muted'
    if os.path.isfile(muteFilename):
        return True
    return False

def individualPostAsHtml(recentPostsCache: {},maxRecentPosts: int, \
                         iconsDir: str,translate: {}, \
                         pageNumber: int,baseDir: str, \
                         session,wfRequest: {},personCache: {}, \
                         nickname: str,domain: str,port: int, \
                         postJsonObject: {}, \
                         avatarUrl: str,showAvatarOptions: bool,
                         allowDeletion: bool, \
                         httpPrefix: str,projectVersion: str, \
                         boxName: str,showRepeats=True, \
                         showIcons=False, \
                         manuallyApprovesFollowers=False, \
                         showPublicOnly=False,
                         storeToCache=True) -> str:
    """ Shows a single post as html
    """
    postActor=postJsonObject['actor']

    # ZZZzzz
    if isPersonSnoozed(baseDir,nickname,domain,postActor):
        return ''

    avatarPosition=''
    messageId=''
    if postJsonObject.get('id'):
        messageId=postJsonObject['id'].replace('/activity','')

    messageIdStr=''
    if messageId:
        messageIdStr=';'+messageId

    fullDomain=domain
    if port:
        if port!=80 and port!=443:
            if ':' not in domain:
                fullDomain=domain+':'+str(port)

    pageNumberParam=''
    if pageNumber:
        pageNumberParam='?page='+str(pageNumber)

    if not showPublicOnly and storeToCache and boxName!='tlmedia':
        # update avatar if needed
        if not avatarUrl:
            avatarUrl=getPersonAvatarUrl(baseDir,postActor,personCache)
        updateAvatarImageCache(session,baseDir,httpPrefix,postActor,avatarUrl,personCache)

        postHtml= \
            loadIndividualPostAsHtmlFromCache(baseDir,nickname,domain, \
                                              postJsonObject)
        if postHtml:
            postHtml=preparePostFromHtmlCache(postHtml,boxName,pageNumber)
            updateRecentPostsCache(recentPostsCache,maxRecentPosts, \
                                   postJsonObject,postHtml)
            return postHtml

    if not avatarUrl:
        avatarUrl=getPersonAvatarUrl(baseDir,postActor,personCache)
        avatarUrl=updateAvatarImageCache(session,baseDir,httpPrefix,postActor,avatarUrl,personCache)
    else:
        updateAvatarImageCache(session,baseDir,httpPrefix,postActor,avatarUrl,personCache)

    if not avatarUrl:
        avatarUrl=postActor+'/avatar.png'

    if fullDomain not in postActor:
        inboxUrl,pubKeyId,pubKey,fromPersonId,sharedInbox,capabilityAcquisition,avatarUrl2,displayName = \
            getPersonBox(baseDir,session,wfRequest,personCache, \
                         projectVersion,httpPrefix,nickname,domain,'outbox')
        if avatarUrl2:
            avatarUrl=avatarUrl2
        if displayName:
            if ':' in displayName:
                displayName= \
                    addEmojiToDisplayName(baseDir,httpPrefix, \
                                          nickname,domain, \
                                          displayName,False)
            titleStr=displayName+' '+titleStr

    avatarLink='    <a href="'+postActor+'">'
    avatarLink+='    <img loading="lazy" src="'+avatarUrl+'" title="'+translate['Show profile']+'" alt=" "'+avatarPosition+'/></a>'
    
    if showAvatarOptions and fullDomain+'/users/'+nickname not in postActor:
        avatarLink='    <a href="/users/'+nickname+'?options='+postActor+';'+str(pageNumber)+';'+avatarUrl+messageIdStr+'">'
        avatarLink+='    <img loading="lazy" title="'+translate['Show options for this person']+'" src="'+avatarUrl+'" '+avatarPosition+'/></a>'
    avatarImageInPost='  <div class="timeline-avatar">'+avatarLink+'</div>'

    # don't create new html within the bookmarks timeline
    # it should already have been created for the inbox
    if boxName=='tlbookmarks':
        return ''

    timelinePostBookmark=postJsonObject['id'].replace('/activity','').replace('://','-').replace('/','-')

    # If this is the inbox timeline then don't show the repeat icon on any DMs
    showRepeatIcon=showRepeats
    showDMicon=False
    if showRepeats:
        if isDM(postJsonObject):
            showRepeatIcon=False
            showDMicon=True
    
    titleStr=''
    galleryStr=''
    isAnnounced=False
    if postJsonObject['type']=='Announce':
        postJsonAnnounce= \
            downloadAnnounce(session,baseDir,httpPrefix,nickname,domain,postJsonObject,projectVersion)
        if not postJsonAnnounce:
            return ''
        postJsonObject=postJsonAnnounce
        isAnnounced=True

    if not isinstance(postJsonObject['object'], dict):
        return ''

    # if this post should be public then check its recipients
    if showPublicOnly:
        if not postContainsPublic(postJsonObject):
            return ''
        
    isModerationPost=False
    if postJsonObject['object'].get('moderationStatus'):
        isModerationPost=True
    containerClass='container'
    containerClassIcons='containericons'
    timeClass='time-right'
    actorNickname=getNicknameFromActor(postActor)
    if not actorNickname:
        # single user instance
        actorNickname='dev'
    actorDomain,actorPort=getDomainFromActor(postActor)

    displayName=getDisplayName(baseDir,postActor,personCache)
    if displayName:
        if ':' in displayName:
            displayName= \
                addEmojiToDisplayName(baseDir,httpPrefix, \
                                      nickname,domain, \
                                      displayName,False)
        titleStr+='<a href="/users/'+nickname+'?options='+postActor+';'+str(pageNumber)+';'+avatarUrl+messageIdStr+'">'+displayName+'</a>'
    else:
        if not messageId:
            #pprint(postJsonObject)
            print('ERROR: no messageId')
        if not actorNickname:
            #pprint(postJsonObject)
            print('ERROR: no actorNickname')
        if not actorDomain:
            #pprint(postJsonObject)
            print('ERROR: no actorDomain')
        titleStr+='<a href="/users/'+nickname+'?options='+postActor+';'+str(pageNumber)+';'+avatarUrl+messageIdStr+'">@'+actorNickname+'@'+actorDomain+'</a>'

    # Show a DM icon for DMs in the inbox timeline
    if showDMicon:
        titleStr=titleStr+' <img loading="lazy" src="/'+iconsDir+'/dm.png" class="DMicon"/>'

    replyStr=''
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
                        
        replyStr=''
        if not isModerationPost and showRepeatIcon:
            if not manuallyApprovesFollowers:
                replyStr+= \
                    '<a href="/users/'+nickname+'?replyto='+replyToLink+ \
                    '?actor='+postJsonObject['actor']+ \
                    '" title="'+translate['Reply to this post']+'">'
            else:
                replyStr+= \
                    '<a href="/users/'+nickname+'?replyfollowers='+replyToLink+ \
                    '?actor='+postJsonObject['actor']+ \
                    '" title="'+translate['Reply to this post']+'">'
        else:
            replyStr+= \
                '<a href="/users/'+nickname+'?replydm='+replyToLink+ \
                '?actor='+postJsonObject['actor']+ \
                '" title="'+translate['Reply to this post']+'">'
        replyStr+='<img loading="lazy" title="'+translate['Reply to this post']+' |" alt="'+translate['Reply to this post']+' |" src="/'+iconsDir+'/reply.png"/></a>'

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
            '<a href="/users/'+nickname+'?'+announceLink+'='+postJsonObject['object']['id']+pageNumberParam+ \
            '?actor='+postJsonObject['actor']+ \
            '?bm='+timelinePostBookmark+ \
            '?tl='+boxName+'" title="'+announceTitle+'">'
        announceStr+='<img loading="lazy" title="'+translate['Repeat this post']+' |" alt="'+translate['Repeat this post']+' |" src="/'+iconsDir+'/'+announceIcon+'"/></a>'

    likeStr=''
    if not isModerationPost:
        likeIcon='like_inactive.png'
        likeLink='like'
        likeTitle=translate['Like this post']
        if noOfLikes(postJsonObject)>0:
            likeIcon='like.png'
            if likedByPerson(postJsonObject,nickname,fullDomain):
                likeLink='unlike'
                likeTitle=translate['Undo the like']
        likeStr= \
            '<a href="/users/' + nickname + '?' + \
            likeLink + '=' + postJsonObject['object']['id'] + pageNumberParam + \
            '?actor='+postJsonObject['actor']+ \
            '?bm='+timelinePostBookmark+ \
            '?tl='+boxName+'" title="'+likeTitle+'">'
        likeStr+='<img loading="lazy" title="'+likeTitle+' |" alt="'+likeTitle+' |" src="/'+iconsDir+'/'+likeIcon+'"/></a>'

    bookmarkStr=''
    if not isModerationPost:
        bookmarkIcon='bookmark_inactive.png'
        bookmarkLink='bookmark'
        bookmarkTitle=translate['Bookmark this post']
        if bookmarkedByPerson(postJsonObject,nickname,fullDomain):
            bookmarkIcon='bookmark.png'
            bookmarkLink='unbookmark'
            bookmarkTitle=translate['Undo the bookmark']
        bookmarkStr= \
            '<a href="/users/' + nickname + '?' + \
            bookmarkLink + '=' + postJsonObject['object']['id'] + pageNumberParam + \
            '?actor='+postJsonObject['actor']+ \
            '?bm='+timelinePostBookmark+ \
            '?tl='+boxName+'" title="'+bookmarkTitle+'">'
        bookmarkStr+='<img loading="lazy" title="'+bookmarkTitle+' |" alt="'+bookmarkTitle+' |" src="/'+iconsDir+'/'+bookmarkIcon+'"/></a>'

    isMuted=postIsMuted(baseDir,nickname,domain,postJsonObject,messageId)

    deleteStr=''
    muteStr=''
    if allowDeletion or \
       ('/'+fullDomain+'/' in postActor and \
        messageId.startswith(postActor)):
        if '/users/'+nickname+'/' in messageId:
            deleteStr='<a href="/users/'+nickname+'?delete='+messageId+pageNumberParam+'" title="'+translate['Delete this post']+'">'
            deleteStr+='<img loading="lazy" alt="'+translate['Delete this post']+' |" title="'+translate['Delete this post']+' |" src="/'+iconsDir+'/delete.png"/></a>'
    else:
        if not isMuted:
            muteStr='<a href="/users/'+nickname+'?mute='+messageId+pageNumberParam+'?tl='+boxName+'?bm='+timelinePostBookmark+'" title="'+translate['Mute this post']+'">'
            muteStr+='<img loading="lazy" alt="'+translate['Mute this post']+' |" title="'+translate['Mute this post']+' |" src="/'+iconsDir+'/mute.png"/></a>'
        else:
            muteStr='<a href="/users/'+nickname+'?unmute='+messageId+pageNumberParam+'?tl='+boxName+'?bm='+timelinePostBookmark+'" title="'+translate['Undo mute']+'">'
            muteStr+='<img loading="lazy" alt="'+translate['Undo mute']+' |" title="'+translate['Undo mute']+' |" src="/'+iconsDir+'/unmute.png"/></a>'
            
    replyAvatarImageInPost=''
    if showRepeatIcon:
        if isAnnounced:
            if postJsonObject['object'].get('attributedTo'):
                if postJsonObject['object']['attributedTo'].startswith(postActor):
                    titleStr+=' <img loading="lazy" title="'+translate['announces']+'" alt="'+translate['announces']+'" src="/'+iconsDir+'/repeat_inactive.png" class="announceOrReply"/>'
                else:
                    announceNickname=getNicknameFromActor(postJsonObject['object']['attributedTo'])
                    if announceNickname:
                        announceDomain,announcePort=getDomainFromActor(postJsonObject['object']['attributedTo'])
                        getPersonFromCache(baseDir,postJsonObject['object']['attributedTo'],personCache)
                        announceDisplayName=getDisplayName(baseDir,postJsonObject['object']['attributedTo'],personCache)
                        if announceDisplayName:
                            if ':' in announceDisplayName:
                                announceDisplayName= \
                                    addEmojiToDisplayName(baseDir,httpPrefix, \
                                                          nickname,domain, \
                                                          announceDisplayName,False)
                            titleStr+=' <img loading="lazy" title="'+translate['announces']+'" alt="'+translate['announces']+'" src="/'+iconsDir+'/repeat_inactive.png" class="announceOrReply"/> <a href="'+postJsonObject['object']['id']+'">'+announceDisplayName+'</a>'
                            # show avatar of person replied to
                            announceActor=postJsonObject['object']['attributedTo']
                            announceAvatarUrl=getPersonAvatarUrl(baseDir,announceActor,personCache)
                            if announceAvatarUrl:
                                replyAvatarImageInPost= \
                                    '<div class="timeline-avatar-reply">' \
                                    '<a href="/users/'+nickname+'?options='+announceActor+';'+str(pageNumber)+';'+announceAvatarUrl+messageIdStr+'">' \
                                    '<img loading="lazy" src="'+announceAvatarUrl+'" ' \
                                    'title="'+translate['Show options for this person']+ \
                                    '" alt=" "'+avatarPosition+'/></a></div>'
                        else:
                            titleStr+=' <img loading="lazy" title="'+translate['announces']+'" alt="'+translate['announces']+'" src="/'+iconsDir+'/repeat_inactive.png" class="announceOrReply"/> <a href="'+postJsonObject['object']['id']+'">@'+announceNickname+'@'+announceDomain+'</a>'
                    else:
                        titleStr+=' <img loading="lazy" title="'+translate['announces']+'" alt="'+translate['announces']+'" src="/'+iconsDir+'/repeat_inactive.png" class="announceOrReply"/> <a href="'+postJsonObject['object']['id']+'">@unattributed</a>'
            else:
                titleStr+=' <img loading="lazy" title="'+translate['announces']+'" alt="'+translate['announces']+'" src="/'+iconsDir+'/repeat_inactive.png" class="announceOrReply"/> <a href="'+postJsonObject['object']['id']+'">@unattributed</a>'
        else:
            if postJsonObject['object'].get('inReplyTo'):
                containerClassIcons='containericons darker'
                containerClass='container darker'
                #avatarPosition=' class="right"'
                if postJsonObject['object']['inReplyTo'].startswith(postActor):
                    titleStr+=' <img loading="lazy" title="'+translate['replying to themselves']+'" alt="'+translate['replying to themselves']+'" src="/'+iconsDir+'/reply.png" class="announceOrReply"/>'
                else:
                    if '/statuses/' in postJsonObject['object']['inReplyTo']:
                        replyActor=postJsonObject['object']['inReplyTo'].split('/statuses/')[0]
                        replyNickname=getNicknameFromActor(replyActor)
                        if replyNickname:
                            replyDomain,replyPort=getDomainFromActor(replyActor)
                            if replyNickname and replyDomain:
                                getPersonFromCache(baseDir,replyActor,personCache)
                                replyDisplayName=getDisplayName(baseDir,replyActor,personCache)
                                if replyDisplayName:
                                    if ':' in replyDisplayName:
                                        replyDisplayName= \
                                            addEmojiToDisplayName(baseDir,httpPrefix, \
                                                                  nickname,domain, \
                                                                  replyDisplayName,False)
                                    titleStr+=' <img loading="lazy" title="'+translate['replying to']+'" alt="'+translate['replying to']+'" src="/'+iconsDir+'/reply.png" class="announceOrReply"/> <a href="'+postJsonObject['object']['inReplyTo']+'">'+replyDisplayName+'</a>'

                                    # show avatar of person replied to
                                    replyAvatarUrl=getPersonAvatarUrl(baseDir,replyActor,personCache)
                                    if replyAvatarUrl:
                                        replyAvatarImageInPost='<div class="timeline-avatar-reply">'
                                        replyAvatarImageInPost+='<a href="/users/'+nickname+'?options='+replyActor+';'+str(pageNumber)+';'+replyAvatarUrl+messageIdStr+'">'
                                        replyAvatarImageInPost+='<img loading="lazy" src="'+replyAvatarUrl+'" '
                                        replyAvatarImageInPost+='title="'+translate['Show profile']
                                        replyAvatarImageInPost+='" alt=" "'+avatarPosition+'/></a></div>'
                                else:
                                    titleStr+=' <img loading="lazy" title="'+translate['replying to']+'" alt="'+translate['replying to']+'" src="/'+iconsDir+'/reply.png" class="announceOrReply"/> <a href="'+postJsonObject['object']['inReplyTo']+'">@'+replyNickname+'@'+replyDomain+'</a>'
                        else:
                            titleStr+=' <img loading="lazy" title="'+translate['replying to']+'" alt="'+translate['replying to']+'" src="/'+iconsDir+'/reply.png" class="announceOrReply"/> <a href="'+postJsonObject['object']['inReplyTo']+'">@unknown</a>'
                    else:
                        postDomain=postJsonObject['object']['inReplyTo'].replace('https://','').replace('http://','').replace('dat://','')
                        if '/' in postDomain:
                            postDomain=postDomain.split('/',1)[0]
                        if postDomain:
                            titleStr+=' <img loading="lazy" title="'+translate['replying to']+'" alt="'+translate['replying to']+'" src="/'+iconsDir+'/reply.png" class="announceOrReply"/> <a href="'+postJsonObject['object']['inReplyTo']+'">'+postDomain+'</a>'
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
                           attach['url'].endswith('.webp') or \
                           attach['url'].endswith('.gif'):
                            if attachmentCtr>0:
                                attachmentStr+='<br>'
                            if boxName=='tlmedia':
                                galleryStr+='<div class="gallery">\n'
                                if not isMuted:
                                    galleryStr+='  <a href="'+attach['url']+'">\n'
                                    galleryStr+='    <img loading="lazy" src="'+attach['url']+'" alt="" title="">\n'
                                    galleryStr+='  </a>\n'
                                if postJsonObject['object'].get('url'):
                                    imagePostUrl=postJsonObject['object']['url']
                                else:
                                    imagePostUrl=postJsonObject['object']['id']
                                if imageDescription and not isMuted:
                                    galleryStr+='  <a href="'+imagePostUrl+'" class="gallerytext"><div class="gallerytext">'+imageDescription+'</div></a>\n'
                                else:
                                    galleryStr+='<label class="transparent">---</label><br>'
                                galleryStr+='  <div class="mediaicons">\n'
                                galleryStr+='    '+replyStr+announceStr+likeStr+bookmarkStr+deleteStr+muteStr+'\n'
                                galleryStr+='  </div>\n'
                                galleryStr+='  <div class="mediaavatar">\n'
                                galleryStr+='    '+avatarLink+'\n'
                                galleryStr+='  </div>\n'
                                galleryStr+='</div>\n'

                            attachmentStr+='<a href="'+attach['url']+'">'
                            attachmentStr+='<img loading="lazy" src="'+attach['url']+'" alt="'+imageDescription+'" title="'+imageDescription+'" class="attachment"></a>\n'
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
                            if boxName=='tlmedia':
                                galleryStr+='<div class="gallery">\n'
                                if not isMuted:
                                    galleryStr+='  <a href="'+attach['url']+'">\n'
                                    galleryStr+='    <video width="600" height="400" controls>\n'
                                    galleryStr+='      <source src="'+attach['url']+'" alt="'+imageDescription+'" title="'+imageDescription+'" class="attachment" type="video/'+extension.replace('.','')+'">'
                                    galleryStr+=translate['Your browser does not support the video tag.']
                                    galleryStr+='    </video>\n'
                                    galleryStr+='  </a>\n'
                                if postJsonObject['object'].get('url'):
                                    videoPostUrl=postJsonObject['object']['url']
                                else:
                                    videoPostUrl=postJsonObject['object']['id']
                                if imageDescription and not isMuted:
                                    galleryStr+='  <a href="'+videoPostUrl+'" class="gallerytext"><div class="gallerytext">'+imageDescription+'</div></a>\n'
                                else:
                                    galleryStr+='<label class="transparent">---</label><br>'
                                galleryStr+='  <div class="mediaicons">\n'
                                galleryStr+='    '+replyStr+announceStr+likeStr+bookmarkStr+deleteStr+muteStr+'\n'
                                galleryStr+='  </div>\n'
                                galleryStr+='  <div class="mediaavatar">\n'
                                galleryStr+='    '+avatarLink+'\n'
                                galleryStr+='  </div>\n'
                                galleryStr+='</div>\n'

                            attachmentStr+='<center><video width="400" height="300" controls>'
                            attachmentStr+='<source src="'+attach['url']+'" alt="'+imageDescription+'" title="'+imageDescription+'" class="attachment" type="video/'+extension.replace('.','')+'">'
                            attachmentStr+=translate['Your browser does not support the video tag.']
                            attachmentStr+='</video></center>'
                            attachmentCtr+=1
                    elif mediaType=='audio/mpeg' or \
                         mediaType=='audio/ogg':
                        extension='.mp3'
                        if attach['url'].endswith('.ogg'):
                            extension='.ogg'                            
                        if attach['url'].endswith(extension):
                            if attachmentCtr>0:
                                attachmentStr+='<br>'
                            if boxName=='tlmedia':
                                galleryStr+='<div class="gallery">\n'
                                if not isMuted:
                                    galleryStr+='  <a href="'+attach['url']+'">\n'
                                    galleryStr+='    <audio controls>\n'
                                    galleryStr+='      <source src="'+attach['url']+'" alt="'+imageDescription+'" title="'+imageDescription+'" class="attachment" type="audio/'+extension.replace('.','')+'">'
                                    galleryStr+=translate['Your browser does not support the audio tag.']
                                    galleryStr+='    </audio>\n'
                                    galleryStr+='  </a>\n'
                                if postJsonObject['object'].get('url'):
                                    audioPostUrl=postJsonObject['object']['url']
                                else:
                                    audioPostUrl=postJsonObject['object']['id']
                                if imageDescription and not isMuted:
                                    galleryStr+='  <a href="'+audioPostUrl+'" class="gallerytext"><div class="gallerytext">'+imageDescription+'</div></a>\n'
                                else:
                                    galleryStr+='<label class="transparent">---</label><br>'
                                galleryStr+='  <div class="mediaicons">\n'
                                galleryStr+='    '+replyStr+announceStr+likeStr+bookmarkStr+deleteStr+muteStr+'\n'
                                galleryStr+='  </div>\n'
                                galleryStr+='  <div class="mediaavatar">\n'
                                galleryStr+='    '+avatarLink+'\n'
                                galleryStr+='  </div>\n'
                                galleryStr+='</div>\n'

                            attachmentStr+='<center><audio controls>'
                            attachmentStr+='<source src="'+attach['url']+'" alt="'+imageDescription+'" title="'+imageDescription+'" class="attachment" type="audio/'+extension.replace('.','')+'">'
                            attachmentStr+=translate['Your browser does not support the audio tag.']
                            attachmentStr+='</audio></center>'
                            attachmentCtr+=1
            attachmentStr+='<br></div>'

    publishedStr=''
    if postJsonObject['object'].get('published'):
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
    footerStr='<a href="'+messageId+'" class="'+timeClass+'">'+publishedStr+'</a>\n'

    # change the background color for DMs in inbox timeline
    if showDMicon:
        containerClassIcons='containericons dm'
        containerClass='container dm'

    if showIcons:
        footerStr='<div class="'+containerClassIcons+'">'
        footerStr+=replyStr+announceStr+likeStr+bookmarkStr+deleteStr+muteStr
        footerStr+='<a href="'+messageId+'" class="'+timeClass+'">'+publishedStr+'</a>\n'
        footerStr+='</div>'

    if not postJsonObject['object'].get('sensitive'):
        postJsonObject['object']['sensitive']=False

    # add an extra line if there is a content warning, for better vertical spacing on mobile
    if postJsonObject['object']['sensitive']:        
        footerStr='<br>'+footerStr

    if not postJsonObject['object'].get('summary'):
        postJsonObject['object']['summary']=''

    if not postJsonObject['object'].get('content'):
        return ''
    objectContent=removeLongWords(postJsonObject['object']['content'],40,[])
    if not postJsonObject['object']['sensitive']:
        contentStr=objectContent+attachmentStr
        contentStr=addEmbeddedElements(translate,contentStr)
        contentStr=insertQuestion(baseDir,translate,nickname,domain,port, \
                                  contentStr,postJsonObject,pageNumber)
    else:
        postID='post'+str(createPassword(8))
        contentStr=''
        if postJsonObject['object'].get('summary'):
            contentStr+='<b>'+postJsonObject['object']['summary']+'</b> '
            if isModerationPost:
                containerClass='container report'
        contentStr+='<button class="cwButton" onclick="showContentWarning('+"'"+postID+"'"+')">'+translate['SHOW MORE']+'</button>'
        contentStr+='<div class="cwText" id="'+postID+'">'
        contentStr+=objectContent+attachmentStr
        contentStr=addEmbeddedElements(translate,contentStr)
        contentStr=insertQuestion(baseDir,translate,nickname,domain,port, \
                                  contentStr,postJsonObject,pageNumber)
        contentStr+='</div>'

    if postJsonObject['object'].get('tag'):
        contentStr=replaceEmojiFromTags(contentStr,postJsonObject['object']['tag'],'content')

    if isMuted:
        contentStr=''
    else:
        contentStr='<div class="message">'+contentStr+'</div>'

    postHtml=''
    if boxName!='tlmedia':
        postHtml='<div id="'+timelinePostBookmark+'" class="'+containerClass+'">\n'
        postHtml+=avatarImageInPost
        postHtml+='<p class="post-title">'+titleStr+replyAvatarImageInPost+'</p>'
        postHtml+=contentStr+footerStr
        postHtml+='</div>\n'
    else:
        postHtml=galleryStr

    if not showPublicOnly and storeToCache and \
       boxName!='tlmedia'and boxName!='tlbookmarks':
        saveIndividualPostAsHtmlToCache(baseDir,nickname,domain, \
                                        postJsonObject,postHtml)
        updateRecentPostsCache(recentPostsCache,maxRecentPosts, \
                               postJsonObject,postHtml)

    return postHtml

def isQuestion(postObjectJson: {}) -> bool:
    """ is the given post a question?
    """
    if postObjectJson['type']!='Create' and \
       postObjectJson['type']!='Update':
        return False
    if not isinstance(postObjectJson['object'], dict):
        return False
    if not postObjectJson['object'].get('type'):
        return False
    if postObjectJson['object']['type']!='Question':
        return False
    if not postObjectJson['object'].get('oneOf'):
        return False
    if not isinstance(postObjectJson['object']['oneOf'], list):
        return False
    return True

def htmlTimeline(defaultTimeline: str, \
                 recentPostsCache: {},maxRecentPosts: int, \
                 translate: {},pageNumber: int, \
                 itemsPerPage: int,session,baseDir: str, \
                 wfRequest: {},personCache: {}, \
                 nickname: str,domain: str,port: int,timelineJson: {}, \
                 boxName: str,allowDeletion: bool, \
                 httpPrefix: str,projectVersion: str, \
                 manuallyApproveFollowers: bool) -> str:
    """Show the timeline as html
    """
    accountDir=baseDir+'/accounts/'+nickname+'@'+domain    

    # should the calendar icon be highlighted?
    calendarImage='calendar.png'
    calendarPath='/calendar'
    calendarFile=accountDir+'/.newCalendar'
    if os.path.isfile(calendarFile):
        calendarImage='calendar_notify.png'
        with open(calendarFile, 'r') as calfile:
            calendarPath=calfile.read().replace('##sent##','').replace('\n', '')

    # should the DM button be highlighted?
    newDM=False
    dmFile=accountDir+'/.newDM'
    if os.path.isfile(dmFile):
        newDM=True
        if boxName=='dm':
            os.remove(dmFile)

    # should the Replies button be highlighted?
    newReply=False
    replyFile=accountDir+'/.newReply'
    if os.path.isfile(replyFile):
        newReply=True
        if boxName=='tlreplies':
            os.remove(replyFile)

    # should the Shares button be highlighted?
    newShare=False
    newShareFile=accountDir+'/.newShare'
    if os.path.isfile(newShareFile):
        newShare=True
        if boxName=='tlshares':
            os.remove(newShareFile)

    # should the Moderation button be highlighted?
    newReport=False
    newReportFile=accountDir+'/.newReport'
    if os.path.isfile(newReportFile):
        newReport=True
        if boxName=='moderation':
            os.remove(newReportFile)

    iconsDir=getIconsDir(baseDir)
    cssFilename=baseDir+'/epicyon-profile.css'
    if os.path.isfile(baseDir+'/epicyon.css'):
        cssFilename=baseDir+'/epicyon.css'

    bannerFile='banner.png'
    bannerFilename=baseDir+'/accounts/'+nickname+'@'+domain+'/'+bannerFile
    if not os.path.isfile(bannerFilename):
        bannerFile='banner.jpg'
        bannerFilename=baseDir+'/accounts/'+nickname+'@'+domain+'/'+bannerFile
    if not os.path.isfile(bannerFilename):
        bannerFile='banner.gif'
        bannerFilename=baseDir+'/accounts/'+nickname+'@'+domain+'/'+bannerFile
    if not os.path.isfile(bannerFilename):
        bannerFile='banner.webp'
    
    with open(cssFilename, 'r') as cssFile:        
        profileStyle = \
            cssFile.read().replace('banner.png', \
                                   '/users/'+nickname+'/'+bannerFile)
        if httpPrefix!='https':
            profileStyle=profileStyle.replace('https://',httpPrefix+'://')

    moderator=isModerator(baseDir,nickname)

    inboxButton='button'
    dmButton='button'
    if newDM:
        dmButton='buttonhighlighted'
    repliesButton='button'
    if newReply:
        repliesButton='buttonhighlighted'
    mediaButton='button'
    bookmarksButton='button'
    sentButton='button'
    sharesButton='button'
    if newShare:
        sharesButton='buttonhighlighted'
    moderationButton='button'
    if newReport:
        moderationButton='buttonhighlighted'
    if boxName=='inbox':
        inboxButton='buttonselected'
    elif boxName=='dm':
        dmButton='buttonselected'
        if newDM:
            dmButton='buttonselectedhighlighted'
    elif boxName=='tlreplies':
        repliesButton='buttonselected'
        if newReply:
            repliesButton='buttonselectedhighlighted'
    elif boxName=='tlmedia':
        mediaButton='buttonselected'
    elif boxName=='outbox':
        sentButton='buttonselected'
    elif boxName=='moderation':
        moderationButton='buttonselected'
        if newReport:
            moderationButton='buttonselectedhighlighted'
    elif boxName=='tlshares':
        sharesButton='buttonselected'
        if newShare:
            sharesButton='buttonselectedhighlighted'
    elif boxName=='tlbookmarks':
        bookmarksButton='buttonselected'

    fullDomain=domain
    if port!=80 and port!=443:
        if ':' not in domain:
            fullDomain=domain+':'+str(port)
    actor=httpPrefix+'://'+fullDomain+'/users/'+nickname

    showIndividualPostIcons=True
    
    followApprovals=''
    followRequestsFilename= \
        baseDir+'/accounts/'+nickname+'@'+domain+'/followrequests.txt'
    if os.path.isfile(followRequestsFilename):
        with open(followRequestsFilename,'r') as f:
            for line in f:
                if len(line)>0:
                    # show follow approvals icon
                    followApprovals='<a href="'+actor+'/followers"><img loading="lazy" class="timelineicon" alt="'+translate['Approve follow requests']+'" title="'+translate['Approve follow requests']+'" src="/'+iconsDir+'/person.png"/></a>'
                    break

    moderationButtonStr=''
    if moderator:
        moderationButtonStr='<a href="'+actor+'/moderation"><button class="'+moderationButton+'"><span>'+translate['Mod']+' </span></button></a>'

    sharesButtonStr='<a href="'+actor+'/tlshares"><button class="'+sharesButton+'"><span>'+translate['Shares']+' </span></button></a>'

    bookmarksButtonStr='<a href="'+actor+'/tlbookmarks"><button class="'+bookmarksButton+'"><span>'+translate['Bookmarks']+' </span></button></a>'

    tlStr=htmlHeader(cssFilename,profileStyle)
    #if (boxName=='inbox' or boxName=='dm') and pageNumber==1:
        # refresh if on the first page of the inbox and dm timeline
        #tlStr=htmlHeader(cssFilename,profileStyle,240)

    if boxName!='dm':
        if not manuallyApproveFollowers:
            newPostButtonStr='<a href="'+actor+'/newpost"><img loading="lazy" src="/'+iconsDir+'/newpost.png" title="'+translate['Create a new post']+'" alt="'+translate['Create a new post']+'" class="timelineicon"/></a>'
        else:
            newPostButtonStr='<a href="'+actor+'/newfollowers"><img loading="lazy" src="/'+iconsDir+'/newpost.png" title="'+translate['Create a new post']+'" alt="'+translate['Create a new post']+'" class="timelineicon"/></a>'
    else:
        newPostButtonStr='<a href="'+actor+'/newdm"><img loading="lazy" src="/'+iconsDir+'/newpost.png" title="'+translate['Create a new DM']+'" alt="'+translate['Create a new DM']+'" class="timelineicon"/></a>'

    # This creates a link to the profile page when viewed in lynx, but should be invisible in a graphical web browser
    tlStr+='<a href="/users/'+nickname+'"><label class="transparent">'+translate['Switch to profile view']+'</label></a>'
    
    # banner and row of buttons
    tlStr+='<a href="/users/'+nickname+'" title="'+translate['Switch to profile view']+'" alt="'+translate['Switch to profile view']+'">'
    tlStr+='<div class="timeline-banner">'
    tlStr+='</div></a>'
    tlStr+='<div class="container">\n'
    if defaultTimeline!='tlmedia':
        tlStr+='    <a href="'+actor+'/inbox"><button class="'+inboxButton+'"><span>'+translate['Inbox']+'</span></button></a>'
    else:
        tlStr+='    <a href="'+actor+'/tlmedia"><button class="'+mediaButton+'"><span>'+translate['Media']+'</span></button></a>'
    tlStr+='    <a href="'+actor+'/dm"><button class="'+dmButton+'"><span>'+translate['DM']+'</span></button></a>'
    tlStr+='    <a href="'+actor+'/tlreplies"><button class="'+repliesButton+'"><span>'+translate['Replies']+'</span></button></a>'
    if defaultTimeline!='tlmedia':
        tlStr+='    <a href="'+actor+'/tlmedia"><button class="'+mediaButton+'"><span>'+translate['Media']+'</span></button></a>'
    else:
        tlStr+='    <a href="'+actor+'/inbox"><button class="'+inboxButton+'"><span>'+translate['Inbox']+'</span></button></a>'
    tlStr+='    <a href="'+actor+'/outbox"><button class="'+sentButton+'"><span>'+translate['Outbox']+'</span></button></a>'
    tlStr+=sharesButtonStr+bookmarksButtonStr+moderationButtonStr+newPostButtonStr
    tlStr+='    <a href="'+actor+'/search"><img loading="lazy" src="/'+iconsDir+'/search.png" title="'+translate['Search and follow']+'" alt="'+translate['Search and follow']+'" class="timelineicon"/></a>'
    tlStr+='    <a href="'+actor+calendarPath+'"><img loading="lazy" src="/'+iconsDir+'/'+calendarImage+'" title="'+translate['Calendar']+'" alt="'+translate['Calendar']+'" class="timelineicon"/></a>'
    tlStr+='    <a href="'+actor+'/'+boxName+'"><img loading="lazy" src="/'+iconsDir+'/refresh.png" title="'+translate['Refresh']+'" alt="'+translate['Refresh']+'" class="timelineicon"/></a>'
    tlStr+=followApprovals
    tlStr+='</div>'

    # second row of buttons for moderator actions
    if moderator and boxName=='moderation':
        tlStr+='<form method="POST" action="/users/'+nickname+'/moderationaction">'
        tlStr+='<div class="container">\n'
        tlStr+='    <b>'+translate['Nickname or URL. Block using *@domain or nickname@domain']+'</b><br>\n'
        tlStr+='    <input type="text" name="moderationAction" value="" autofocus><br>\n'
        tlStr+='    <input type="submit" title="'+translate['Remove the above item']+'" name="submitRemove" value="'+translate['Remove']+'">'
        tlStr+='    <input type="submit" title="'+translate['Suspend the above account nickname']+'" name="submitSuspend" value="'+translate['Suspend']+'">'
        tlStr+='    <input type="submit" title="'+translate['Remove a suspension for an account nickname']+'" name="submitUnsuspend" value="'+translate['Unsuspend']+'">'
        tlStr+='    <input type="submit" title="'+translate['Block an account on another instance']+'" name="submitBlock" value="'+translate['Block']+'">'
        tlStr+='    <input type="submit" title="'+translate['Unblock an account on another instance']+'" name="submitUnblock" value="'+translate['Unblock']+'">'
        tlStr+='    <input type="submit" title="'+translate['Information about current blocks/suspensions']+'" name="submitInfo" value="'+translate['Info']+'">'
        tlStr+='</div></form>'

    if boxName=='tlshares':
        maxSharesPerAccount=itemsPerPage
        return tlStr+ \
            htmlSharesTimeline(translate,pageNumber,itemsPerPage, \
                               baseDir,actor,nickname,domain,port, \
                               maxSharesPerAccount,httpPrefix) + \
                               htmlFooter()

    # add the javascript for content warnings
    tlStr+='<script>'+contentWarningScript()+'</script>'

    # page up arrow
    if pageNumber>1:
        tlStr+='<center><a href="'+actor+'/'+boxName+'?page='+str(pageNumber-1)+'"><img loading="lazy" class="pageicon" src="/'+iconsDir+'/pageup.png" title="'+translate['Page up']+'" alt="'+translate['Page up']+'"></a></center>'

    # show the posts
    itemCtr=0
    if timelineJson:
        if boxName=='tlmedia':
            if pageNumber>1:
                tlStr+='<br>'
            tlStr+='<div class="galleryContainer">\n'
        for item in timelineJson['orderedItems']:
            if item['type']=='Create' or item['type']=='Announce' or item['type']=='Update':
                # is the actor who sent this post snoozed?
                if isPersonSnoozed(baseDir,nickname,domain,item['actor']):
                    continue

                # is the post in the memory cache of recent ones?
                currTlStr=None
                if boxName!='tlmedia' and recentPostsCache.get('index'):
                    postId=item['id'].replace('/activity','').replace('/','#')
                    if postId in recentPostsCache['index']:
                        if not item.get('muted'):
                            if recentPostsCache['html'].get(postId):                            
                                currTlStr=recentPostsCache['html'][postId]
                                currTlStr= \
                                    preparePostFromHtmlCache(currTlStr,boxName,pageNumber)
                if not currTlStr:
                    # read the post from disk
                    currTlStr= \
                        individualPostAsHtml(recentPostsCache,maxRecentPosts, \
                                             iconsDir,translate,pageNumber, \
                                             baseDir,session,wfRequest,personCache, \
                                             nickname,domain,port,item,None,True, \
                                             allowDeletion, \
                                             httpPrefix,projectVersion,boxName, \
                                             boxName!='dm', \
                                             showIndividualPostIcons, \
                                             manuallyApproveFollowers,False,True)

                if currTlStr:
                    itemCtr+=1
                    tlStr+=currTlStr
        if boxName=='tlmedia':
            tlStr+='</div>\n'

    # page down arrow
    if itemCtr>2:
        tlStr+='<center><a href="'+actor+'/'+boxName+'?page='+str(pageNumber+1)+'"><img loading="lazy" class="pageicon" src="/'+iconsDir+'/pagedown.png" title="'+translate['Page down']+'" alt="'+translate['Page down']+'"></a></center>'
    tlStr+=htmlFooter()
    return tlStr

def htmlShares(defaultTimeline: str, \
               recentPostsCache: {},maxRecentPosts: int, \
               translate: {},pageNumber: int,itemsPerPage: int, \
               session,baseDir: str,wfRequest: {},personCache: {}, \
               nickname: str,domain: str,port: int, \
               allowDeletion: bool, \
               httpPrefix: str,projectVersion: str) -> str:
    """Show the shares timeline as html
    """
    manuallyApproveFollowers= \
        followerApprovalActive(baseDir,nickname,domain)

    return htmlTimeline(defaultTimeline,recentPostsCache,maxRecentPosts, \
                        translate,pageNumber, \
                        itemsPerPage,session,baseDir,wfRequest,personCache, \
                        nickname,domain,port,None,'tlshares',allowDeletion, \
                        httpPrefix,projectVersion,manuallyApproveFollowers)

def htmlInbox(defaultTimeline: str, \
              recentPostsCache: {},maxRecentPosts: int, \
              translate: {},pageNumber: int,itemsPerPage: int, \
              session,baseDir: str,wfRequest: {},personCache: {}, \
              nickname: str,domain: str,port: int,inboxJson: {}, \
              allowDeletion: bool, \
              httpPrefix: str,projectVersion: str) -> str:
    """Show the inbox as html
    """
    manuallyApproveFollowers= \
        followerApprovalActive(baseDir,nickname,domain)

    return htmlTimeline(defaultTimeline,recentPostsCache,maxRecentPosts, \
                        translate,pageNumber, \
                        itemsPerPage,session,baseDir,wfRequest,personCache, \
                        nickname,domain,port,inboxJson,'inbox',allowDeletion, \
                        httpPrefix,projectVersion,manuallyApproveFollowers)

def htmlBookmarks(defaultTimeline: str, \
                  recentPostsCache: {},maxRecentPosts: int, \
                  translate: {},pageNumber: int,itemsPerPage: int, \
                  session,baseDir: str,wfRequest: {},personCache: {}, \
                  nickname: str,domain: str,port: int,bookmarksJson: {}, \
                  allowDeletion: bool, \
                  httpPrefix: str,projectVersion: str) -> str:
    """Show the bookmarks as html
    """
    manuallyApproveFollowers= \
        followerApprovalActive(baseDir,nickname,domain)

    return htmlTimeline(defaultTimeline,recentPostsCache,maxRecentPosts, \
                        translate,pageNumber, \
                        itemsPerPage,session,baseDir,wfRequest,personCache, \
                        nickname,domain,port,bookmarksJson,'tlbookmarks',allowDeletion, \
                        httpPrefix,projectVersion,manuallyApproveFollowers)

def htmlInboxDMs(defaultTimeline: str, \
                 recentPostsCache: {},maxRecentPosts: int, \
                 translate: {},pageNumber: int,itemsPerPage: int, \
                 session,baseDir: str,wfRequest: {},personCache: {}, \
                 nickname: str,domain: str,port: int,inboxJson: {}, \
                 allowDeletion: bool, \
                 httpPrefix: str,projectVersion: str) -> str:
    """Show the DM timeline as html
    """
    return htmlTimeline(defaultTimeline,recentPostsCache,maxRecentPosts, \
                        translate,pageNumber, \
                        itemsPerPage,session,baseDir,wfRequest,personCache, \
                        nickname,domain,port,inboxJson,'dm',allowDeletion, \
                        httpPrefix,projectVersion,False)

def htmlInboxReplies(defaultTimeline: str, \
                     recentPostsCache: {},maxRecentPosts: int, \
                     translate: {},pageNumber: int,itemsPerPage: int, \
                     session,baseDir: str,wfRequest: {},personCache: {}, \
                     nickname: str,domain: str,port: int,inboxJson: {}, \
                     allowDeletion: bool, \
                     httpPrefix: str,projectVersion: str) -> str:
    """Show the replies timeline as html
    """
    return htmlTimeline(defaultTimeline,recentPostsCache,maxRecentPosts, \
                        translate,pageNumber, \
                        itemsPerPage,session,baseDir,wfRequest,personCache, \
                        nickname,domain,port,inboxJson,'tlreplies',allowDeletion, \
                        httpPrefix,projectVersion,False)

def htmlInboxMedia(defaultTimeline: str, \
                   recentPostsCache: {},maxRecentPosts: int, \
                   translate: {},pageNumber: int,itemsPerPage: int, \
                   session,baseDir: str,wfRequest: {},personCache: {}, \
                   nickname: str,domain: str,port: int,inboxJson: {}, \
                   allowDeletion: bool, \
                   httpPrefix: str,projectVersion: str) -> str:
    """Show the media timeline as html
    """
    return htmlTimeline(defaultTimeline,recentPostsCache,maxRecentPosts, \
                        translate,pageNumber, \
                        itemsPerPage,session,baseDir,wfRequest,personCache, \
                        nickname,domain,port,inboxJson,'tlmedia',allowDeletion, \
                        httpPrefix,projectVersion,False)

def htmlModeration(defaultTimeline: str, \
                   recentPostsCache: {},maxRecentPosts: int, \
                   translate: {},pageNumber: int,itemsPerPage: int, \
                   session,baseDir: str,wfRequest: {},personCache: {}, \
                   nickname: str,domain: str,port: int,inboxJson: {}, \
                   allowDeletion: bool, \
                   httpPrefix: str,projectVersion: str) -> str:
    """Show the moderation feed as html
    """
    return htmlTimeline(defaultTimeline,recentPostsCache,maxRecentPosts, \
                        translate,pageNumber, \
                        itemsPerPage,session,baseDir,wfRequest,personCache, \
                        nickname,domain,port,inboxJson,'moderation',allowDeletion, \
                        httpPrefix,projectVersion,True)

def htmlOutbox(defaultTimeline: str, \
               recentPostsCache: {},maxRecentPosts: int, \
               translate: {},pageNumber: int,itemsPerPage: int, \
               session,baseDir: str,wfRequest: {},personCache: {}, \
               nickname: str,domain: str,port: int,outboxJson: {}, \
               allowDeletion: bool,
               httpPrefix: str,projectVersion: str) -> str:
    """Show the Outbox as html
    """
    manuallyApproveFollowers= \
        followerApprovalActive(baseDir,nickname,domain)
    return htmlTimeline(defaultTimeline,recentPostsCache,maxRecentPosts, \
                        translate,pageNumber, \
                        itemsPerPage,session,baseDir,wfRequest,personCache, \
                        nickname,domain,port,outboxJson,'outbox',allowDeletion, \
                        httpPrefix,projectVersion,manuallyApproveFollowers)

def htmlIndividualPost(recentPostsCache: {},maxRecentPosts: int, \
                       translate: {}, \
                       baseDir: str,session,wfRequest: {},personCache: {}, \
                       nickname: str,domain: str,port: int,authorized: bool, \
                       postJsonObject: {},httpPrefix: str,projectVersion: str) -> str:
    """Show an individual post as html
    """
    iconsDir=getIconsDir(baseDir)
    postStr='<script>'+contentWarningScript()+'</script>'    
    postStr+= \
        individualPostAsHtml(recentPostsCache,maxRecentPosts, \
                             iconsDir,translate,None, \
                             baseDir,session,wfRequest,personCache, \
                             nickname,domain,port,postJsonObject,None,True,False, \
                             httpPrefix,projectVersion,'inbox', \
                             False,authorized,False,False,False)
    messageId=postJsonObject['id'].replace('/activity','')

    # show the previous posts
    while postJsonObject['object'].get('inReplyTo'):
        postFilename=locatePost(baseDir,nickname,domain,postJsonObject['object']['inReplyTo'])
        if not postFilename:
            break
        postJsonObject=loadJson(postFilename)
        if postJsonObject:
            postStr= \
                individualPostAsHtml(recentPostsCache,maxRecentPosts, \
                                     iconsDir,translate,None, \
                                     baseDir,session,wfRequest,personCache, \
                                     nickname,domain,port,postJsonObject, \
                                     None,True,False, \
                                     httpPrefix,projectVersion,'inbox', \
                                     False,authorized,False,False,False)+postStr

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
                    individualPostAsHtml(recentPostsCache,maxRecentPosts, \
                                         iconsDir,translate,None, \
                                         baseDir,session,wfRequest,personCache, \
                                         nickname,domain,port,item,None,True,False, \
                                         httpPrefix,projectVersion,'inbox', \
                                         False,authorized,False,False,False)
    cssFilename=baseDir+'/epicyon-profile.css'
    if os.path.isfile(baseDir+'/epicyon.css'):
        cssFilename=baseDir+'/epicyon.css'        
    with open(cssFilename, 'r') as cssFile:
        postsCSS=cssFile.read()
        if httpPrefix!='https':
            postsCSS=postsCSS.replace('https://',httpPrefix+'://')
    return htmlHeader(cssFilename,postsCSS)+postStr+htmlFooter()

def htmlPostReplies(recentPostsCache: {},maxRecentPosts: int, \
                    translate: {},baseDir: str, \
                    session,wfRequest: {},personCache: {}, \
                    nickname: str,domain: str,port: int,repliesJson: {}, \
                    httpPrefix: str,projectVersion: str) -> str:
    """Show the replies to an individual post as html
    """
    iconsDir=getIconsDir(baseDir)
    repliesStr=''
    if repliesJson.get('orderedItems'):
        for item in repliesJson['orderedItems']:
            repliesStr+= \
                individualPostAsHtml(recentPostsCache,maxRecentPosts, \
                                     iconsDir,translate,None, \
                                     baseDir,session,wfRequest,personCache, \
                                     nickname,domain,port,item,None,True,False, \
                                     httpPrefix,projectVersion,'inbox', \
                                     False,False,False,False,False)

    cssFilename=baseDir+'/epicyon-profile.css'
    if os.path.isfile(baseDir+'/epicyon.css'):
        cssFilename=baseDir+'/epicyon.css'        
    with open(cssFilename, 'r') as cssFile:
        postsCSS=cssFile.read()
        if httpPrefix!='https':
            postsCSS=postsCSS.replace('https://',httpPrefix+'://')
    return htmlHeader(cssFilename,postsCSS)+repliesStr+htmlFooter()

def htmlRemoveSharedItem(translate: {},baseDir: str,actor: str,shareName: str) -> str:
    """Shows a screen asking to confirm the removal of a shared item
    """
    itemID=getValidSharedItemID(shareName)
    nickname=getNicknameFromActor(actor)
    domain,port=getDomainFromActor(actor)
    sharesFile=baseDir+'/accounts/'+nickname+'@'+domain+'/shares.json'
    if not os.path.isfile(sharesFile):
        print('ERROR: no shares file '+sharesFile)
        return None
    sharesJson=loadJson(sharesFile)    
    if not sharesJson:
        print('ERROR: unable to load shares.json')
        return None
    if not sharesJson.get(itemID):
        print('ERROR: share named "'+itemID+'" is not in '+sharesFile)
        return None
    sharedItemDisplayName=sharesJson[itemID]['displayName']
    sharedItemImageUrl=None
    if sharesJson[itemID].get('imageUrl'):
        sharedItemImageUrl=sharesJson[itemID]['imageUrl']

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
        sharesStr+='  <img loading="lazy" src="'+sharedItemImageUrl+'"/>'
    sharesStr+='  <p class="followText">'+translate['Remove']+' '+sharedItemDisplayName+' ?</p>'
    sharesStr+='  <form method="POST" action="'+actor+'/rmshare">'
    sharesStr+='    <input type="hidden" name="actor" value="'+actor+'">'
    sharesStr+='    <input type="hidden" name="shareName" value="'+shareName+'">'
    sharesStr+='    <button type="submit" class="button" name="submitYes">'+translate['Yes']+'</button>'
    sharesStr+='    <a href="'+actor+'/inbox'+'"><button class="button">'+translate['No']+'</button></a>'
    sharesStr+='  </form>'
    sharesStr+='  </center>'
    sharesStr+='  </div>'
    sharesStr+='</div>'
    sharesStr+=htmlFooter()
    return sharesStr

def htmlDeletePost(recentPostsCache: {},maxRecentPosts: int, \
                   translate,pageNumber: int, \
                   session,baseDir: str,messageId: str, \
                   httpPrefix: str,projectVersion: str, \
                   wfRequest: {},personCache: {}) -> str:
    """Shows a screen asking to confirm the deletion of a post
    """
    if '/statuses/' not in messageId:
        return None
    iconsDir=getIconsDir(baseDir)
    actor=messageId.split('/statuses/')[0]
    nickname=getNicknameFromActor(actor)
    domain,port=getDomainFromActor(actor)

    postFilename=locatePost(baseDir,nickname,domain,messageId)
    if not postFilename:
        return None

    postJsonObject=loadJson(postFilename)
    if not postJsonObject:
        return None

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
        if httpPrefix!='https':
            profileStyle=profileStyle.replace('https://',httpPrefix+'://')
        deletePostStr=htmlHeader(cssFilename,profileStyle)
        deletePostStr+='<script>'+contentWarningScript()+'</script>'
        deletePostStr+= \
            individualPostAsHtml(recentPostsCache,maxRecentPosts, \
                                 iconsDir,translate,pageNumber, \
                                 baseDir,session,wfRequest,personCache, \
                                 nickname,domain,port,postJsonObject, \
                                 None,True,False, \
                                 httpPrefix,projectVersion,'outbox', \
                                 False,False,False,False,False)
        deletePostStr+='<center>'
        deletePostStr+='  <p class="followText">'+translate['Delete this post?']+'</p>'
        deletePostStr+='  <form method="POST" action="'+actor+'/rmpost">'
        deletePostStr+='    <input type="hidden" name="pageNumber" value="'+str(pageNumber)+'">'
        deletePostStr+='    <input type="hidden" name="messageId" value="'+messageId+'">'
        deletePostStr+='    <button type="submit" class="button" name="submitYes">'+translate['Yes']+'</button>'
        deletePostStr+='    <a href="'+actor+'/inbox'+'"><button class="button">'+translate['No']+'</button></a>'
        deletePostStr+='  </form>'
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
    followStr+='  <img loading="lazy" src="'+followProfileUrl+'"/></a>'
    followStr+='  <p class="followText">'+translate['Follow']+' '+getNicknameFromActor(followActor)+'@'+followDomain+' ?</p>'
    followStr+='  <form method="POST" action="'+originPathStr+'/followconfirm">'
    followStr+='    <input type="hidden" name="actor" value="'+followActor+'">'
    followStr+='    <button type="submit" class="button" name="submitYes">'+translate['Yes']+'</button>'
    followStr+='    <a href="'+originPathStr+'"><button class="button">'+translate['No']+'</button></a>'
    followStr+='  </form>'
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
    followStr+='  <img loading="lazy" src="'+followProfileUrl+'"/></a>'
    followStr+='  <p class="followText">'+translate['Stop following']+' '+getNicknameFromActor(followActor)+'@'+followDomain+' ?</p>'
    followStr+='  <form method="POST" action="'+originPathStr+'/unfollowconfirm">'
    followStr+='    <input type="hidden" name="actor" value="'+followActor+'">'
    followStr+='    <button type="submit" class="button" name="submitYes">'+translate['Yes']+'</button>'
    followStr+='    <a href="'+originPathStr+'"><button class="button">'+translate['No']+'</button></a>'
    followStr+='  </form>'
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
                      pageNumber: int, \
                      donateUrl: str, \
                      xmppAddress: str, \
                      matrixAddress: str, \
                      PGPpubKey: str, \
                      emailAddress) -> str:
    """Show options for a person: view/follow/block/report
    """
    optionsDomain,optionsPort=getDomainFromActor(optionsActor)
    
    if os.path.isfile(baseDir+'/img/options-background.png'):
        if not os.path.isfile(baseDir+'/accounts/options-background.png'):
            copyfile(baseDir+'/img/options-background.png',baseDir+'/accounts/options-background.png')

    followStr='Follow'
    blockStr='Block'
    nickname=None
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

    # To snooze, or not to snooze? That is the question
    snoozeButtonStr='Snooze'
    if nickname:
        if isPersonSnoozed(baseDir,nickname,domain,optionsActor):
            snoozeButtonStr='Unsnooze'

    donateStr=''
    if donateUrl:
        donateStr= \
            '    <a href="'+donateUrl+'"><button class="button" name="submitDonate">'+translate['Donate']+'</button></a>'

    optionsStr=htmlHeader(cssFilename,profileStyle)
    optionsStr+='<div class="options">'
    optionsStr+='  <div class="optionsAvatar">'
    optionsStr+='  <center>'
    optionsStr+='  <a href="'+optionsActor+'">'
    optionsStr+='  <img loading="lazy" src="'+optionsProfileUrl+'"/></a>'
    optionsStr+='  <p class="optionsText">'+translate['Options for']+' @'+getNicknameFromActor(optionsActor)+'@'+optionsDomain+'</p>'
    if emailAddress:
        optionsStr+='<p class="imText">'+translate['Email']+': '+emailAddress+'</p>'
    if xmppAddress:
        optionsStr+='<p class="imText">'+translate['XMPP']+': '+xmppAddress+'</p>'
    if matrixAddress:
        optionsStr+='<p class="imText">'+translate['Matrix']+': '+matrixAddress+'</p>'
    if PGPpubKey:
        optionsStr+='<p class="pgp">'+PGPpubKey.replace('\n','<br>')+'</p>'
    optionsStr+='  <form method="POST" action="'+originPathStr+'/personoptions">'
    optionsStr+='    <input type="hidden" name="pageNumber" value="'+str(pageNumber)+'">'
    optionsStr+='    <input type="hidden" name="actor" value="'+optionsActor+'">'
    optionsStr+='    <input type="hidden" name="avatarUrl" value="'+optionsProfileUrl+'">'
    optionsStr+=optionsLinkStr
    optionsStr+='    <button type="submit" class="button" name="submitView">'+translate['View']+'</button>'
    optionsStr+=donateStr
    optionsStr+='    <button type="submit" class="button" name="submit'+followStr+'">'+translate[followStr]+'</button>'
    optionsStr+='    <button type="submit" class="button" name="submit'+blockStr+'">'+translate[blockStr]+'</button>'
    optionsStr+='    <button type="submit" class="button" name="submitDM">'+translate['DM']+'</button>'
    optionsStr+='    <button type="submit" class="button" name="submit'+snoozeButtonStr+'">'+translate[snoozeButtonStr]+'</button>'
    optionsStr+='    <button type="submit" class="button" name="submitReport">'+translate['Report']+'</button>'
    optionsStr+='  </form>'
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
#    blockStr+='  <img loading="lazy" src="'+blockProfileUrl+'"/></a>'
#    blockStr+='  <p class="blockText">'+translate['Block']+' '+getNicknameFromActor(blockActor)+'@'+blockDomain+' ?</p>'
#    blockStr+='  <form method="POST" action="'+originPathStr+'/blockconfirm">'
#    blockStr+='    <input type="hidden" name="actor" value="'+blockActor+'">'
#    blockStr+='    <button type="submit" class="button" name="submitYes">'+translate['Yes']+'</button>'
#    blockStr+='    <a href="'+originPathStr+'"><button class="button">'+translate['No']+'</button></a>'
#    blockStr+='  </form>'
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
    blockStr+='  <img loading="lazy" src="'+blockProfileUrl+'"/></a>'
    blockStr+='  <p class="blockText">'+translate['Stop blocking']+' '+getNicknameFromActor(blockActor)+'@'+blockDomain+' ?</p>'
    blockStr+='  <form method="POST" action="'+originPathStr+'/unblockconfirm">'
    blockStr+='    <input type="hidden" name="actor" value="'+blockActor+'">'
    blockStr+='    <button type="submit" class="button" name="submitYes">'+translate['Yes']+'</button>'
    blockStr+='    <a href="'+originPathStr+'"><button class="button">'+translate['No']+'</button></a>'
    blockStr+='  </form>'
    blockStr+='</center>'
    blockStr+='</div>'
    blockStr+='</div>'
    blockStr+=htmlFooter()
    return blockStr

def htmlSearchEmojiTextEntry(translate: {}, \
                             baseDir: str,path: str) -> str:
    """Search for an emoji by name
    """
    # emoji.json is generated so that it can be customized and the changes
    # will be retained even if default_emoji.json is subsequently updated                    
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
    emojiStr+='  <form method="POST" action="'+actor+'/searchhandleemoji">'
    emojiStr+='    <input type="hidden" name="actor" value="'+actor+'">'
    emojiStr+='    <input type="text" name="searchtext" autofocus><br>'
    emojiStr+='    <button type="submit" class="button" name="submitSearch">'+translate['Submit']+'</button>'
    emojiStr+='  </form>'
    emojiStr+='  </center>'
    emojiStr+='  </div>'
    emojiStr+='</div>'
    emojiStr+=htmlFooter()
    return emojiStr

def weekDayOfMonthStart(monthNumber: int,year: int) -> int:
    """Gets the day number of the first day of the month
    1=sun, 7=sat
    """
    firstDayOfMonth=datetime(year, monthNumber, 1, 0, 0)
    return int(firstDayOfMonth.strftime("%w"))+1

def getCalendarEvents(baseDir: str,nickname: str,domain: str,year: int,monthNumber: int) -> {}:
    """Retrieves calendar events
    Returns a dictionary indexed by day number of lists containing Event and Place activities
    """
    calendarFilename=baseDir+'/accounts/'+nickname+'@'+domain+'/calendar/'+str(year)+'/'+str(monthNumber)+'.txt'
    events={}
    if not os.path.isfile(calendarFilename):
        return events
    calendarPostIds=[]
    recreateEventsFile=False
    with open(calendarFilename,'r') as eventsFile: 
        for postId in eventsFile:
            postId=postId.replace('\n','')
            postFilename=locatePost(baseDir,nickname,domain,postId)
            if postFilename:
                postJsonObject=loadJson(postFilename)
                if postJsonObject:
                    if postJsonObject.get('object'):
                        if isinstance(postJsonObject['object'], dict):
                            if postJsonObject['object'].get('tag'):
                                postEvent=[]
                                dayOfMonth=None
                                for tag in postJsonObject['object']['tag']:
                                    if not tag.get('type'):
                                        continue
                                    if tag['type']!='Event' and tag['type']!='Place':
                                        continue
                                    if tag['type']=='Event':
                                        # tag is an event
                                        if not tag.get('startTime'):
                                            continue
                                        eventTime= \
                                            datetime.strptime(tag['startTime'], \
                                                              "%Y-%m-%dT%H:%M:%S%z")
                                        if int(eventTime.strftime("%Y"))==year and \
                                           int(eventTime.strftime("%m"))==monthNumber:
                                            dayOfMonth=str(int(eventTime.strftime("%d")))
                                            postEvent.append(tag)
                                    else:
                                        # tag is a place
                                        postEvent.append(tag)
                                if postEvent and dayOfMonth:
                                    calendarPostIds.append(postId)
                                    if not events.get(dayOfMonth):
                                        events[dayOfMonth]=[]
                                    events[dayOfMonth].append(postEvent)
            else:
                recreateEventsFile=True

    # if some posts have been deleted then regenerate the calendar file
    if recreateEventsFile:
        calendarFile=open(calendarFilename, "w")
        for postId in calendarPostIds:
            calendarFile.write(postId+'\n')
        calendarFile.close()
    
    return events

def htmlCalendarDay(translate: {}, \
                    baseDir: str,path: str, \
                    year: int,monthNumber: int,dayNumber: int,
                    nickname: str,domain: str,dayEvents: [], \
                    monthName: str, actor: str) -> str:
    """Show a day within the calendar
    """
    accountDir=baseDir+'/accounts/'+nickname+'@'+domain
    calendarFile=accountDir+'/.newCalendar'
    if os.path.isfile(calendarFile):
        os.remove(calendarFile)
    
    cssFilename=baseDir+'/epicyon-calendar.css'
    if os.path.isfile(baseDir+'/calendar.css'):
        cssFilename=baseDir+'/calendar.css'        
    with open(cssFilename, 'r') as cssFile:
        calendarStyle = cssFile.read()
    
    calendarStr=htmlHeader(cssFilename,calendarStyle)
    calendarStr+='<main><table class="calendar">\n'
    calendarStr+='<caption class="calendar__banner--month">\n'
    calendarStr+='  <a href="'+actor+'/calendar?year='+str(year)+'?month='+str(monthNumber)+'">'
    calendarStr+='  <h1>'+str(dayNumber)+' '+monthName+'</h1></a><br><span class="year">'+str(year)+'</span>\n'
    calendarStr+='</caption>\n'
    calendarStr+='<tbody>\n'

    for eventPost in dayEvents:
        eventTime=None
        eventDescription=None
        eventPlace=None
        for ev in eventPost:
            if ev['type']=='Event':
                if ev.get('startTime'):
                    eventDate=datetime.strptime(ev['startTime'],"%Y-%m-%dT%H:%M:%S%z")            
                    eventTime=eventDate.strftime("%H:%M").strip()
                if ev.get('name'):
                    eventDescription=ev['name'].strip()
            elif ev['type']=='Place':
                if ev.get('name'):
                    eventPlace=ev['name']
        if eventTime and eventDescription and eventPlace:
            calendarStr+='<tr><td class="calendar__day__time"><b>'+eventTime+'</b></td><td class="calendar__day__event"><span class="place">'+eventPlace+'</span><br>'+eventDescription+'</td></tr>\n'
        elif eventTime and eventDescription and not eventPlace:
            calendarStr+='<tr><td class="calendar__day__time"><b>'+eventTime+'</b></td><td class="calendar__day__event">'+eventDescription+'</td></tr>\n'
        elif not eventTime and eventDescription and not eventPlace:
            calendarStr+='<tr><td class="calendar__day__time"></td><td class="calendar__day__event">'+eventDescription+'</td></tr>\n'
        elif not eventTime and eventDescription and eventPlace:
            calendarStr+='<tr><td class="calendar__day__time"></td><td class="calendar__day__event"><span class="place">'+eventPlace+'</span><br>'+eventDescription+'</td></tr>\n'
        elif eventTime and not eventDescription and eventPlace:
            calendarStr+='<tr><td class="calendar__day__time"><b>'+eventTime+'</b></td><td class="calendar__day__event"><span class="place">'+eventPlace+'</span></td></tr>\n'
    
    calendarStr+='</tbody>\n'
    calendarStr+='</table></main>\n'
    calendarStr+=htmlFooter()

    return calendarStr
    
def htmlCalendar(translate: {}, \
                 baseDir: str,path: str, \
                 httpPrefix: str,domainFull: str) -> str:
    """Show the calendar for a person
    """
    iconsDir=getIconsDir(baseDir)
    domain=domainFull
    if ':' in domainFull:
        domain=domainFull.split(':')[0]
        
    monthNumber=0
    dayNumber=None
    year=1970
    actor=httpPrefix+'://'+domainFull+path.replace('/calendar','')
    if '?' in actor:
        first=True
        for p in actor.split('?'):
            if not first:
                if '=' in p:
                    if p.split('=')[0]=='year':
                        numStr=p.split('=')[1]
                        if numStr.isdigit():
                            year=int(numStr)
                    elif p.split('=')[0]=='month':
                        numStr=p.split('=')[1]
                        if numStr.isdigit():
                            monthNumber=int(numStr)
                    elif p.split('=')[0]=='day':
                        numStr=p.split('=')[1]
                        if numStr.isdigit():
                            dayNumber=int(numStr)
            first=False
        actor=actor.split('?')[0]

    currDate=datetime.now()
    if year==1970 and monthNumber==0:
        year=currDate.year
        monthNumber=currDate.month

    nickname=getNicknameFromActor(actor)
    events=getCalendarEvents(baseDir,nickname,domain,year,monthNumber)

    months=('Jaruary','February','March','April','May','June','July','August','September','October','November','December')
    monthName=translate[months[monthNumber-1]]

    if os.path.isfile(baseDir+'/img/calendar-background.png'):
        if not os.path.isfile(baseDir+'/accounts/calendar-background.png'):
            copyfile(baseDir+'/img/calendar-background.png',baseDir+'/accounts/calendar-background.png')

    if dayNumber:
        dayEvents=None
        if events.get(str(dayNumber)):
            dayEvents=events[str(dayNumber)]
        return htmlCalendarDay(translate,baseDir,path, \
                               year,monthNumber,dayNumber, \
                               nickname,domain,dayEvents, \
                               monthName,actor)
    
    prevYear=year
    prevMonthNumber=monthNumber-1
    if prevMonthNumber<1:
        prevMonthNumber=12
        prevYear=year-1

    nextYear=year
    nextMonthNumber=monthNumber+1
    if nextMonthNumber>12:
        nextMonthNumber=1
        nextYear=year+1

    print('Calendar year='+str(year)+' month='+str(monthNumber)+ ' '+str(weekDayOfMonthStart(monthNumber,year)))

    if monthNumber<12:
        daysInMonth=(date(year, monthNumber+1, 1) - date(year, monthNumber, 1)).days
    else:
        daysInMonth=(date(year+1, 1, 1) - date(year, monthNumber, 1)).days

    cssFilename=baseDir+'/epicyon-calendar.css'
    if os.path.isfile(baseDir+'/calendar.css'):
        cssFilename=baseDir+'/calendar.css'        
    with open(cssFilename, 'r') as cssFile:
        calendarStyle = cssFile.read()
    
    calendarStr=htmlHeader(cssFilename,calendarStyle)
    calendarStr+='<main><table class="calendar">\n'
    calendarStr+='<caption class="calendar__banner--month">\n'
    calendarStr+='  <a href="'+actor+'/calendar?year='+str(prevYear)+'?month='+str(prevMonthNumber)+'">'
    calendarStr+='  <img loading="lazy" alt="'+translate['Previous month']+'" title="'+translate['Previous month']+'" src="/'+iconsDir+'/prev.png" class="buttonprev"/></a>\n'
    calendarStr+='  <a href="'+actor+'/inbox">'
    calendarStr+='  <h1>'+monthName+'</h1></a>\n'
    calendarStr+='  <a href="'+actor+'/calendar?year='+str(nextYear)+'?month='+str(nextMonthNumber)+'">'
    calendarStr+='  <img loading="lazy" alt="'+translate['Next month']+'" title="'+translate['Next month']+'" src="/'+iconsDir+'/prev.png" class="buttonnext"/></a>\n'
    calendarStr+='</caption>\n'
    calendarStr+='<thead>\n'
    calendarStr+='<tr>\n'
    calendarStr+='  <th class="calendar__day__header">'+translate['Sun']+'</th>\n'
    calendarStr+='  <th class="calendar__day__header">'+translate['Mon']+'</th>\n'
    calendarStr+='  <th class="calendar__day__header">'+translate['Tue']+'</th>\n'
    calendarStr+='  <th class="calendar__day__header">'+translate['Wed']+'</th>\n'
    calendarStr+='  <th class="calendar__day__header">'+translate['Thu']+'</th>\n'
    calendarStr+='  <th class="calendar__day__header">'+translate['Fri']+'</th>\n'
    calendarStr+='  <th class="calendar__day__header">'+translate['Sat']+'</th>\n'
    calendarStr+='</tr>\n'
    calendarStr+='</thead>\n'
    calendarStr+='<tbody>\n'

    dayOfMonth=0
    dow=weekDayOfMonthStart(monthNumber,year)
    for weekOfMonth in range(1,6):
        calendarStr+='  <tr>\n'
        for dayNumber in range(1,8):
            if (weekOfMonth>1 and dayOfMonth<daysInMonth) or \
               (weekOfMonth==1 and dayNumber>=dow):
                dayOfMonth+=1

                isToday=False
                if year==currDate.year:
                    if currDate.month==monthNumber:
                        if dayOfMonth==currDate.day:
                            isToday=True
                if events.get(str(dayOfMonth)):
                    url=actor+'/calendar?year='+str(year)+'?month='+str(monthNumber)+'?day='+str(dayOfMonth)
                    dayLink='<a href="'+url+'">'+str(dayOfMonth)+'</a>'
                    # there are events for this day
                    if not isToday:
                        calendarStr+='    <td class="calendar__day__cell" data-event="">'+dayLink+'</td>\n'
                    else:
                        calendarStr+='    <td class="calendar__day__cell" data-today-event="">'+dayLink+'</td>\n'
                else:
                    # No events today
                    if not isToday:
                        calendarStr+='    <td class="calendar__day__cell">'+str(dayOfMonth)+'</td>\n'
                    else:
                        calendarStr+='    <td class="calendar__day__cell" data-today="">'+str(dayOfMonth)+'</td>\n'
            else:
                calendarStr+='    <td class="calendar__day__cell"></td>\n'
        calendarStr+='  </tr>\n'
        
    calendarStr+='</tbody>\n'
    calendarStr+='</table></main>\n'
    calendarStr+=htmlFooter()
    return calendarStr

def htmlHashTagSwarm(baseDir: str,actor: str) -> str:
    """Returns a tag swarm of today's hashtags
    """
    daysSinceEpoch=(datetime.utcnow() - datetime(1970,1,1)).days
    daysSinceEpochStr=str(daysSinceEpoch)+' '
    nickname=getNicknameFromActor(actor)
    tagSwarm=[]
    for subdir, dirs, files in os.walk(baseDir+'/tags'):
        for f in files:
            tagsFilename=os.path.join(baseDir+'/tags',f)
            if not os.path.isfile(tagsFilename):
                continue
            hashTagName=f.split('.')[0]
            if isBlockedHashtag(baseDir,hashTagName):
                continue
            if daysSinceEpochStr not in open(tagsFilename).read():
                continue
            with open(tagsFilename, 'r') as tagsFile:
                lines=tagsFile.readlines()
                for l in lines:
                    if '  ' not in l:
                        continue
                    postDaysSinceEpochStr=l.split('  ')[0]
                    if not postDaysSinceEpochStr.isdigit():
                        continue
                    postDaysSinceEpoch=int(postDaysSinceEpochStr)
                    if postDaysSinceEpoch<daysSinceEpoch:
                        break
                    if postDaysSinceEpoch==daysSinceEpoch:
                        tagSwarm.append(hashTagName)
                        break
    if not tagSwarm:
        return ''
    tagSwarm.sort()
    tagSwarmStr=''
    for tagName in tagSwarm:
        tagSwarmStr+='<a href="'+actor+'/tags/'+tagName+'" class="hashtagswarm">'+tagName+'</a> '
    tagSwarmHtml=tagSwarmStr.strip()+'\n'
    return tagSwarmHtml

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
    followStr+='  <form method="POST" accept-charset="UTF-8" action="'+actor+'/searchhandle">'
    followStr+='    <input type="hidden" name="actor" value="'+actor+'">'
    followStr+='    <input type="text" name="searchtext" autofocus><br>'
    followStr+='    <button type="submit" class="button" name="submitSearch">'+translate['Submit']+'</button>'
    followStr+='    <button type="submit" class="button" name="submitBack">'+translate['Go Back']+'</button>'
    followStr+='  </form>'
    followStr+='  <p class="hashtagswarm">'+htmlHashTagSwarm(baseDir,actor)+'</p>'
    followStr+='  </center>'
    followStr+='  </div>'
    followStr+='</div>'
    followStr+=htmlFooter()
    return followStr

def htmlProfileAfterSearch(recentPostsCache: {},maxRecentPosts: int, \
                           translate: {}, \
                           baseDir: str,path: str,httpPrefix: str, \
                           nickname: str,domain: str,port: int, \
                           profileHandle: str, \
                           session,wfRequest: {},personCache: {},
                           debug: bool,projectVersion: str) -> str:
    """Show a profile page after a search for a fediverse address
    """
    if '/users/' in profileHandle or \
       '/channel/' in profileHandle or \
       '/profile/' in profileHandle or \
       '/@' in profileHandle:
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
        personUrl=None
        if wf.get('errors'):
            personUrl=httpPrefix+'://'+searchDomainFull+'/users/'+searchNickname
            
        asHeader = {'Accept': 'application/activity+json; profile="https://www.w3.org/ns/activitystreams"'}
        if not personUrl:
            personUrl = getUserUrl(wf)
        if not personUrl:
            # try single user instance
            asHeader = {'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"'}
            personUrl=httpPrefix+'://'+searchDomainFull
        profileJson = getJson(session,personUrl,asHeader,None,projectVersion,httpPrefix,domain)
        if not profileJson:
            asHeader = {'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"'}
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
        if httpPrefix!='https':
            profileStyle=profileStyle.replace('https://',httpPrefix+'://')
        # url to return to
        backUrl=path
        if not backUrl.endswith('/inbox'):
            backUrl+='/inbox'

        profileDescriptionShort=profileDescription
        if '\n' in profileDescription:
            if len(profileDescription.split('\n'))>2:
                profileDescriptionShort=''
        else:
            if '<br>' in profileDescription:
                if len(profileDescription.split('<br>'))>2:
                    profileDescriptionShort=''
        # keep the profile description short
        if len(profileDescriptionShort)>256:
            profileDescriptionShort=''
        # remove formatting from profile description used on title
        avatarDescription=''
        if profileJson.get('summary'):
            avatarDescription=profileJson['summary'].replace('<br>','\n').replace('<p>','').replace('</p>','')
        profileStr=' <div class="hero-image">'
        profileStr+='  <div class="hero-text">'
        profileStr+='    <img loading="lazy" src="'+avatarUrl+'" alt="'+avatarDescription+'" title="'+avatarDescription+'">'
        profileStr+='    <h1>'+displayName+'</h1>'
        profileStr+='    <p><b>@'+searchNickname+'@'+searchDomainFull+'</b></p>'
        profileStr+='    <p>'+profileDescriptionShort+'</p>'
        profileStr+='  </div>'
        profileStr+='</div>'
        profileStr+='<div class="container">\n'
        profileStr+='  <form method="POST" action="'+backUrl+'/followconfirm">'
        profileStr+='    <center>'
        profileStr+='      <input type="hidden" name="actor" value="'+personUrl+'">'
        profileStr+='      <button type="submit" class="button" name="submitYes">'+translate['Follow']+'</button>'
        profileStr+='      <button type="submit" class="button" name="submitView">'+translate['View']+'</button>'
        profileStr+='      <a href="'+backUrl+'"><button class="button">'+translate['Go Back']+'</button></a>'
        profileStr+='    </center>'
        profileStr+='  </form>'
        profileStr+='</div>'

        profileStr+='<script>'+contentWarningScript()+'</script>'

        iconsDir=getIconsDir(baseDir)
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
                individualPostAsHtml(recentPostsCache,maxRecentPosts, \
                                     iconsDir,translate,None,baseDir, \
                                     session,wfRequest,personCache, \
                                     nickname,domain,port, \
                                     item,avatarUrl,False,False, \
                                     httpPrefix,projectVersion,'inbox', \
                                     False,False,False,False,False)
            i+=1
            if i>=20:
                break

    return htmlHeader(cssFilename,profileStyle)+profileStr+htmlFooter()
