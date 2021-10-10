from pprint import pprint
from config import userid, password, header
import requests
import time
import math
import random
import base64
from hashlib import md5

login_check_param = 'login%5Buserid%5D=' + userid + '&' + \
                    'login%5Bpassword%5D=' + password + '&' + \
                    'login%5Bremember_me%5D=false'

url = [
    'https://fr.elvenar.com/',
    'https://fr.elvenar.com/glps/login_check',
    'https://fr0.elvenar.com/web/glps',
    'https://fr0.elvenar.com/web/login/play',
    'https://fr3.elvenar.com/game'
]

accept = [
    'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'application/json,text/plain,*/*',
    'application/json,text/javascript,*/*;q=0.01'
]

host = [
    'fr.elvenar.com',
    'fr0.elvenar.com',
    'fr3.elvenar.com'
]

get_key = 'MAW#YB*y06wqz$kTOE'

def createTid():
    return str(math.trunc(time.time() * 1000)) + '-' + \
           str(math.trunc((99999 - 10000) * random.random() + 10000))


# GET https://fr.elvenar.com/ -> fetch PHPSESSID & XSRF-TOKEN
def getTokens():
    h = header.copy()
    h['Accept'] = accept[0]
    h['Host'] = host[0]
    r = requests.get(url[0], headers = h)
    if r.status_code != requests.codes.ok:
        print(r.status_code, r.reason)
        print('GET', url[0])
        pprint(h)
        pprint(r.headers)
        return (None, None)
    return (r.cookies['PHPSESSID'], r.cookies['XSRF-TOKEN'])


# POST https://fr.elvenar.com/glps/login_check with login_check_param,
# -> fetch new PHPSESSID (and player ID ?)
def getNewPHP(phpsessid, xsrf):
    my_tid = createTid()
    h = header.copy()
    h['Accept'] = accept[1]
    h['Content-Length'] = str(len(login_check_param))
    h['Content-Type'] = 'application/x-www-form-urlencoded;charset=UTF-8'
    h['Cookie'] = 'PHPSESSID=' + phpsessid + ';' + \
                  'XSRF-TOKEN=' + xsrf + ';' + \
                  'device_view=full;' + \
                  'portal_tid=' + my_tid + ';' + \
                  'portal_data=portal_tid=' + my_tid
    h['Host'] = host[0]
    h['Referer'] = 'https://fr.elvenar.com/'
    h['X-Requested-With'] = 'XMLHttpRequest'
    h['X-XSRF-TOKEN'] = xsrf

    r = requests.post(url[1], headers = h, data = login_check_param)
    if r.status_code != requests.codes.ok:
        print(r.status_code, r.reason)
        print('POST', url[1])
        pprint(h)
        pprint(r.headers)
        return (None, my_tid)
    if r.json()['success'] != True:
        pprint(r.json())
#        pprint(r.json()['errors'])
        return (None, my_tid, None)

    return (r.cookies['PHPSESSID'], my_tid, str(r.json()['player_id']))

def getRedirLogin(phpsessid, xsrf, tid):
    h = header.copy()
    h['Accept'] = accept[0]
    h['Cookie'] = 'PHPSESSID=' + phpsessid + ';' + \
                  'XSRF-TOKEN=' + xsrf + ';' + \
                  'device_view=full;' + \
                  'portal_tid=' + tid + ';' + \
                  'portal_data=portal_tid=' + tid
    h['Host'] = host[0]
    h['Referer'] = 'https://fr.elvenar.com/'
    r = requests.get(url[0], headers = h, allow_redirects = False)
    if r.status_code != requests.codes.found:
        print(r.status_code, r.reason)
        print('GET', url[0])
        pprint(h)
        pprint(r.headers)
        return None
    new_url = r.headers['location']
    h = header.copy()
    h['Accept'] = accept[0]
    h['Host'] = host[1]
    h['Referer'] = 'https://fr.elvenar.com/'
    r = requests.get(new_url, headers = h, allow_redirects = False)
    if r.status_code != requests.codes.found:
        print(r.status_code, r.reason)
        print('GET', new_url)
        pprint(h)
        pprint(r.headers)
        return None
    my_mid = r.cookies['_mid']
    h['Cookie'] = '_mid=' + my_mid
    r = requests.get(url[2], headers = h)
    if r.status_code != requests.codes.ok:
        print(r.status_code, r.reason)
        print('GET', url[2])
        pprint(h)
        pprint(r.headers)
    return my_mid

def getWorldRedir(mid):
    params = 'world_id=fr3'
    my_tid = createTid()
    h = header.copy()
    h['Accept'] = accept[2]
    h['Content-Length'] = str(len(params))
    h['Content-Type'] = 'application/x-www-form-urlencoded;charset=UTF-8'
    h['Cookie'] = '_mid=' + mid + ';' + \
                  'ig_conv_last_site=' + url[2] + ';' + \
                  'portal_tid' + my_tid + ';' + \
                  'portal_ref_url=' + url[0] + ';' + \
                  'portal_ref_session=0;' + \
                  'portal_data=portal_tid=' + my_tid + \
                             '&portal_ref_url=' + url[0] + \
                             '&portal_ref_session=0'
    h['Host'] = host[1]
    h['Referer'] = url[2]
    h['X-Requested-With'] = 'XMLHttpRequest'
    r = requests.post(url[3], headers = h, data = params)
    if r.status_code != requests.codes.ok:
        print(r.status_code, r.reason)
        print('GET', url[2])
        pprint(h)
        pprint(r.headers)
        return (None, my_tid)
    return (r.json()['redirect'], my_tid)

