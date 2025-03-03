import os
import requests
import simplejson
import pickle
import urlparse
from urllib import urlencode
import oauth2 as oauth

REQUEST_TOKEN_URL = 'http://vimeo.com/oauth/request_token'
ACCESS_TOKEN_URL = 'http://vimeo.com/oauth/access_token'
AUTHORIZATION_URL = 'http://vimeo.com/oauth/authorize'


class Client(object):
    """A client for interacting with Vimeo resources."""

    def __init__(self, **kwargs):
        """Create a client instance with the provided options. Options should be passed in as kwargs."""

        self.options = kwargs
        self.key = kwargs.get('key')
        self.secret = kwargs.get('secret')
        self.callback = kwargs.get('callback')
        self.username = kwargs.get('username')
        self.token_check = kwargs.get('token')
        self.access_token = None
        self.access_token_secret = None
        self._authorize_url = None
        self.consumer = None
        self.token = None
        self.client = None

        if 'key' and 'secret' in kwargs:
            self.consumer = oauth.Consumer(key=self.key, secret=self.secret)

        self.path = os.path.join("~", ".vimeo")

        # decide which protocol flow to follow based on the token value
        # provided by the caller.
        if self._options_for_authorization_flow_present():
            if self.token_check == True:
                self._access_token_flow()
            elif self.token_check == False:
                pass
            else:
                self._authorization_flow()

    def _authorization_flow(self):
        """Given the values, get the request token."""

        self.client = oauth.Client(self.consumer)
        self._get_new_token(REQUEST_TOKEN_URL)

        # Store self.token in cache.
        path = self._get_cache_token_path()
        if not os.path.exists(path):
            os.makedirs(path)
        f = open(self._get_cache_token_filename(), "w")
        pickle.dump(self.token, f, pickle.HIGHEST_PROTOCOL)
        f.close()

    def authorize_url(self, permission="read"):
        """Build the authorization URL and return for OAuth2 authorization code flow."""

        if not self.token:
            self._authorization_flow()
        return "{0}?oauth_token={1}&permission={2}". format(AUTHORIZATION_URL, self.token.key, permission)

    def _access_token_flow(self):
        """Fetch the auth informations from the cache and store the values."""

        f = open(self._get_cache_token_filename(), "r")
        file_content = f.read()
        f.close()
        file_content_parsed = file_content.split('!***!')
        self.key = file_content_parsed[0]
        self.secret = file_content_parsed[1]
        self.access_token = file_content_parsed[2]
        self.access_token_secret = file_content_parsed[3]
        self.callback = file_content_parsed[4]
        self.consumer = oauth.Consumer(key=self.key, secret=self.secret)
        self.token = oauth.Token(key=self.access_token, secret=self.access_token_secret)
        self.client = oauth.Client(self.consumer, self.token)

    def exchange_token(self, verifier):
        """Given the value of the verifier and request token info, request an access token."""

        f = open(self._get_cache_token_filename(), "r")
        self.token = pickle.load(f)
        f.close()
        self.token.set_verifier(verifier)
        self.client = oauth.Client(self.consumer, self.token)
        self._get_new_token(ACCESS_TOKEN_URL)
        file_content = self.key + "!***!" + self.secret + "!***!" + self.token.key + "!***!" + self.token.secret + "!***!" + self.callback
        f = open(self._get_cache_token_filename(), "w")
        f.write(file_content)
        f.close()
        return self.token

    def _is_success(self, headers):
        """Check if the response status is success, if not then raise the VimeoError"""
        try:
            status = headers["status"]
        except KeyError:
            status = headers["stat"]
            if status == "fail":
                raise VimeoError(headers["err"]["msg"])
        else:
            if status != "200":
                raise VimeoError("Invalid response {0}".format(headers["status"]))
        return True

    def _get_new_token(self, request_url):

        resp, content = self.client.request(request_url, "POST", body=urlencode({'oauth_callback': self.callback}))

        if self._is_success(resp):
            new_token = dict(urlparse.parse_qsl(content))
            self.token = oauth.Token(new_token["oauth_token"], new_token["oauth_token_secret"])
            self.client = oauth.Client(self.consumer, self.token)

    def get(self, method, **kwargs):
        """Request the URL with the given method for fetching the contents from Vimeo"""

        url = 'http://vimeo.com/api/rest/v2?format=json&method=' + method + '&full_response=1'
        for k in kwargs:
            url = url + '&' + k + '=' + str(kwargs.get(k))
        request = oauth.Request.from_consumer_and_token(consumer=self.consumer, token=self.token, http_method="POST", http_url=url)
        request.update({'oauth_callback': self.callback})
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        request.sign_request(signature_method, self.consumer, self.token)
        headers = request.to_header()
        r = requests.post(url, headers=headers)
        if self._is_success(simplejson.loads(r.text)):
            return r.text

    def _get_cache_token_path(self):
        """Return the directory holding the app data."""
        return os.path.expanduser(os.path.join(self.path, self.key))

    def _get_cache_token_filename(self):
        """Return the full pathname of the cache token file."""
        filename = 'auth-%s.info' % self.username
        return os.path.join(self._get_cache_token_path(), filename)

    # Helper functions for testing arguments provided to the constructor.
    def _options_present(self, options, kwargs):
        return all(map(lambda k: k in kwargs, options))

    def _options_for_authorization_flow_present(self):
        required = ('key', 'secret', 'callback', 'username')
        return self._options_present(required, self.options)


class VimeoError(Exception):
    """
    Exception raised by non-API call errors.
    """
    pass
