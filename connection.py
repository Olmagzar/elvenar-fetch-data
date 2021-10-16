from config import userid, password, header, url, accept, host
from pprint import pprint
import time
import math
import random
import base64
import requests

login_check_param = 'login%5Buserid%5D=' + userid + '&' + \
                    'login%5Bpassword%5D=' + password + '&' + \
                    'login%5Bremember_me%5D=false'

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
    return (r.json()['redirect'], my_tid, r.cookies['cid'])

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

def login():
    (phpsessid, xsrf) = getTokens()
    if phpsessid == None or xsrf == None:
        print("Error: getTokens")
        return None

    (new_phpsessid, tid, player_id) = getNewPHP(phpsessid, xsrf)
    if new_phpsessid == None or tid == None or player_id == None:
        print("Error: getNewPHP")
        return None

    mid = getRedirLogin(new_phpsessid, xsrf, tid)
    if mid == None:
        print("Error getting mid from redirection logins")
        return None

    (new_url, new_tid, cid) = getWorldRedir(mid)
    if new_url == None:
        print("Error getting world url and tokens")
        return None

    sid = getSid(new_url)
    if sid == None:
        print("Error getting 'sid'")
        return None

    gateway = getJsonGateway(sid)
    if gateway == None:
        print("Error getting json gateway")
    login_data = {
        'PHPSESSID': phpsessid,
        'XSRF-TOKEN': xsrf,
        'PHPSESSID2': new_phpsessid,
        'tid': tid,
        'player_id': player_id,
        'mid': mid,
        'tid2': new_tid,
        'cid': cid,
        'sid': sid,
        'json_gateway': gateway,
        'json_id': gateway[36:]
    }
    return login_data

def logout(cred):
    sid = cred['sid']
    mid = cred['mid']
    tid2 = cred['tid2']
    cid = cred['cid']
    phpsessid2 = cred['PHPSESSID2']
    xsrf = cred['XSRF-TOKEN']
    tid = cred['tid']
    h = header.copy()
    h['Accept'] = accept[0]
    h['Cookie'] = 'ig_conv_last_site=' + url[4] + ';' + \
                  'sid=' + sid + ';' + \
                  'req_page_info=game_v1;' + \
                  'start_page_type=game;' + \
                  'start_page_version=v1'
    h['Host'] = host[2]
    h['Referer'] = url[4]
    r = requests.get(url[5], headers = h, allow_redirects = False)
    if r.status_code != requests.codes.found:
        print(r.status_code, r.reason)
        print('GET', url[5])
        pprint(h)
        pprint(r.headers)
        return 1

    h['Cookie'] = '_mid=' + mid + ';' + \
                  'ig_conv_last_site=' + url[4] + ';' + \
                  'portal_tid=' + tid2 + ';' + \
                  'portal_ref_url=' + url[0] + ';' + \
                  'portal_ref_session=1;' + \
                  'portal_data=portal_tid=' + tid2 + \
                             '&portal_ref_url=' + url[0] + ';' + \
                             '&portal_ref_session=1;' + \
                  'cid=' + cid
    h['Host'] = host[1]
    r = requests.get(url[2], headers = h)
    if r.status_code != requests.codes.ok:
        print(r.status_code, r.reason)
        print('GET', url[2])
        pprint(h)
        pprint(r.headers)
        return 1

    h['Cookie'] = '_mid=' + mid + ';' + \
                  'ig_conv_last_site=' + url[2] + ';' + \
                  'portal_tid=' + tid2 + ';' + \
                  'portal_ref_url=' + url[4] + ';' + \
                  'portal_ref_session=1;' + \
                  'portal_data=portal_tid=' + tid2 + \
                             '&portal_ref_url=' + url[4] + ';' + \
                             '&portal_ref_session=1;' + \
                  'cid=' + cid
    h['Referer'] = url[2]
    r = requests.get(url[6], headers = h, allow_redirects = False)
    if r.status_code != requests.codes.found:
        print(r.status_code, r.reason)
        print('GET', url[6])
        pprint(h)
        pprint(r.headers)
        return 1

    h['Cookie'] = 'PHPSESSID=' + phpsessid2 + ';' + \
                  'device_view=full;' + \
                  'portal_tid=' + tid + ';' + \
                  'portal_data=portal_tid=' + tid + ';' + \
                  'ig_conv_last_site=' + url[2]
    h['Host'] = host[0]
    r = requests.get(url[7], headers = h, allow_redirects = False)
    if r.status_code != requests.codes.found:
        print(r.status_code, r.reason)
        print('GET', url[6])
        pprint(h)
        pprint(r.headers)
        return 1

    h['Cookie'] = 'PHPSESSID=' + r.cookies['PHPSESSID'] + ';' + \
                  'XSRF-TOKEN=' + r.cookies['XSRF-TOKEN'] + ';' + \
                  'device_view=full;' + \
                  'portal_tid=' + tid + ';' + \
                  'portal_data=portal_tid=' + tid + ';' + \
                  'ig_conv_last_site=' + url[2]
    r = requests.get(url[0], headers = h)
    if r.status_code != requests.codes.ok:
        print(r.status_code, r.reason)
        print('GET', url[0])
        pprint(h)
        pprint(r.headers)
        return 1
    return 0
