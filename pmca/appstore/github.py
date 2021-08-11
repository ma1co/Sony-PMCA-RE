import json
from ..util import http

class GithubApi(object):
 def __init__(self, user, repo):
  self.apiBase = 'https://api.github.com'
  self.rawBase = 'https://raw.githubusercontent.com'
  self.user = user
  self.repo = repo

 def request(self, endpoint):
  url = '/repos/%s/%s' % (self.user, self.repo) + endpoint
  return json.loads(http.get(self.apiBase + url).data)

 def getFile(self, branch, path):
  return http.get(self.rawBase + '/%s/%s/%s/%s' % (self.user, self.repo, branch, path)).data

 def getReleases(self):
  return self.request('/releases')
