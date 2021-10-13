from pprint import pprint
from config import userid, password, header
import requests
import time
import math
import random
import base64
import os
import stat
import json
from hashlib import md5

login_check_param = 'login%5Buserid%5D=' + userid + '&' + \
                    'login%5Bpassword%5D=' + password + '&' + \
                    'login%5Bremember_me%5D=false'

url = [
    'https://fr.elvenar.com/',
    'https://fr.elvenar.com/glps/login_check',
    'https://fr0.elvenar.com/web/glps',
    'https://fr0.elvenar.com/web/login/play',
    'https://fr3.elvenar.com/game',
    'https://fr3.elvenar.com/game/logout',
    'https://fr0.elvenar.com/web/web/login/logout',
    'https://fr.elvenar.com/glps/logout'
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

def main():
    print("[....] LOGIN")
    cred = login()
    UP = "\x1b[3A"
    CLR = "\x1b[0K"
    GOOD = "\033[38;5;34m"
    BAD = "\033[38;5;1m"
    RES = "\033[0m"
    if cred != None:
        print(f"\n\n{UP}[ {GOOD}OK{RES} ]")

        fd = os.open('players.json', os.O_CREAT|os.O_WRONLY)
        os.chmod(fd, stat.S_IRUSR|stat.S_IWUSR|stat.S_IRGRP|stat.S_IROTH)
        os.write(fd, b'[')
        #pprint(cred)
        nb_ghosts = 0
        ghosts = [0 for i in range(19)]

        reqId = 1
        payload = forgeRequest(cred['json_id'], reqId, 'fetchInitialWorldMapData', 'WorldMapService', [])
        data = request(cred['json_gateway'], payload, cred['sid'])
        data = json.loads(data.decode())[0]['responseData']
        if data['__class__'] == 'GameExceptionVO':
            print("fetchInitialWorldMapData failed, aborting")
            print("[....] LOGOUT")
            rc = logout(cred)
            if rc != 0:
                print(f"\n\n{UP}[ {BAD}KO{RES} ]")
            else:
                print(f"\n\n{UP}[ {GOOD}OK{RES} ]")
            return 1
        data = data['player_world_map_area_vo']['provinces']
        me = [ p for p in data
                    if (p['__class__'] == 'PlayerProvinceVO' and str(p['player_id']) == cred['player_id'])
             ][0]

        # Get player list
        reqId += 1
        payload = forgeRequest(cred['json_id'], reqId, 'accessRanking', 'RankingService', ['player',999999,0])
        data = request(cred['json_gateway'], payload, cred['sid'])
        data = json.loads(data.decode())[0]['responseData']
        if data['__class__'] == 'GameExceptionVO':
            print("AccessRanking error for players, aborting")
            print("[....] LOGOUT")
            rc = logout(cred)
            if rc != 0:
                print(f"\n\n{UP}[ {BAD}KO{RES} ]")
            else:
                print(f"\n\n{UP}[ {GOOD}OK{RES} ]")
            return 1

        print('[....] fetch players')
        rc = 1
        data = data['rankings']
        print('0/' + str(len(data)))
        i = 1
        for player in data:
            print(f"\n\n{UP}" + str(i) + '/' + str(len(data)) + f"{CLR}")
            i += 1
            # Get location
            reqId += 1
            payload_player = forgeRequest(cred['json_id'], reqId, 'visitPlayer',
                                          'OtherPlayerService',
                                          [player['player']['player_id']])
            data_player = request(cred['json_gateway'], payload_player, cred['sid'])
            data_player = json.loads(data_player.decode())[0]['responseData']
            if data_player['__class__'] == 'GameExceptionVO':
                print("visitPlayer error -", player['player']['name'])
                break

            tech = data_player['technologySection']
            data_player = data_player['other_player']
            if data_player['player_id'] != player['player']['player_id']:
                print("WARNING: player", player['player']['name'], "(" + data_player['name'] + ")",
                      'has incoherent IDs:', player['player']['player_id'] + '/' + data_player['player_id'])

            if not 'r' in data_player['location']:
                data_player['location']['r'] = 0
            if not 'q' in data_player['location']:
                data_player['location']['q'] = 0

            if data_player['location']['r'] == me['r'] \
               and data_player['location']['q'] == me['q'] \
               and data_player['player_id'] != me['player_id']:
                nb_ghosts += 1
                ghosts[tech] += 1
                continue

            tmp = {
                'id': data_player['player_id'],
                'name': data_player['name'],
                'x': data_player['location']['r'],
                'y': data_player['location']['q']
            }
            # Get encounter score
            reqId += 1
            payload_points = forgeRequest(cred['json_id'], reqId, 'getRankingOverview',
                                          'RankingService', [player['player']['player_id']])
            city_points = request(cred['json_gateway'], payload_points, cred['sid'])
            city_points = json.loads(city_points.decode())[0]
            if city_points['requestClass'] == 'ExceptionService':
                print("getRankingOverview error -", data_player['name'])
                break

            for elt in city_points['responseData']:
                if elt['category'] != 'encounters':
                    continue
                tmp['encounter'] = elt['score']

            if 'guild_info' in data_player:
                tmp['guild_id'] = data_player['guild_info']['id']
                tmp['guild_name'] = data_player['guild_info']['name']

            buf = json.dumps(tmp).encode()
            os.write(fd, buf + ',')
            rc = 0

        if rc != 0:
            print(f"{UP}[ {BAD}KO{RES} ]\n")
        else:
            print(f"\n{UP}[ {GOOD}OK{RES} ]\n{CLR}", end='')

        os.write(fd, b']')
        os.close(fd)
        print('Found', nb_ghosts, 'ghost cities.')
        pprint(ghosts)
        print("[....] LOGOUT")
        rc = logout(cred)
        if rc != 0:
            print(f"\n\n{UP}[ {BAD}KO{RES} ]")
        else:
            print(f"\n\n{UP}[ {GOOD}OK{RES} ]")
    else:
        print(f"\n\n{UP}[ {BAD}KO{RES} ]")

if __name__ == '__main__':
    main()
