import json
from hashlib import md5

def analyseCity(player):
    city = player['city_map']['entities']
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
    return (effects != {})

def processResp(data, me, rqIds, player_list, ghosts, err):
    if data['requestClass'] == 'ExceptionService':
        err.append(data)
    elif data['requestClass'] == 'OtherPlayerService' and \
         data['requestMethod'] == 'visitPlayer':
        player = data['responseData']
        tech = player['technologySection']

        active_city = analyseCity(player)
        city = player['city_map']['entities']
        player = player['other_player']
        player_id = str(player['player_id'])
        city_hash = md5(json.dumps(city).encode()).hexdigest()
        if ('city_hash' in player_list[player_id] and \
            player_list[player_id]['city_hash'] != city_hash) \
           or active_city == True:
            player_list[player_id]['active'] = True

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

        player_list[player_id]['name'] = player['name']
        player_list[player_id]['x'] = player['location']['r']
        player_list[player_id]['y'] = player['location']['q']
        player_list[player_id]['encounter'] = 0
        player_list[player_id]['tech'] = tech
        player_list[player_id]['city_hash'] = city_hash

        if 'guild_info' in player:
            player_list[player_id]['guild_id'] = player['guild_info']['id']
            player_list[player_id]['guild_name'] = player['guild_info']['name']
        elif 'guild_id' in player_list[player_id]:
            trash = player_list[player_id].pop('guild_id')
            trash = player_list[player_id].pop('guild_name')
    elif data['requestClass'] == 'RankingService' and \
         data['requestMethod'] == 'getRankingOverview':
        player_id = str(rqIds[data['requestId']])
        score_hash = md5(json.dumps(data['responseData']).encode()).hexdigest()
        if 'score_hash' in player_list[player_id] and \
           player_list[player_id]['score_hash'] != score_hash and \
           player_list[player_id]['ghost'] == False:
            player_list[player_id]['active'] = True
        player_list[player_id]['score_hash'] = score_hash
        for elt in data['responseData']:
            if elt['category'] != 'encounters':
                continue
            player_list[player_id]['encounter'] = elt['score']
    else:
        err.append(data)
