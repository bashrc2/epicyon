__filename__ = "content.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
import commentjson
from shutil import copyfile

def validHashTag(hashtag: str) -> bool:
    """Returns true if the give hashtag contains valid characters
    """
    validChars = set('0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')
    if set(hashtag).issubset(validChars):
        return True
    return False

def addHashTags(wordStr: str,httpPrefix: str,domain: str,replaceHashTags: {},postHashtags: {}) -> bool:
    """Detects hashtags and adds them to the replacements dict
    Also updates the hashtags list to be added to the post
    """
    if not wordStr.startswith('#'):
        return False
    if len(wordStr)<2:
        return False
    if replaceHashTags.get(wordStr):
       return True
    hashtag=wordStr[1:]
    if not validHashTag(hashtag):
        return False
    hashtagUrl=httpPrefix+"://"+domain+"/tags/"+hashtag
    postHashtags[hashtag]= {
        'href': hashtagUrl,
        'name': '#'+hashtag,
        'type': 'Hashtag'
    }
    replaceHashTags[wordStr]= \
        "<a href=\""+hashtagUrl+"\" class=\"mention hashtag\" rel=\"tag\">#<span>"+hashtag+"</span></a>"
    return True

def loadEmojiDict(emojiDataFilename: str,emojiDict: {}) -> None:
    """Creates an emoji dictionary based on emoji/emoji-data.txt
    """
    if not os.path.isfile(emojiDataFilename):
        return
    with open (emojiDataFilename, "r") as fileHandler:
        for line in fileHandler:
            if len(line)<5:
                continue
            if line.startswith('#'):
                continue
            if '; Emoji' not in line:
                continue
            if ')' not in line:
                continue
            emojiUnicode=line.split(' ')[0]
            if len(emojiUnicode)<4:
                continue
            if '..' in emojiUnicode:
                emojiUnicode=emojiUnicode.split('..')[0]
            emojiName=line.split(')',1)[1].strip().replace('\n','').replace(' ','').replace('-','')
            if '..' in emojiName:
                emojiName=emojiName.split('..')[0]
            emojiDict[emojiName.lower()]=emojiUnicode

def addEmoji(baseDir: str,wordStr: str,httpPrefix: str,domain: str,replaceEmoji: {},postTags: {},emojiDict: {}) -> bool:
    """Detects Emoji and adds them to the replacements dict
    Also updates the tags list to be added to the post
    """
    if not wordStr.startswith(':'):
        return False
    if not wordStr.endswith(':'):
        return False
    if len(wordStr)<3:
        return False
    if replaceEmoji.get(wordStr):
       return True
    emoji=wordStr[1:]
    emoji=emoji[:-1]
    if not validHashTag(emoji):
        return False
    if not emojiDict.get(emoji):
        return False
    emojiFilename=baseDir+'/emoji/'+emojiDict[emoji]+'.png'
    if not os.path.isfile(emojiFilename):
        return False
    emojiUrl=httpPrefix+"://"+domain+"/emoji/"+emojiDict[emoji]+'.png'
    postTags[emoji]= {
        'href': emojiUrl,
        'name': ':'+emoji+':',
        'type': 'Emoji'
    }
    replaceEmoji[wordStr]= \
        "<img src=\""+emojiUrl+"\" alt=\""+emoji+"\" align=\"middle\" class=\"emoji\"/>"
    return True