def getSid(world_url):
    h = header.copy()
    h['Accept'] = accept[0]
    h['Cookie'] = 'ig_conv_last_site=' + url[2]
    h['Host'] = host[2]
    h['Referer'] = url[2]
    r = requests.get(world_url, headers = h, allow_redirects = False)
    if r.status_code != requests.codes.found:
        print(r.status_code, r.reason)
        print('GET', world_url)
        pprint(h)
        pprint(r.headers)
        return None
    return r.cookies['sid']

def getJsonGateway(sid):
    h = header.copy()
    h['Accept'] = accept[0]
    h['Cookie'] = 'ig_conv_last_site=' + url[2] + ';' + \
                  'sid=' + sid + ';' + \
                  'req_page_info=game_v1;' + \
                  'start_page_type=game;' + \
                  'start_page_version=v1'
    h['Host'] = host[2]
    h['Referer'] = url[2]
    r = requests.get(url[4], headers = h)
    if r.status_code != requests.codes.ok:
        print(r.status_code, r.reason)
        print('GET', url[4])
        pprint(h)
        pprint(r.headers)
        return None
    buf = r.text
    pos = buf.rfind('json_gateway_url')
    encoded_gateway = buf[pos - 1:].split()[1][1:-2]
    return 'https:' + base64.b64decode(encoded_gateway).decode()

def request(json_gateway, req, sid):
    h = header.copy()
    h['Accept'] = '*/*'
    h['Content-Length'] = str(len(req))
    h['Content-Type'] = 'application/json'
    h['Cookie'] = 'ig_conv_last_site=' + url[4] + ';' + \
                  'sid=' + sid + ';' + \
                  'req_page_info=game_v1;' + \
                  'start_page_type=game;' + \
                  'start_page_version=v1'
    h['Host'] = host[2]
    h['Os-type'] = 'browser'
    h['Referer'] = url[4]
    h['X-Requested-With'] = 'ElvenarHaxeClient'
    r = requests.post(json_gateway, headers = h, data = req)
    if r.status_code != requests.codes.ok:
        print(r.status_code, r.reason)
        print('GET', json_gateway)
        pprint(h)
        pprint(r.headers)
        return None
    return r.content

def forgeRequest(gateway_id, requestId, requestMethod, requestClass, requestData):
    req = [ {
        'requestId': requestId,
        'requestMethod': requestMethod,
        'requestClass': requestClass,
        'requestData': requestData,
        '__clazz__': 'ServerRequestVO'
    } ]
    req_str = str(req).replace(' ', '')
    req_str = req_str.replace("'", '"')
    concat = gateway_id + get_key + req_str
    return md5(concat.encode('utf-8')).hexdigest()[:10] + req_str

def login():
    print("GET", url[0])
    (phpsessid, xsrf) = getTokens()
    if phpsessid == None or xsrf == None:
        print("Error: getTokens")
        return 1
    else:
        print("PHPSESSID=" + phpsessid)
        print("XSRF-TOKEN=" + xsrf)
        print()

    print("POST", url[1])
    (new_phpsessid, tid, player_id) = getNewPHP(phpsessid, xsrf)
    if new_phpsessid == None or tid == None or player_id == None:
        print("Error: getNewPHP")
        return 1
    else:
        print("PHPSESSID=" + new_phpsessid)
        print("tid:", tid)
        print()

    print("GET", url[0], '(authenticated)')
    mid = getRedirLogin(new_phpsessid, xsrf, tid)
    if mid == None:
        print("Error getting mid from redirection logins")
        return 1
    else:
        print("_mid=" + mid)
        print()

    print("POST", url[3])
    (new_url, new_tid) = getWorldRedir(mid)
    if new_url == None:
        print("Error getting world url and tokens")
        return 1
    else:
        print("world url:", new_url)
        print("tid:", new_tid)
        print()

    print("GET", new_url)
    sid = getSid(new_url)
    if sid == None:
        print("Error getting 'sid'")
        return 1
    else:
        print("sid=" + sid)
        print()

    print("GET", url[4])
    gateway = getJsonGateway(sid)
    if gateway == None:
        print("Error getting json gateway")
    else:
        print("json gateway:", gateway)
    login_data = {
        'PHPSESSID': phpsessid,
        'XSRF-TOKEN': xsrf,
        'PHPSESSID2': new_phpsessid,
        'tid': tid,
        'player_id': player_id,
        'mid': mid,
        'tid2': new_tid,
        'sid': sid,
        'json_gateway': gateway
    }
    return login_data
