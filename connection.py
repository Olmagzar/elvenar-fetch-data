from pprint import pprint
import json
import time
import math
import random
import base64
import brotli
import requests
from hashlib import md5

class ElvenarConnection():
    __worlds = [
        'Arendyll',
        'Winyandor',
        'Felyndral',
        'Khelonaar',
        'Elcysandir',
        'Sinya Arda',
        'Ceravyn',
        'Harandar'
    ]
    def __init__(self, login, passwd, country, world):
        self.__home_page = 'https://{}.elvenar.com/'.format(country)
        if world in self.__worlds:
            self.__world_id = '{}{}'.format(country, self.__worlds.index(world) + 1)
        elif country == 'beta':
            country = 'zz'
            world = 'zz1'
        else:
            raise Exception("World {} not found in the list".format(world))

        self.__login_check_params = 'login%5Buserid%5D={}&'.format(login) + \
                                    'login%5Bpassword%5D={}&'.format(passwd) + \
                                    'login%5Bremember_me%5D=false'
        self.__login_page = '{}glps/login_check'.format(self.__home_page)
        self.__world_selection_page = 'https://{}0.elvenar.com/web/glps'.format(country)
        self.__ask_world_page = 'https://{}0.elvenar.com/web/login/play'.format(country)
        self.__selected_world_page = 'https://{}.elvenar.com/game'.format(self.__world_id)
        self.__world_logout_page = '{}/logout'.format(self.__selected_world_page)
        self.__world_selection_logout_page = 'https://{}0.elvenar.com/web/web/login/logout'.format(country)
        self.__home_logout_page = '{}glps/logout'.format(self.__home_page)

        self.__player_id = ''
        self.__headers = {
            'Accept': '',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en,q=0.5',
            'Connection': 'keep-alive',
            'Host': '',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:68.0) Gecko/20100101 Goanna/4.8 Firefox 68.0 PaleMoon/29.4.2.1'
        }

    def __getPlayerID(self):
        return self.__player_id
    player_id = property(__getPlayerID)

    def __emitGET(self, url, cookie = None, referer = None):
        h = self.__headers.copy()
        h['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        h['Host'] =  url.split('/')[2]
        if cookie != None:
            h['Cookie'] = cookie
        if referer != None:
            h['Referer'] = referer

        r = requests.get(url, headers = h, allow_redirects = False)
        if r.status_code != requests.codes.ok and \
           r.status_code != requests.codes.found:
            print(r.status_code, r.reason)
            print('GET', url)
            pprint(h)
            pprint(r.headers)
            return None
        return r

    # GET https://fr.elvenar.com/ -> fetch PHPSESSID & XSRF-TOKEN
    def __getTokens(self):
        r = self.__emitGET(self.__home_page)
        if r == None:
            raise Exception("Could not retrieve initial tokens")
        else:
            self.__phpsessid = r.cookies['PHPSESSID']
            self.__xsrf = r.cookies['XSRF-TOKEN']

    def __getSid(self):
        cookie = 'ig_conv_last_site={}'.format(self.__world_selection_page)
        r = self.__emitGET(self.__world_url, cookie, self.__world_selection_page)
        if r == None:
            raise Exception("Could not retrieve session ID")
        else:
            self.__sid = r.cookies['sid']

    def __getJsonGateway(self):
        cookie = 'ig_conv_last_site={};'.format(self.__world_selection_page) + \
                 'sid={};'.format(self.__sid) + \
                 'req_page_info=game_v1;' + \
                 'start_page_type=game;' + \
                 'start_page_version=v1'
        r = self.__emitGET(self.__selected_world_page, cookie, self.__world_selection_page)
        if r == None:
            raise Exception("Could not retrieve selected world page")
        else:
            buf = r.text
            pos = buf.rfind('json_gateway_url')
            if pos == -1:
                raise Exception("Could not retrieve 'json_gateway_url'")
            else:
                encoded_gateway = buf[pos - 1:].split()[1][1:-2]
                self.__json_gateway = 'https:' + base64.b64decode(encoded_gateway).decode()
                self.__json_id = self.__json_gateway[36:]

    def __getRedirLogin(self):
        cookie = 'PHPSESSID={};'.format(self.__phpsessid2) + \
                 'XSRF-TOKEN={};'.format(self.__xsrf) + \
                 'device_view=full;' + \
                 'portal_tid={};'.format(self.__tid) + \
                 'portal_data=portal_tid={}'.format(self.__tid)
        r = self.__emitGET(self.__home_page, cookie, self.__home_page)
        if r == None:
            raise Exception("Could not get logged in page")
        url = r.headers['location']
        r = self.__emitGET(url, referer = self.__home_page)
        if r == None:
            raise Exception("Could note get credential page")
        self.__mid = r.cookies['_mid']
        cookie = '_mid={}'.format(self.__mid)
        r = self.__emitGET(self.__world_selection_page, cookie, self.__home_page)
        if r == None:
            raise Exception("Could not get world selection page")

    def __emitPOST(self, accept, url, cookie, params, referer, token = None):
        h = self.__headers.copy()
        h['Accept'] = accept
        h['Content-Length'] = str(len(params))
        h['Content-Type'] = 'application/x-www-form-urlencoded;charset=UTF-8'
        h['Cookie'] = cookie
        h['Host'] = url.split('/')[2]
        h['Referer'] = referer
        h['X-Requested-With'] = 'XMLHttpRequest'
        if token != None:
            h['X-XSRF-TOKEN'] = token
        r = requests.post(url, headers = h, data = params)
        if r.status_code != requests.codes.ok:
            print(r.status_code, r.reason)
            print('POST', url)
            pprint(h)
            pprint(r.headers)
            return None
        return r

    @staticmethod
    def __createTid():
        return str(math.trunc(time.time() * 1000)) + '-' + \
               str(math.trunc((99999 - 10000) * random.random() + 10000))

    # POST https://fr.elvenar.com/glps/login_check with login_check_param,
    # -> fetch new PHPSESSID and player ID
    def __getNewPHP(self):
        accept = 'application/json,text/plain,*/*'
        self.__tid = self.__createTid()
        cookie = 'PHPSESSID={};'.format(self.__phpsessid) + \
                 'XSRF-TOKEN={};'.format(self.__xsrf) + \
                 'device_view=full;' + \
                 'portal_tid={};'.format(self.__tid) + \
                 'portal_data=portal_tid={}'.format(self.__tid)
        r = self.__emitPOST(accept, self.__login_page, cookie,
                            self.__login_check_params,
                            self.__home_page, self.__xsrf)
        if r == None:
            raise Exception("Could not post login credentials")
        elif r.json()['success'] != True:
            pprint(r.json())
            raise Exception("Could not login")
        else:
            self.__phpsessid2 = r.cookies['PHPSESSID']
            self.__player_id = str(r.json()['player_id'])

    def __getWorldRedir(self):
        accept = 'application/json,text/javascript,*/*;q=0.01'
        params = 'world_id={}'.format(self.__world_id)
        self.__tid2 = self.__createTid()
        cookie = '_mid={};'.format(self.__mid) + \
                 'ig_conv_last_site={};'.format(self.__world_selection_page) + \
                 'portal_tid={};'.format(self.__tid2) + \
                 'portal_ref_url={};'.format(self.__home_page) + \
                 'portal_ref_session=0;' + \
                 'portal_data=portal_tid={}'.format(self.__tid2) + \
                            '&portal_ref_url={}'.format(self.__home_page) + \
                            '&portal_ref_session=0'
        r = self.__emitPOST(accept, self.__ask_world_page, cookie, params,
                            self.__world_selection_page)
        if r == None:
            raise Exception("Could not post world selection")
        else:
            self.__world_url = r.json()['redirect']
            self.__cid = r.cookies['cid']

    def login(self):
        try:
            self.__getTokens()
            self.__getNewPHP()
            self.__getRedirLogin()
            self.__getWorldRedir()
            self.__getSid()
            self.__getJsonGateway()
        except:
            raise

    def logout(self):
        cookie = 'ig_conv_last_site={};'.format(self.__selected_world_page) + \
                 'sid={};'.format(self.__sid) + \
                 'req_page_info=game_v1;' + \
                 'start_page_type=game;' + \
                 'start_page_version=v1'
        r = self.__emitGET(self.__world_logout_page, cookie,
                           self.__selected_world_page)
        if r == None:
            raise Exception("Could not get world logout page")

        cookie = '_mid={};'.format(self.__mid) + \
                 'ig_conv_last_site={};'.format(self.__selected_world_page) + \
                 'portal_tid={};'.format(self.__tid2) + \
                 'portal_ref_url={};'.format(self.__home_page) + \
                 'portal_ref_session=1;' + \
                 'portal_data=portal_tid={}'.format(self.__tid2) + \
                            '&portal_ref_url={}'.format(self.__home_page) + \
                            '&portal_ref_session=1;' + \
                 'cid={}'.format(self.__cid)
        r = self.__emitGET(self.__world_selection_page, cookie,
                           self.__selected_world_page)
        if r == None:
            raise Exception("Could not get world selection page on way out")

        cookie = '_mid={};'.format(self.__mid) + \
                 'ig_conv_last_site={};'.format(self.__world_selection_page) + \
                 'portal_tid={};'.format(self.__tid2) + \
                 'portal_ref_url={};'.format(self.__selected_world_page) + \
                 'portal_ref_session=1;' + \
                 'portal_data=portal_tid={}'.format(self.__tid2) + \
                            '&portal_ref_url={}'.format(self.__selected_world_page) + \
                            '&portal_ref_session=1;' + \
                 'cid={}'.format(self.__cid)
        r = self.__emitGET(self.__world_selection_logout_page, cookie,
                           self.__world_selection_page)
        if r == None:
            raise Exception("Could not get world selection logout page")

        cookie = 'PHPSESSID={};'.format(self.__phpsessid2) + \
                 'device_view=full;' + \
                 'portal_tid={};'.format(self.__tid) + \
                 'portal_data=portal_tid={};'.format(self.__tid) + \
                 'ig_conv_last_site={}'.format(self.__world_selection_page)
        r = self.__emitGET(self.__home_logout_page, cookie,
                           self.__world_selection_page)
        if r == None:
            raise Exception("Could not get home logout page")

        cookie = 'PHPSESSID={};'.format(r.cookies['PHPSESSID']) + \
                 'XSRF-TOKEN={};'.format(r.cookies['XSRF-TOKEN']) + \
                 'device_view=full;' + \
                 'portal_tid={};'.format(self.__tid) + \
                 'portal_data=portal_tid={};'.format(self.__tid) + \
                 'ig_conv_last_site={}'.format(self.__world_selection_page)
        r = self.__emitGET(self.__home_page, cookie,
                           self.__world_selection_page)
        if r == None:
            raise Exception("Could not get home page on way out")

    def __forgeRequest(self, request):
        get_key = 'MAW#YB*y06wqz$kTOE'
        req_str = json.dumps(request, separators=(',',':'))
        concat = self.__json_id + get_key + req_str
        return md5(concat.encode('utf-8')).hexdigest()[:10] + req_str

    def request(self, rq):
        payload = self.__forgeRequest(rq)
        h = self.__headers.copy()
        h['Accept'] = '*/*'
        h['Content-Length'] = str(len(payload))
        h['Content-Type'] = 'application/json'
        h['Cookie'] = 'ig_conv_last_site={};'.format(self.__selected_world_page) + \
                      'sid={};'.format(self.__sid) + \
                      'req_page_info=game_v1;' + \
                      'start_page_type=game;' + \
                      'start_page_version=v1'
        h['Host'] = self.__selected_world_page.split('/')[2]
        h['Os-type'] = 'browser'
        h['Referer'] = self.__selected_world_page
        h['X-Requested-With'] = 'ElvenarHaxeClient'
        r = requests.post(self.__json_gateway, headers = h, data = payload)
        if r.status_code != requests.codes.ok:
            print(r.status_code, r.reason)
            print('POST', self.__json_gateway)
            pprint(h)
            pprint(r.headers)
            return None
        return r.content
