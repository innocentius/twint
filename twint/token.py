import re
import time
import random
import aiohttp
import asyncio
from async_timeout import timeout
import requests
import logging as logme

user_agent_list = [
    # 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
    # ' Chrome/60.0.3112.113 Safari/537.36',
    # 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
    # ' Chrome/60.0.3112.90 Safari/537.36',
    # 'Mozilla/5.0 (Windows NT 5.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
    # ' Chrome/60.0.3112.90 Safari/537.36',
    # 'Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
    # ' Chrome/60.0.3112.90 Safari/537.36',
    # 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko)'
    # ' Chrome/44.0.2403.157 Safari/537.36',
    # 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
    # ' Chrome/60.0.3112.113 Safari/537.36',
    # 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
    # ' Chrome/57.0.2987.133 Safari/537.36',
    # 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
    # ' Chrome/57.0.2987.133 Safari/537.36',
    # 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
    # ' Chrome/55.0.2883.87 Safari/537.36',
    # 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
    # ' Chrome/55.0.2883.87 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:78.0) Gecko/20100101 Firefox/78.0'
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.135 Safari/537.36'
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36'
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.83 Safari/537.36'
]

class TokenExpiryException(Exception):
    def __init__(self, msg):
        super().__init__(msg)

        
class RefreshTokenException(Exception):
    def __init__(self, msg):
        super().__init__(msg)
        
async def Request(_url, connector=None, params=None, headers=None):
    logme.debug(__name__ + ':Request:Connector')
    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        return await Response(session, _url, params)


async def Response(session, _url, params=None):
    logme.debug(__name__ + ':Response')
    httpproxy = "http://127.0.0.1:24000"
    with timeout(120):
        async with session.get(_url, ssl=True, params=params, proxy=httpproxy) as response:
            resp = await response.text()
            if response.status == 429:  # 429 implies Too many requests i.e. Rate Limit Exceeded
                raise TokenExpiryException(loads(resp)['errors'][0]['message'])
            return resp
async def gettoken(__url):
    logme.debug(__name__ + ':get_token_new')
    a = await Request(__url, headers = {'User-Agent': random.choice(user_agent_list)})
    return a
class Token:
    def __init__(self, config):
        self._session = requests.Session()
        self._session.headers.update({'User-Agent': random.choice(user_agent_list)})
        self.config = config
        self._retries = 5
        self._timeout = 10
        self.url = 'https://twitter.com'

    def _request(self, proxy_host = None, proxy_port = None):
        for attempt in range(self._retries + 1):
            # The request is newly prepared on each retry because of potential cookie updates.
            req = self._session.prepare_request(requests.Request('GET', self.url))
            logme.debug(f'Retrieving {req.url}')
            try:
                if(proxy_host and proxy_port):
                    prox = "http://" + proxy_host + ":" + proxy_port
                    prox_full ={'http': prox}
                    logme.log(logme.WARNING, f'using proxy {prox}')
                    print("using proxy", flush = True)
                    self._session.proxies.update(prox_full)
                    r = self._session.send(req, allow_redirects=True, timeout=self._timeout)
                else:
                    r = self._session.send(req, allow_redirects=True, timeout=self._timeout)
            except requests.exceptions.RequestException as exc:
                if attempt < self._retries:
                    retrying = ', retrying'
                    level = logme.WARNING
                else:
                    retrying = ''
                    level = logme.ERROR
                logme.log(level, f'Error retrieving {req.url}: {exc!r}{retrying}')
            else:
                success, msg = (True, None)
                msg = f': {msg}' if msg else ''

                if success:
                    logme.debug(f'{req.url} retrieved successfully{msg}')
                    return r
            if attempt < self._retries:
                # TODO : might wanna tweak this back-off timer
                sleep_time = 2.0 * 2 ** attempt
                logme.info(f'Waiting {sleep_time:.0f} seconds')
                time.sleep(sleep_time)
        else:
            msg = f'{self._retries + 1} requests to {self.url} failed, giving up.'
            logme.fatal(msg)
            self.config.Guest_token = None
            raise RefreshTokenException(msg)

    def refresh(self):
        logme.debug('Retrieving guest token')
        print('DEBUG: Guest Token Retrieve Begin', flush = True)
        failure_count = 0
        res = None
        while(True):
            try:
                res = asyncio.run(gettoken(self.url))
            except Exception as s:                
                #When an exception happens, we check how many time it failed.
                #If failed less than 10 times, we try get the token again.
                failure_count += 1
                if failure_count <= 10:
                    delay = round(failure_count * 2, 1)
                    # This is not due to twitter throttling, so no need to sleep for a extended amount of time.
                    sys.stderr.write('sleeping for {} secs\n'.format(delay))
                    time.sleep(delay)
                    continue
                logme.critical(__name__ + ':Twint:Token:Get_Token_Error_Too_Many_Trials' + string(e))
                break
        print('DEBUG: Guest Token Refreshed.', flush = True)
        if res:
            match = re.search(r'\("gt=(\d+);', res)
        if match:
            logme.log(logme.WARNING, f'Found guest token in HTML')
            self.config.Guest_token = str(match.group(1))
        else:
            self.config.Guest_token = None
            print(res)
            raise RefreshTokenException('Could not find the Guest token in HTML')
            
