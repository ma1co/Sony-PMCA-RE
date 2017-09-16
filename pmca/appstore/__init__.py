from collections import OrderedDict
from datetime import datetime
import yaml

from .github import GithubApi
from ..util import http

class AppStore(object):
 def __init__(self, repo, branch='master', filename='apps.yaml'):
  self.repo = repo
  self.branch = branch
  self.filename = filename

 @property
 def apps(self):
  if not hasattr(self, '_apps'):
   apps = (self._createAppInstance(dict) for dict in self._loadApps())
   self._apps = OrderedDict((app.package, app) for app in apps)
  return self._apps

 def _loadApps(self):
  for doc in yaml.safe_load_all(self.repo.getFile(self.branch, self.filename)):
   if 'package' in doc and 'name' in doc:
    yield doc

 def _createAppInstance(self, dict):
  return App(self.repo, dict)


class App(object):
 def __init__(self, repo, dict):
  self.repo = repo
  self.dict = dict

 def __getattr__(self, name):
  if name in ['package', 'author', 'name', 'desc', 'homepage']:
   return self.dict.get(name)
  raise AttributeError(name)

 @property
 def release(self):
  if not hasattr(self, '_release'):
   dict = self._loadRelease()
   self._release = self._createReleaseInstance(dict) if dict else None
  return self._release

 def _loadRelease(self):
  release = self.dict.get('release', {})
  if release.get('type') == 'github' and 'user' in release and 'repo' in release:
   for dict in GithubApi(release['user'], release['repo'], self.repo.client).getReleases():
    asset = self._findGithubAsset(dict.get('assets', []))
    if asset:
     return {
      'version': dict.get('name') or dict.get('tag_name'),
      'date': datetime.strptime(dict.get('created_at'), '%Y-%m-%dT%H:%M:%SZ'),
      'desc': dict.get('body'),
      'url': asset,
     }
  elif release.get('type') == 'yaml' and 'url' in release:
   for dict in yaml.safe_load_all(http.get(release['url']).data):
    if 'version' in dict and 'url' in dict:
     return dict
  elif 'version' in release and 'url' in release:
   return release

 def _findGithubAsset(self, assets, contentType='application/vnd.android.package-archive'):
  for asset in assets:
   if asset.get('content_type') == contentType:
    return asset.get('browser_download_url')

 def _createReleaseInstance(self, dict):
  return Release(self.package, dict)


class Release(object):
 def __init__(self, package, dict):
  self.package = package
  self.dict = dict

 def __getattr__(self, name):
  if name in ['version', 'date', 'desc', 'url']:
   return self.dict.get(name)
  raise AttributeError(name)

 @property
 def asset(self):
  return self._loadAsset()

 def _loadAsset(self):
  return http.get(self.url).raw_data