def addMention(wordStr: str,httpPrefix: str,following: str,replaceMentions: {},recipients: []) -> bool:
    """Detects mentions and adds them to the replacements dict and recipients list
    """
    if not wordStr.startswith('@'):
        return False
    if len(wordStr)<2:
        return False
    possibleHandle=wordStr[1:]
    print('Possible mention: '+possibleHandle)
    # @nick
    if '@' not in possibleHandle:
        # fall back to a best effort match against the following list
        # if no domain was specified. eg. @nick
        possibleNickname=possibleHandle
        for follow in following:
            if follow.startswith(possibleNickname+'@'):
                replaceDomain=follow.replace('\n','').split('@')[1]
                recipientActor=httpPrefix+"://"+replaceDomain+"/users/"+possibleNickname
                if recipientActor not in recipients:
                    recipients.append(recipientActor)
                replaceMentions[wordStr]="<span class=\"h-card\"><a href=\""+httpPrefix+"://"+replaceDomain+"/@"+possibleNickname+"\" class=\"u-url mention\">@<span>"+possibleNickname+"</span></a></span>"
                return True
        return False
    possibleNickname=possibleHandle.split('@')[0]
    possibleDomain=possibleHandle.split('@')[1].strip('\n')
    for follow in following:
        if follow.replace('\n','')!=possibleHandle:
            continue
        recipientActor=httpPrefix+"://"+possibleDomain+"/users/"+possibleNickname
        if recipientActor not in recipients:
            recipients.append(recipientActor)
        replaceMentions[wordStr]="<span class=\"h-card\"><a href=\""+httpPrefix+"://"+possibleDomain+"/@"+possibleNickname+"\" class=\"u-url mention\">@<span>"+possibleNickname+"</span></a></span>"
        return True
    # @nick@domain
    if '@' in possibleHandle:
        if not (possibleDomain=='localhost' or '.' in possibleDomain):
            return False        
        recipientActor=httpPrefix+"://"+possibleDomain+"/users/"+possibleNickname
        if recipientActor not in recipients:
            recipients.append(recipientActor)
        replaceMentions[wordStr]="<span class=\"h-card\"><a href=\""+httpPrefix+"://"+possibleDomain+"/@"+possibleNickname+"\" class=\"u-url mention\">@<span>"+possibleNickname+"</span></a></span>"
        return True
    return False

def addHtmlTags(baseDir: str,httpPrefix: str, \
                nickname: str,domain: str,content: str, \
                recipients: [],hashtags: {}) -> str:
    """ Replaces plaintext mentions such as @nick@domain into html
    by matching against known following accounts
    """
    if content.startswith('<p>'):
        return content
    words=content.replace(',',' ').replace(';',' ').split(' ')

    # remove . for words which are not mentions
    wordCtr=0
    newWords=[]
    for wordIndex in range(0,len(words)):
        wordStr=words[wordIndex]
        if wordStr.endswith('.'):
            if not wordStr.startswith('@'):
                wordStr=wordStr[:-1]
        if wordStr.startswith('.'):
            wordStr=wordStr[1:]
        newWords.append(wordStr)
    words=newWords
    print(str(words))

    replaceMentions={}
    replaceHashTags={}
    replaceEmoji={}
    emojiDict={}
    originalDomain=domain
    if ':' in domain:
        domain=domain.split(':')[0]
    followingFilename=baseDir+'/accounts/'+nickname+'@'+domain+'/following.txt'

    # read the following list so that we can detect just @nick
    # in addition to @nick@domain
    following=None
    if os.path.isfile(followingFilename):
        with open(followingFilename, "r") as f:
            following = f.readlines()

    # extract mentions and tags from words
    for wordStr in words:
        if following:
            if addMention(wordStr,httpPrefix,following,replaceMentions,recipients):
                continue
        if addHashTags(wordStr,httpPrefix,originalDomain,replaceHashTags,hashtags):
            continue
        if len(wordStr)>2 and wordStr.startswith(':') and wordStr.endswith(':') and not emojiDict:
            print('Loading emoji lookup')
            if not os.path.isfile(baseDir+'/emoji/emoji.json'):
                copyfile(baseDir+'/emoji/default_emoji.json',baseDir+'/emoji/emoji.json')
            with open(baseDir+'/emoji/emoji.json', 'r') as fp:
                emojiDict=commentjson.load(fp)

        addEmoji(baseDir,wordStr,httpPrefix,originalDomain,replaceEmoji,hashtags,emojiDict)

    # replace words with their html versions
    for wordStr,replaceStr in replaceMentions.items():
        content=content.replace(wordStr,replaceStr)
    for wordStr,replaceStr in replaceHashTags.items():
        content=content.replace(wordStr,replaceStr)
    for wordStr,replaceStr in replaceEmoji.items():
        content=content.replace(wordStr,replaceStr)
        
    content=content.replace('\n','</p><p>')
    print('Tags extracted from post: '+str(hashtags))
    return '<p>'+content+'</p>'
                
def getMentionsFromHtml(htmlText: str,matchStr="<span class=\"h-card\"><a href=\"") -> []:
    """Extracts mentioned actors from the given html content string
    """
    mentions=[]
    if matchStr not in htmlText:
        return mentions
    mentionsList=htmlText.split(matchStr)
    for mentionStr in mentionsList:
        if '"' not in mentionStr:
            continue
        actorStr=mentionStr.split('"')[0]
        if actorStr.startswith('http') or \
           actorStr.startswith('dat:'):
            mentions.append(actorStr)
    return mentions
