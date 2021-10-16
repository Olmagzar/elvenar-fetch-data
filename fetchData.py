from pprint import pprint
from connection import login, logout
from elv_requests import forgeRequest, request
import os
import stat
import json


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

        fd = os.open('players.json', os.O_RDONLY)
        buf = os.read(fd, 1024 * 1024 * 40)
        os.close(fd)
        buf = buf[:-2] + b']'
        player_list = json.loads(buf.decode())
        id_list = [ p['id'] for p in player_list ]
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

        data = data['rankings']
        print('[....] fetch players')
        print('0/' + str(len(data)))
        i = 0
        new_id_list = [ p['player']['player_id'] for p in data ]
        for player in data:
            i += 1
            print(f"\n\n{UP}" + str(i) + '/' + str(len(data)) + ' ' + \
                    str(player['player']['player_id']) + f"{CLR}")

            # Skip me and already stored data
            if str(player['player']['player_id']) == str(cred['player_id']) or \
               player['player']['player_id'] in id_list:
                continue

            # Get location
            reqId += 1
            rq = createRequest(reqId, 'visitPlayer', 'OtherPlayerService',
                               [player['player']['player_id']])
            payload_player = forgeRequest(cred['json_id'], rq)
            data_player = request(cred['json_gateway'], payload_player, cred['sid'])
            data_player = json.loads(data_player.decode())[0]
            if data_player['requestClass'] == 'ExceptionService':
                fd = os.open('errors.txt', os.O_CREAT|os.O_APPEND|os.O_WRONLY)
                os.chmod(fd, stat.S_IRUSR|stat.S_IWUSR|stat.S_IRGRP|stat.S_IROTH)
                os.write(fd, ("visitPlayer error - " + player['player']['name'] + \
                              ' (' + player['player']['id'] + ') ' + '\n').encode())
                os.write(fd, json.dumps(data_player).encode())
                os.write(fd, b'\n')
                os.close(fd)
                continue

            data_player = data_player['responseData']
            if 'technologySection' in data_player:
                tech = data_player['technologySection']
            else:
                fd = os.open('errors.txt', os.O_CREAT|os.O_APPEND|os.O_WRONLY)
                os.chmod(fd, stat.S_IRUSR|stat.S_IWUSR|stat.S_IRGRP|stat.S_IROTH)
                os.write(fd, ('WARNING: player ' + player['player']['name'] + \
                              ' (' + player['player']['id'] + ') has no tech.\n').encode())
                os.close(fd)
                tech = 0
            data_player = data_player['other_player']
            if data_player['player_id'] != player['player']['player_id']:
                fd = os.open('errors.txt', os.O_CREAT|os.O_APPEND|os.O_WRONLY)
                os.chmod(fd, stat.S_IRUSR|stat.S_IWUSR|stat.S_IRGRP|stat.S_IROTH)
                os.write(fd, ('WARNING: player ' + player['player']['name'] + ' (' + \
                              data_player['name'] + ') has incoherent IDs: ' + \
                              player['player']['player_id'] + '/' + data_player['player_id']).encode())
                os.write(fd, b'\n')
                os.close(fd)

            if not 'r' in data_player['location']:
                data_player['location']['r'] = 0
            if not 'q' in data_player['location']:
                data_player['location']['q'] = 0

            if data_player['location']['r'] == me['r'] \
               and data_player['location']['q'] == me['q'] \
               and data_player['player_id'] != me['player_id']:
                ghosts[tech] += 1

            tmp = {
                'id': data_player['player_id'],
                'name': data_player['name'],
                'x': data_player['location']['r'],
                'y': data_player['location']['q']
            }
            # Get encounters score
            reqId += 1
            rq = createRequest(reqId, 'getRankingOverview', 'RankingService',
                               [player['player']['player_id']])
            payload_points = forgeRequest(cred['json_id'], rq)
            city_points = request(cred['json_gateway'], payload_points, cred['sid'])
            city_points = json.loads(city_points.decode())[0]
            if city_points['requestClass'] == 'ExceptionService':
                fd = os.open('errors.txt', os.O_CREAT|os.O_APPEND|os.O_WRONLY)
                os.chmod(fd, stat.S_IRUSR|stat.S_IWUSR|stat.S_IRGRP|stat.S_IROTH)
                os.write(fd, ('getRankingOverview error - ' + data_player['name']).encode())
                os.write(fd, b'\n')
                os.write(fd, json.dumps(city_points).encode())
                os.write(fd, b'\n')
                os.close()
                continue

            for elt in city_points['responseData']:
                if elt['category'] != 'encounters':
                    continue
                tmp['encounter'] = elt['score']

            if 'guild_info' in data_player:
                tmp['guild_id'] = data_player['guild_info']['id']
                tmp['guild_name'] = data_player['guild_info']['name']

            player_list.append(tmp)


        if i != len(data):
            print(f"{UP}[ {BAD}KO{RES} ]\n")
        else:
            print(f"\n{UP}[ {GOOD}OK{RES} ]\n{CLR}", end='')

        print("[....] remove inactive accounts")
        for i in id_list:
            if not i in new_id_list:
                p = [ p for p in player_list if p['id'] == i ][0]
                player_list.remove(p)
        print(f"\n\n{UP}[DONE]")
        print("[....] write new database")
        os.rename('players.json', 'old-db.json')
        fd = os.open('players.json', os.O_CREAT|os.O_WRONLY)
        os.chmod(fd, stat.S_IRUSR|stat.S_IWUSR|stat.S_IRGRP|stat.S_IROTH)
        buf = json.dumps(player_list).encode()
        os.write(fd, buf)
        os.close(fd)
        print(f"\n\n{UP}[DONE]")
        print('Found', sum(ghosts), 'ghost cities.')
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
