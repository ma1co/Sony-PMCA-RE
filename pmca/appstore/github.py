import json
from ..util import http

class GithubApi(object):
 def __init__(self, user, repo, client=None):
  self.apiBase = 'https://api.github.com'
  self.rawBase = 'https://raw.githubusercontent.com'
  self.user = user
  self.repo = repo
  self.client = client

 def request(self, endpoint):
  url = '/repos/%s/%s' % (self.user, self.repo) + endpoint
  if self.client:
   url += '?client_id=%s&client_secret=%s' % self.client
  return json.loads(http.get(self.apiBase + url).data)

 def getFile(self, branch, path):
  return http.get(self.rawBase + '/%s/%s/%s/%s' % (self.user, self.repo, branch, path)).data

 def getReleases(self):
  return self.request('/releases')
