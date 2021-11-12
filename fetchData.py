from pprint import pprint
from connection import login, logout
from elv_requests import createRequest, forgeRequest, request
from config import db_file
import os
import stat
import json
import time
from hashlib import md5

ghosts = [0 for i in range(19)]

def getName(players, player_id):
    return [ p['player']['player_name'] for p in players \
                 if p['player']['player_id'] == player_id ][0]

def processResp(data, me, rqIds, players, player_list, tguilds):
    if data['requestClass'] == 'ExceptionService':
        fd = os.open('errors.txt', os.O_CREAT|os.O_APPEND|os.O_WRONLY)
        os.chmod(fd, stat.S_IRUSR|stat.S_IWUSR|stat.S_IRGRP|stat.S_IROTH)
        os.write(fd, json.dumps(data).encode())
        os.write(fd, b'\n')
        os.close(fd)
        return
    elif data['requestClass'] == 'OtherPlayerService' and \
         data['requestMethod'] == 'visitPlayer':
        player = data['responseData']
        if 'technologySection' in player:
            tech = player['technologySection']
        else:
            player_id = str(rqIds[data['requestId']])
            player_name = getName(players, player_id)
            fd = os.open('errors.txt', os.O_CREAT|os.O_APPEND|os.O_WRONLY)
            os.chmod(fd, stat.S_IRUSR|stat.S_IWUSR|stat.S_IRGRP|stat.S_IROTH)
            os.write(fd, ('WARNING: player ' + player_name + \
                          ' (' + player_id + ') has no tech.\n').encode())
            os.close(fd)
            tech = 0

        city = player['city_map']['entities']
        city_hash = md5(json.dumps(city).encode()).hexdigest()
        # Coeur de la montagne : B_Dwarfs_AW2_X -> goods bonus
        # Centre d'échange     : B_Gr6_AW2_X    -> manuf spell pickup bonus
        # Voyage temporel      : B_Gr9_AW1_X    -> sensible goods bonus
        # Vortex de stockage   : B_Gr10_AW1_X   -> sensible goods bonus
        # Arbre d'illumination : B_****_AW?_X   -> ascendant goods bonus
        buildings = { b['id']: (b['cityentity_id'], b['level'], 'connected' in b) for b in city \
                        if b['type'] == 'goods' \
                        or 'B_Dwarfs_AW2_' in b['cityentity_id'] \
                        or 'B_Gr6_AW2_' in b['cityentity_id'] \
                        or 'B_Gr9_AW1_' in b['cityentity_id'] \
                        or 'B_Gr10_AW1_' in b['cityentity_id'] }

        # Effects:
        # - 'good_production_boost_spell'    (manuf enchantée, ownerId, remainingTime)
        # - 'manufactories_production_boost' (phénix doré, remainingTime)
        # - 'increase_spell_power_boost'     (phénix des tempêtes, remainingTime)
        effects = {}
        if 'effects' in player:
            for e in player['effects']:
                if e['actionId'] in ('good_production_boost_spell', \
                                     'manufactories_production_boost', \
                                     'increase_spell_power_boost') \
                   and 'remainingTime' in e:
                    effects[e['ownerId']] = (e['actionId'], e['remainingTime'])

        player = player['other_player']
        player_id = str(player['player_id'])
        if not 'r' in player['location']:
            player['location']['r'] = 0
        if not 'q' in player['location']:
            player['location']['q'] = 0
        if player['location']['r'] == me['r'] \
           and player['location']['q'] == me['q'] \
           and player_id != str(me['player_id']):
            player_list[player_id]['ghost'] = True
            player_list[player_id]['active_period'] = 0
            player_list[player_id]['active'] = False
            ghosts[tech] += 1
        else:
            player_list[player_id]['ghost'] = False

        if ('city_hash' in player_list[player_id] and \
            player_list[player_id]['city_hash'] != city_hash) \
           or effects != {}:
            player_list[player_id]['active'] = True
            if player_list[player_id]['ghost'] == True:
                print('mark ghost active', effects != {})

        player_list[player_id]['name'] = player['name']
        player_list[player_id]['x'] = player['location']['r']
        player_list[player_id]['y'] = player['location']['q']
        player_list[player_id]['encounter'] = 0
        player_list[player_id]['tech'] = tech
        player_list[player_id]['city_hash'] = city_hash
        player_list[player_id]['buildings'] = buildings
        player_list[player_id]['effects'] = effects

        if 'guild_info' in player:
            player_list[player_id]['guild_id'] = player['guild_info']['id']
            player_list[player_id]['guild_name'] = player['guild_info']['name']
            if player['guild_info']['id'] in tguilds:
                player_list[player_id]['active_guild'] = True
        else:
            if 'guild_id' in player_list[player_id]:
                trash = player_list[player_id].pop('guild_id')
                trash = player_list[player_id].pop('guild_name')
            trash = player_list[player_id].pop('active_guild')
    elif data['requestClass'] == 'RankingService' and \
         data['requestMethod'] == 'getRankingOverview':
        player_id = str(rqIds[data['requestId']])
        score_hash = md5(json.dumps(data['responseData']).encode()).hexdigest()
        if 'score_hash' in player_list[player_id] and \
           player_list[player_id]['score_hash'] != score_hash:
            player_list[player_id]['active'] = True
            if player_list[player_id]['ghost'] == True:
                print('(2) mark ghost active')
        player_list[player_id]['score_hash'] = score_hash
        for elt in data['responseData']:
            if elt['category'] != 'encounters':
                continue
            player_list[player_id]['encounter'] = elt['score']
    else:
        fd = os.open('errors.txt', os.O_CREAT|os.O_APPEND|os.O_WRONLY)
        os.chmod(fd, stat.S_IRUSR|stat.S_IWUSR|stat.S_IRGRP|stat.S_IROTH)
        os.write(fd, json.dumps(data).encode())
        os.write(fd, b'\n')
        os.close(fd)


