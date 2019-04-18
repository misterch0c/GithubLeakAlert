from github3 import GitHub
import requests
import json
import base64
import re
import subprocess
import pymongo
import datetime
from pymongo import MongoClient

client = MongoClient()
client = MongoClient('localhost', 27017)
db = client.githubdorker
leaks=db.leaks
tok="63f64803725a0dbaa4f6e5acae5b7fa8a67b6fb7"

def isAlive(sHost):
    try:
        output = subprocess.check_output("ping -c 1 "+sHost, shell=True)
    except Exception:
        return False

    return True

def pp_json(json_thing, sort=True, indents=4):
    if type(json_thing) is str:
        print(json.dumps(json.loads(json_thing), sort_keys=sort, indent=indents))
    else:
        print(json.dumps(json_thing, sort_keys=sort, indent=indents))
    return None

def parse_line(l):	
    ls=l.split(':')
    if len(ls)>2 or len(ls)==1:
        return l
    else:
        print(ls)
        rz=re.findall(r'"([^"]*)"', ls[1])
        return ','.join(rz)

def getsftp(r,g):

    usersl=[]
    pwdsl=[]
    rez=[]
    hosts=[]
    rezz={}
	
    for repo in r:
        rowner=str(repo.repository).split('/')[0]
        rrepo=str(repo.repository).split('/')[1]
        print("+++++++++++++++")
        repobj=g.repository(rowner,rrepo)
        com=repobj.iter_commits(None,repo.path)
        for ev in com:
            comitdate=ev.commit.author['date']
            htmlink = ev.commit.html_url

            head = {'Authorization': 'token %s' % tok}
            res = requests.get(repo.git_url, headers=head)
            cont=base64.b64decode(res.json()['content']).decode('utf-8')

            for l in cont.splitlines():
                if '\"user\"' in l or '\"username\"' in l:
                    if '//' not in l:
                        usersl.append(parse_line(l))
                        if '\"password\"' in l:
                            if '//' not in l:
                                pwdsl.append(parse_line(l))
                                if '\"host\"' in l:
                                    l = l.replace("http://","").replace("https://","").replace("www.", "")
                                    if not any(x in l for x in ['//','192.168','localhost','127.0.0.1','172.16','10.0']):
                                        hosts.append(parse_line(l))

                    if usersl and pwdsl and hosts and isAlive(hosts[0]):
                        print(repo.git_url)
                        ins=leaks.update_one({"url":repo.git_url},{
			"$setOnInsert":{    
       			    "url":repo.git_url,
			    "password" : pwdsl,
			    "username" : usersl,
			    "host" : hosts,
			    "repository" : rrepo,
			    "owner" : rowner,
			    "date" : comitdate,
			    "online" : isAlive(hosts[0]),
			    "html_link" : htmlink,
			    "created_issue" : False,
			}
		    },upsert = True)
                        print("Added in database " + str(ins.upserted_id))

                usersl=[]
                pwdsl=[]
                hosts=[]

def create_issues(g):
    lleaks=leaks.find({'date': {'$gt': datetime.datetime(2017, 2, 1, 0, 0, 1).isoformat()}})
	
    for idx,leak in enumerate(lleaks):
        print(leak)
        post = """
A set of credentials associated to an online host has been found inside this respository.
```
File: sftp-config.json
sha1: {0}
date: {1}
```
Consider changing your password or [not using passwords at all](https://www.digitalocean.com/community/tutorials/how-to-set-up-ssh-keys--2) and [including sensitive files in your .gitignore](https://git-scm.com/docs/gitignore)
This issue was created automatically by [GithubLeakAlert](https://github.com/misterch0c/GithubLeakAlert), excuse any false positive.<br>

Better prevent than cure (;
<p align="center">
  <img src="http://i.imgur.com/p89jk7r.png" alt="white hat pepe"/>
</p>
        """.format(leak['html_link'].split('/').pop(),leak['date'])

        if not leak['created_issue']:
            print(lleaks)
	    #issue = g.create_issue(leak['owner'],leak['repository'],"Credentials found in this repository",body=post)
            leaks.update_one({'_id':leak['_id']},{'$set':{'created_issue': True}})
	    #ci = g.create_issue("d0rker","test","tesddtt",body=post)



def main():
    g = GitHub(token=tok)
    r = g.search_code("filename:sftp-config password", "indexed","desc")
    getsftp(r, g)
    #create_issues(g)
if __name__ == "__main__":
    main()
