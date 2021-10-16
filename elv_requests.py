from config import header, get_key, url, host
from pprint import pprint
from hashlib import md5
import requests
import json

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
        print('POST', json_gateway)
        pprint(h)
        pprint(r.headers)
        return None
    return r.content

def createRequest(requestId, requestMethod, requestClass, requestData):
    req = [ {
        'requestId': requestId,
        'requestMethod': requestMethod,
        'requestClass': requestClass,
        'requestData': requestData,
        '__clazz__': 'ServerRequestVO'
    } ]
    return req

def forgeRequest(gateway_id, request):
    req_str = json.dumps(request).replace(' ', '')
    concat = gateway_id + get_key + req_str
    return md5(concat.encode('utf-8')).hexdigest()[:10] + req_str