def main():
    print("[....] Login")
    cred = login()
    UP = "\x1b[3A"
    CLR = "\x1b[0K"
    GOOD = "\033[38;5;34m"
    BAD = "\033[38;5;1m"
    RES = "\033[0m"
    if cred != None:
        print(f"\n\n{UP}[ {GOOD}OK{RES} ]")

        print("[....] Get cartographer details")
        reqId = 1
        rq = createRequest(reqId, 'fetchInitialWorldMapData', 'WorldMapService', [])
        payload = forgeRequest(cred['json_id'], rq)
        data = request(cred['json_gateway'], payload, cred['sid'])
        #data = json.loads(data.decode())[0]
        for data in json.loads(data.decode()):
            if data['requestClass'] == 'ExceptionService':
                print("fetchInitialWorldMapData failed, aborting")
                pprint(data)
                print("[....] Logout")
                rc = logout(cred)
                if rc != 0:
                    print(f"\n\n{UP}[{BAD}FAIL{RES}]")
                else:
                    print(f"\n\n{UP}[ {GOOD}OK{RES} ]")
                return 1
            elif data['requestClass'] == 'WorldMapService' and \
                 data['requestMethod'] == 'fetchInitialWorldMapData':
                provinces = data['responseData']['player_world_map_area_vo']['provinces']
                me = [ p for p in provinces
                            if (p['__class__'] == 'PlayerProvinceVO' and str(p['player_id']) == cred['player_id'])
                     ][0]
                print(f"\n\n{UP}[ {GOOD}OK{RES} ]")

        # Get player list
        print("[....] Get list of players")
        reqId += 1
        rq = createRequest(reqId, 'accessRanking', 'RankingService', ['player',999999,0])
        payload = forgeRequest(cred['json_id'], rq)
        data = request(cred['json_gateway'], payload, cred['sid'])
        data = json.loads(data.decode())[0]
        if data['requestClass'] == 'ExceptionService':
            print(f"\n\n{UP}[{BAD}FAIL{RES}]")
            pprint(data)
            print("[....] Logout")
            rc = logout(cred)
            if rc != 0:
                print(f"\n\n{UP}[{BAD}FAIL{RES}]")
            else:
                print(f"\n\n{UP}[ {GOOD}OK{RES} ]")
            return 1

        players = data['responseData']['rankings']
        print(f"\n\n{UP}[ {GOOD}OK{RES} ]")

        if os.path.exists(db_file):
            print('[....] Load local database')
            sz = os.path.getsize(db_file)
            fd = os.open(db_file, os.O_RDONLY)
            buf = os.read(fd, sz)
            os.close(fd)
            player_list = json.loads(buf.decode())
            print(f"\n\n{UP}[ {GOOD}OK{RES} ]")
        else:
            player_list = {}

        print('[....] Initialize memory')
        id_list = []
        mark_act = 0
        mark_inact = 0
        mark_new = 0
        for p in players:
            if not 'points' in p:
                p['points'] = 0
            player_id = str(p['player']['player_id'])
            id_list += [player_id]
            if player_id in player_list:
                if player_list[player_id]['points'] != p['points']:
                    player_list[player_id]['active'] = True
                    player_list[player_id]['active_guild'] = True
                    mark_act += 1
                else:
                    player_list[player_id]['active'] = False
                    player_list[player_id]['active_guild'] = False
                    mark_inact += 1
            else:
                player_list[player_id] = { 'active': True, 'active_guild': True, 'tournament': 0 }
                mark_new += 1
            player_list[player_id]['points'] = p['points']
        print(f"\n\n{UP}[ {GOOD}OK{RES} ] Initialize memory (" + str(mark_act) + ", " + str(mark_inact) + ", " + str(mark_new) + ")")

        print("[....] Mark tournament players active")
        reqId += 1
        rq = createRequest(reqId, 'accessRanking', 'RankingService', ['tournament',999999,0])
        payload = forgeRequest(cred['json_id'], rq)
        data = request(cred['json_gateway'], payload, cred['sid'])
        data = json.loads(data.decode())[0]
        tguilds = []
        mark_t = 0
        if data['requestClass'] == 'ExceptionService':
            print(f"\n\n{UP}[{BAD}FAIL{RES}]")
            pprint(data)
        else:
            tplayers = data['responseData']['rankings']
            for p in tplayers:
                player_id = str(p['player']['player_id'])
                if player_list[player_id]['tournament'] != p['points']:
                    player_list[player_id]['active'] = True
                player_list[player_id]['active_guild'] = True
                player_list[player_id]['tournament'] = p['points']
                mark_t += 1
                if 'guildInfo' in p:
                    tguilds += [p['guildInfo']['id']]
            print(f"\n\n{UP}[ {GOOD}OK{RES} ] Mark tournament players active (" + str(mark_t) + ")")

        if time.gmtime().tm_wday == 0:
            for player_id in player_list:
                player_list[player_id]['tournament'] = 0

        print('[....] Download players')
        print('0/' + str(len(players)))
        i = 0
        request_list = []
        rqIds = {}
        for player_id in id_list:
            i += 1
            print(f"\n\n{UP}" + str(i) + '/' + str(len(id_list)) + f"{CLR}")

            # Get location
            reqId += 1
            rq = createRequest(reqId, 'visitPlayer',
                               'OtherPlayerService', [player_id])
            rqIds[reqId] = player_id
            request_list += rq
            reqId += 1
            rq = createRequest(reqId, 'getRankingOverview',
                               'RankingService', [player_id])
            rqIds[reqId] = player_id
            request_list += rq
            if len(request_list) >= 50 or i == len(id_list):
                payload = forgeRequest(cred['json_id'], request_list)
                data = request(cred['json_gateway'], payload, cred['sid'])
                data = json.loads(data.decode())

                for idx in range(len(data)):
                    processResp(data[idx], me, rqIds, players, player_list, tguilds)
                request_list = []
                rqIds = {}

        if i != len(id_list):
            print(f"{UP}[{BAD}FAIL{RES}]\n")
        else:
            print(f"\n{UP}[ {GOOD}OK{RES} ]\n{CLR}", end='')

        print("[....] Mark spire guilds active")
        reqId += 1
        rq = createRequest(reqId, 'accessRanking', 'RankingService', ['previous_spire',999999,0])
        payload = forgeRequest(cred['json_id'], rq)
        data = request(cred['json_gateway'], payload, cred['sid'])
        data = json.loads(data.decode())[0]['responseData']
        if data['__class__'] == 'GameExceptionVO':
            print(f"\n\n{UP}[{BAD}FAIL{RES}]")
        else:
            guilds = data['rankings']
            guild_ids = [ g['guildInfo']['id'] for g in guilds ]
            for p_id in player_list:
                p = player_list[p_id]
                if 'guild_id' in p and p['guild_id'] in guild_ids:
                    p['active_guild'] = True
            print(f"\n\n{UP}[ {GOOD}OK{RES} ]")

        print("[....] Mark event guilds active")
        reqId += 1
        rq = createRequest(reqId, 'accessRanking', 'RankingService', ['guild_event',999999,0])
        payload = forgeRequest(cred['json_id'], rq)
        data = request(cred['json_gateway'], payload, cred['sid'])
        data = json.loads(data.decode())[0]['responseData']
        if data['__class__'] == 'GameExceptionVO':
            print(f"\n\n{UP}[{BAD}FAIL{RES}]")
        else:
            guilds = data['rankings']
            guild_ids = [ g['guildInfo']['id'] for g in guilds ]
            for p_id in player_list:
                p = player_list[p_id]
                if 'guild_id' in p and p['guild_id'] in guild_ids:
                    p['active_guild'] = True
            print(f"\n\n{UP}[ {GOOD}OK{RES} ]")

        if os.path.exists(db_file):
            print("[....] Remove deleted accounts")
            list_copy = player_list.copy()
            for player_id in list_copy.keys():
                if not player_id in id_list:
                    trash = player_list.pop(player_id)
            print(f"\n\n{UP}[ {GOOD}OK{RES} ]")
            os.remove(db_file)

        print("[....] Update active period")
        for player_id in player_list:
            active = player_list[player_id].pop('active')
            if active == True:
                player_list[player_id]['active_period'] = 35
            else:
                period = player_list[player_id]['active_period']
                player_list[player_id]['active_period'] = max(period - 1, 0)
        print(f"\n\n{UP}[ {GOOD}OK{RES} ]")

        print("[....] Write database")
        fd = os.open(db_file, os.O_CREAT|os.O_WRONLY)
        os.chmod(fd, stat.S_IRUSR|stat.S_IWUSR|stat.S_IRGRP|stat.S_IROTH)
        buf = json.dumps(player_list).encode()
        os.write(fd, buf)
        os.close(fd)
        ts = time.gmtime()
        ts = "{}{:02}{:02}_{:02}{:02}".format(ts.tm_year, ts.tm_mon, ts.tm_mday,
                                              ts.tm_hour, ts.tm_min)
        db_file2 = db_file[:-len('.json')] + '-' + ts + '.json'
        fd = os.open(db_file2, os.O_CREAT|os.O_WRONLY)
        os.chmod(fd, stat.S_IRUSR|stat.S_IWUSR|stat.S_IRGRP|stat.S_IROTH)
        buf = json.dumps(player_list).encode()
        os.write(fd, buf)
        os.close(fd)
        print(f"\n\n{UP}[ {GOOD}OK{RES} ]")
        print('Found', sum(ghosts), 'ghost cities.')
        pprint(ghosts)
        print("[....] Logout")
        rc = logout(cred)
        if rc != 0:
            print(f"\n\n{UP}[{BAD}FAIL{RES}]")
        else:
            print(f"\n\n{UP}[ {GOOD}OK{RES} ]")
    else:
        print(f"\n\n{UP}[{BAD}FAIL{RES}]")

if __name__ == '__main__':
    main()
