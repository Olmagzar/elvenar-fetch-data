from pprint import pprint
from connection import ElvenarConnection
from processData import processResp
import os
import stat
import json
import time
import argparse
import sys

UP = "\x1b[3A"
CLR = "\x1b[0K"
GOOD = "\033[38;5;34m"
BAD = "\033[38;5;1m"
RES = "\033[0m"

# TODO: check Exceptions, it might need to be reworked!
class GameCartographer():
    def __init__(self, username, passwd, country, world, prefix_path, guild_name, player_guild):
        self.__ghosts = [0 for i in range(20)]
        self.__err = []
        self.__reqId = 1
        self.__logged_in = False
        self.__country = country.lower()
        self.__world = world
        self.__game = ElvenarConnection(username, passwd, country, world)
        prefix_path = '{}/{}/{}'.format(prefix_path, country.lower(), world.lower())
        self.__db_file = '{}/players.json'.format(prefix_path)
        self.__guild_name = guild_name
        self.__player_guild = player_guild
        try:
            if not os.path.isdir(prefix_path):
                os.makedirs(prefix_path)
            print("[....] Login")
            self.__game.login()
            self.__logged_in = True
            print(f"\n\n{UP}[ {GOOD}OK{RES} ]")
            self.__refreshCity()
            self.__getCartographer()
        except:
            print(f"\n\n{UP}[{BAD}FAIL{RES}]")
            raise

    def __del__(self):
        if self.__logged_in == True:
            try:
                print("[....] Logout")
                self.__game.logout()
                print(f"\n\n{UP}[ {GOOD}OK{RES} ]")
            except:
                print(f"\n\n{UP}[{BAD}FAIL{RES}]")
                raise

    def __createRequest(self, requestMethod, requestClass, requestData):
        req = [ {
            'requestId': self.__reqId,
            'requestMethod': requestMethod,
            'requestClass': requestClass,
            'requestData': requestData,
            '__clazz__': 'ServerRequestVO'
        } ]
        self.__reqId += 1
        return req

    def __refreshCity(self):
        print("[....] Refresh city")
        rq = self.__createRequest('getData', 'StartupService', [])
        data = self.__game.request(rq)
        if data == None:
            print(f"\n\n{UP}[{BAD}FAIL{RES}]")
            raise Exception("Could not complete getData request")
        print(f"\n\n{UP}[ {GOOD}OK{RES} ]")
        for data in json.loads(data.decode()):
            if data['requestClass'] == 'ExceptionService':
                print(f"\n\n{UP}[{BAD}FAIL{RES}]")
                pprint(data)

    def __getCartographer(self):
        print("[....] Get cartographer details")
        rq = self.__createRequest('fetchInitialWorldMapData', 'WorldMapService', [])
        data = self.__game.request(rq)
        if data == None:
            print(f"\n\n{UP}[{BAD}FAIL{RES}]")
            raise Exception("Could not complete initialWorld request")
        for data in json.loads(data.decode()):
            if data['requestClass'] == 'ExceptionService':
                print(f"\n\n{UP}[{BAD}FAIL{RES}]")
                pprint(data)
                raise Exception("Could not complete initialWorld request")
            elif data['requestClass'] == 'WorldMapService' and \
                 data['requestMethod'] == 'fetchInitialWorldMapData':
                provinces = data['responseData']['player_world_map_area_vo']['provinces']
                self.__me = [ p for p in provinces
                            if (p['__class__'] == 'PlayerProvinceVO' and str(p['player_id']) == self.__game.player_id)
                     ][0]
                print(f"\n\n{UP}[ {GOOD}OK{RES} ]")
        if not hasattr(self, '_GameCartographer__me'):
            print(f"\n\n{UP}[{BAD}FAIL{RES}]")
            raise Exception("Could not retrieve cartographer details")

    def __getGuildID(self):
        guild_id = -1
        if self.__guild_name != None:
            rq = self.__createRequest('getRankingList', 'RankingService',
                                      ['guild',0,999999,self.__guild_name,'name'])
            data = self.__game.request(rq)
            if data == None:
                raise Exception("Could not access guild search")
            data = json.loads(data.decode())[0]
            if data['requestClass'] == 'ExceptionService' or \
               'rankings' not in data['responseData']:
                pprint(data)
                raise Exception("Could not retrieve guild search result")
            for g in data['responseData']['rankings']:
                if g['guild_info']['name'].lower() == self.__guild_name.lower():
                    guild_id = g['guild_info']['id']
                    break
            if guild_id == -1:
                raise Exception("Guild named '{}' not found".format(
                        self.__guild_name))
        elif self.__player_guild != None:
            rq = self.__createRequest('getRankingList', 'RankingService',
                                      ['player',0,999999,self.__player_guild,'name'])
            data = self.__game.request(rq)
            if data == None:
                raise Exception("Could not access player search")
            data = json.loads(data.decode())[0]
            if data['requestClass'] == 'ExceptionService' or \
               'rankings' not in data['responseData']:
                pprint(data)
                raise Exception("Could not retrieve player search result")
            for p in data['responseData']['rankings']:
                if p['player']['name'].lower() == self.__player_guild.lower() \
                   and 'guildInfo' in p:
                    guild_id = p['guildInfo']['id']
                    break
            if guild_id == -1:
                raise Exception(
                        "Guild named '{}' not found or not in a guild".format(
                        self.__player_guild))
        else:
            raise Exception("Could not retrieve guild id (unspecified data)")
        return guild_id

    def __getPlayerList(self):
        print("[....] Get list of players")
        if self.__guild_name == None and self.__player_guild == None:
            rq = self.__createRequest('accessRanking', 'RankingService',
                                      ['player',8,0])
            data = self.__game.request(rq)
            if data == None:
                print(f"\n\n{UP}[{BAD}FAIL{RES}]")
                raise Exception("Could not access player list")
            data = json.loads(data.decode())[0]
            if data['requestClass'] == 'ExceptionService':
                print(f"\n\n{UP}[{BAD}FAIL{RES}]")
                pprint(data)
                raise Exception("Could not retrieve player list")
            list_size = data['responseData']['length']
            max_size = 45000
            if list_size > max_size:
                parts = int(list_size/max_size)
                rq = self.__createRequest('accessRanking', 'RankingService',
                                          ['player',max_size,0])
            else:
                parts = 0
                rq = self.__createRequest('accessRanking', 'RankingService',
                                          ['player',list_size - 1,0])
            self.__players = []
            while (parts >= 0):
                data = self.__game.request(rq)
                if data == None:
                    print(f"\n\n{UP}[{BAD}FAIL{RES}]")
                    raise Exception("Could not access player list")
                data = json.loads(data.decode())[0]
                if data['requestClass'] == 'ExceptionService':
                    print(f"\n\n{UP}[{BAD}FAIL{RES}]")
                    pprint(data)
                    raise Exception("Could not retrieve player list")
                # Actually server returns "size"+1
                # Use extra one as pivot id to get the next part of the list and
                # remove the previous last so it doesn't appears twice.
                #  (there might be an error someday if rankings changes between
                #   two parts on the pivot id. That might result with
                #   'KeyError no "active_period" in ...')
                last_id = data['responseData']['rankings'][
                            len(data['responseData']['rankings']) - 1]['player']['player_id']
                if self.__players != []:
                    _ = self.__players.pop()
                self.__players += data['responseData']['rankings']
                parts -= 1
                # queue the remaining part
                if parts >= 0:
                    rq = self.__createRequest('accessRanking', 'RankingService',
                                              ['player',max_size,last_id])
            ranks = []
            for p in self.__players:
                ranks.append(p['rank'])
            for i in range(1, list_size + 1):
                if not i in ranks:
                    self.__err.append('missing rank {}'.format(i))
        else:
            guild_id = self.__getGuildID()
            rq = self.__createRequest('getGuild', 'GuildService', [guild_id])
            data = self.__game.request(rq)
            if data == None:
                print(f"\n\n{UP}[{BAD}FAIL{RES}]")
                raise Exception("Could not access player list")
            data = json.loads(data.decode())[0]
            if data['requestClass'] == 'ExceptionService':
                print(f"\n\n{UP}[{BAD}FAIL{RES}]")
                pprint(data)
                raise Exception("Could not retrieve player list")
            self.__players = data['responseData']['members']
        print(f"\n\n{UP}[ {GOOD}OK{RES} ]")
        for e in self.__err:
            print(e)

    def __loadLocalDB(self):
        if os.path.exists(self.__db_file):
            print('[....] Load local database')
            sz = os.path.getsize(self.__db_file)
            fd = os.open(self.__db_file, os.O_RDONLY)
            buf = os.read(fd, sz)
            os.close(fd)
            self.__player_list = json.loads(buf.decode())
            print(f"\n\n{UP}[ {GOOD}OK{RES} ]")
        else:
            self.__player_list = {}

    def __initMemory(self):
        print('[....] Initialize memory')
        self.__id_list = []
        self.__mark_new = 0
        for p in self.__players:
            if 'score' in p:
                p['points'] = p['score']
            elif not 'points' in p:
                p['points'] = 0
            player_id = str(p['player']['player_id'])
            if player_id in self.__id_list:
                self.__err.append('"{}" had a duplicate, one other player might be lost'.format(
                                    p['player']['name']))
                self.__players.remove(p)
                continue
            self.__id_list += [player_id]
            if player_id in self.__player_list:
                self.__player_list[player_id]['active'] = False
            else:
                self.__player_list[player_id] = { 'active': True, 'tournament': 0 }
                self.__mark_new += 1
            self.__player_list[player_id]['points'] = p['points']
        print(f"\n\n{UP}[ {GOOD}OK{RES} ]")
        for e in self.__err:
            print(e)

    def __markTournamentPlayers(self):
        print("[....] Mark tournament players active")
        # This part might need to use a loop as in __getPlayerList but it seems
        # unlikely that there would be one day enougth tournament players to
        # cause an error.
        rq = self.__createRequest('accessRanking', 'RankingService', ['tournament',999999,0])
        data = self.__game.request(rq)
        if data == None:
            print(f"\n\n{UP}[{BAD}FAIL{RES}]")
            raise Exception("Could not access tournament ranking list")
        data = json.loads(data.decode())[0]
        self.__mark_t = 0
        if data['requestClass'] == 'ExceptionService':
            print(f"\n\n{UP}[{BAD}FAIL{RES}]")
            pprint(data)
            raise Exception("Could not get tournament list")
        else:
            tplayers = data['responseData']['rankings']
            if self.__guild_name != None or self.__player_guild != None:
                guild_id = self.__getGuildID()
            for p in tplayers:
                player_id = str(p['player']['player_id'])
                try:
                    if player_id in self.__player_list and \
                        self.__player_list[player_id]['tournament'] != p['points']:
                        self.__player_list[player_id]['active'] = True
                        if self.__guild_name == None and self.__player_guild == None:
                            self.__mark_t += 1
                        elif 'guildInfo' in p and p['guildInfo']['id'] == guild_id:
                            self.__mark_t += 1
                        self.__player_list[player_id]['tournament'] = p['points']
                except KeyError:
                    self.__err.append(p)
                except:
                    raise
            print(f"\n\n{UP}[ {GOOD}OK{RES} ]")

        if time.gmtime().tm_wday == 0:
            for player_id in self.__player_list:
                self.__player_list[player_id]['tournament'] = 0

    def initializePlayerList(self):
        self.__getPlayerList()
        self.__loadLocalDB()
        self.__initMemory()
        self.__markTournamentPlayers()

    def visitPlayers(self):
        print('[....] Download players')
        print('0/' + str(len(self.__id_list)))
        i = 0
        request_list = []
        rqIds = {}
        for player_id in self.__id_list:
            i += 1
            print(f"\n\n{UP}" + str(i) + '/' + str(len(self.__id_list)) + f"{CLR}")

            # Get location
            rq = self.__createRequest('visitPlayer', 'OtherPlayerService',
                                      [player_id])
            rqIds[self.__reqId] = player_id
            request_list += rq
            rq = self.__createRequest('getRankingOverview', 'RankingService',
                                      [player_id])
            rqIds[self.__reqId] = player_id
            request_list += rq
            if len(request_list) >= 50 or i == len(self.__id_list):
                data = self.__game.request(request_list)
                if data == None:
                    print(f"\n\n{UP}[{BAD}FAIL{RES}]")
                    raise Exception("Could not complete visiting tour")
                data = json.loads(data.decode())

                for idx in range(len(data)):
                    processResp(data[idx], self.__me, rqIds, self.__player_list,
                                self.__ghosts, self.__err)
                request_list = []
                rqIds = {}

        if i != len(self.__id_list):
            print(f"{UP}[{BAD}FAIL{RES}]\n")
        else:
            print(f"\n{UP}[ {GOOD}OK{RES} ]\n{CLR}", end='')

    def __removePlayers(self):
        if os.path.exists(self.__db_file):
            print("[....] Remove deleted accounts")
            list_copy = self.__player_list.copy()
            for player_id in list_copy.keys():
                if not player_id in self.__id_list:
                    trash = self.__player_list.pop(player_id)
            print(f"\n\n{UP}[ {GOOD}OK{RES} ]")
            os.remove(self.__db_file)

    def __updateActivity(self):
        print("[....] Update active period")
        for player_id in self.__player_list:
            active = self.__player_list[player_id].pop('active')
            if active == True:
                self.__player_list[player_id]['active_period'] = 35
            else:
                try:
                    period = self.__player_list[player_id]['active_period']
                    self.__player_list[player_id]['active_period'] = max(period - 1, 0)
                except KeyError as e:
                    self.__err.append('KeyError: "{}" not found for "{}" ({})'.format(e,
                                        self.__player_list[player_id]['name']),
                                        player_id)
                except:
                    raise
        print(f"\n\n{UP}[ {GOOD}OK{RES} ]")

    def __writeLocalDB(self):
        print("[....] Write database")
        fd = os.open(self.__db_file, os.O_CREAT|os.O_WRONLY)
        buf = json.dumps(self.__player_list).encode()
        os.write(fd, buf)
        os.close(fd)
        os.chmod(self.__db_file, stat.S_IRUSR|stat.S_IWUSR|stat.S_IRGRP|stat.S_IROTH)
        ts = time.gmtime()
        ts = "{}{:02}{:02}_{:02}{:02}".format(ts.tm_year, ts.tm_mon, ts.tm_mday,
                                              ts.tm_hour, ts.tm_min)
        db_file = '{}-{}.json'.format(self.__db_file[:-len('.json')], ts)
        fd = os.open(db_file, os.O_CREAT|os.O_WRONLY)
        buf = json.dumps(self.__player_list).encode()
        os.write(fd, buf)
        os.close(fd)
        os.chmod(db_file, stat.S_IRUSR|stat.S_IWUSR|stat.S_IRGRP|stat.S_IROTH)
        print(f"\n\n{UP}[ {GOOD}OK{RES} ]")

    def finalizePlayerList(self):
        self.__removePlayers()
        self.__updateActivity()
        self.__writeLocalDB()

    def summarizeJourney(self):
        print("[....] Write report")
        prefix_path = './reports/{}'.format(self.__country)
        if not os.path.isdir(prefix_path):
            os.makedirs(prefix_path)
        ts = time.gmtime()
        ts = "{}{:02}{:02}_{:02}{:02}".format(ts.tm_year, ts.tm_mon, ts.tm_mday,
                                              ts.tm_hour, ts.tm_min)
        fn = '{}/{}_report-{}.txt'.format(prefix_path, self.__world, ts)
        fd = os.open(fn, os.O_CREAT|os.O_WRONLY)
        os.write(fd, 'Over {} cities:\n'.format(len(self.__player_list)).encode())
        os.write(fd, '    {} were put in storage,\n'.format(sum(self.__ghosts)).encode())
        os.write(fd, '    {} were new players,\n'.format(self.__mark_new).encode())
