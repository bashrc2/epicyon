__filename__ = "content.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
import commentjson

def addMentions(baseDir: str,httpPrefix: str, \
                nickname: str,domain: str,content: str) -> str:
    """ Replaces plaintext mentions such as @nick@domain into html
    by matching against known following accounts
    """
    if content.startswith('<p>'):
        return content
    wordsOnly=content.replace(',',' ').replace(';',' ').replace('.',' ').replace(':',' ')
    words=wordsOnly.split(' ')
    replaceMentions={}
    followingFilename=baseDir+'/accounts/'+nickname+'@'+domain+'/following.txt'
    if not os.path.isfile(followingFilename):
        return content
    with open(followingFilename, "r") as f:
        following = f.readlines()
    for wordStr in words:
        if wordStr.startswith('@'):
            if len(wordStr)>1:
                possibleHandle=wordStr[1:]
                if '@' in possibleHandle:
                    possibleNickname=possibleHandle.split('@')[0]
                    possibleDomain=possibleHandle.split('@')[1]
                    replaceFound=False
                    for follow in following:
                        if follow.replace('\n','')==possibleHandle:
                            replaceMentions[wordStr]="<span class=\"h-card\"><a href=\""+httpPrefix+"://"+possibleDomain+"/@"+possibleNickname+"\" class=\"u-url mention\">@<span>"+possibleNickname+"</span></a></span>"
                            replaceFound=True
                            break
                    if not replaceFound:
                        # fall back to a best effort match if an exact one is not found
                        for follow in following:
                            if follow.startsWith(possibleNickname+'@'):
                                replaceDomain=follow.replace('\n','').split('@')[1]
                                replaceMentions[wordStr]="<span class=\"h-card\"><a href=\""+httpPrefix+"://"+replaceDomain+"/@"+possibleNickname+"\" class=\"u-url mention\">@<span>"+possibleNickname+"</span></a></span>"
                                replaceFound=True
                                break
    # do the mention replacements
    for wordStr,replaceStr in replaceMentions.items():
        content=content.replace(wordStr,replaceStr)
    content=content.replace('\n','</p><p>')
    return '<p>'+content+'</p>'
                