#        os.write(fd, '    {} changed their city,\n'.format(self.__mark_city).encode())
#        os.write(fd, '    {} changed had an active effect,\n'.format(self.__mark_effect).encode())
        os.write(fd, '    {} actively participated in tournament,\n'.format(self.__mark_t).encode())
        os.write(fd, json.dumps(self.__ghosts[1:]).encode())
        os.write(fd, b'\n')
        os.close(fd)
        os.chmod(fn, stat.S_IRUSR|stat.S_IWUSR|stat.S_IRGRP|stat.S_IROTH)
        print(f"\n\n{UP}[ {GOOD}OK{RES} ]")
        for e in self.__err:
            print(e)

def main(username, passwd, country, world, prefix_path, guild_name, player_guild):
    try:
        cartograph = GameCartographer(username, passwd, country, world,
                                      prefix_path, guild_name, player_guild)
        cartograph.initializePlayerList()
        cartograph.visitPlayers()
        cartograph.finalizePlayerList()
        cartograph.summarizeJourney()
    except KeyboardInterrupt:
        print('KeyboardInterrupt')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate json database from web requests.')
    parser.add_argument('username', type=str, help='Player login')
    parser.add_argument('passwd', type=str, help='Player password')
    parser.add_argument('country', type=str, help='Country server')
    parser.add_argument('world', type=str, help='World to fetch data from')
    parser.add_argument('--prefix-path', type=str, default='./elvenar-db/src',
                        help='Path to load and store database from ' + \
                             '(<prefix-path>/<country>/<world>/players.json)')
    parser.add_argument('--guild-name', type=str,
                        help='Fetch cities from the specified guild')
    parser.add_argument('--player-guild', type=str,
                        help='Fetch cities from the guild of the specified player')
    args = parser.parse_args(sys.argv[1:])
    username = vars(args)['username']
    passwd = vars(args)['passwd']
    country = vars(args)['country']
    world = vars(args)['world']
    prefix_path = vars(args)['prefix_path']
    guild_name = vars(args)['guild_name']
    player_guild = vars(args)['player_guild']
    main(username, passwd, country, world, prefix_path, guild_name, player_guild)
