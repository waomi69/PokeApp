from django.shortcuts import render
from django.core.cache import cache
from django.core.paginator import Paginator 

import PokeServiceMain.forms as forms
import PokeServiceMain.casts as casts
import typing, re,  random, math
import main.models as models
import main.battle as battle


# Create your views here.
def PokemonsCatalog(request):
    

    LIMIT_OF_POKEMONS: int = 6
    if 'search' in request.GET:
        pat = rf".*{request.GET['search']}.*"
        pattern = re.compile(pat)
        pokemons_by_cached = [pokemon for pokemon in casts.GetPokemons() if pattern.match(pokemon)]
    else:
        pokemons_by_cached = cache.get('pokemons')

    if not pokemons_by_cached:
        pokemons_by_cached = casts.GetPokemons()
        cache.set('pokemons', pokemons_by_cached)

    catalog_paginator = Paginator(pokemons_by_cached, LIMIT_OF_POKEMONS)

    page = int(request.GET.get('page', 1))
    page_pokemons = catalog_paginator.get_page(page)


    # OFFSET_OF_LIMIT: int = (page - 1) * LIMIT_OF_POKEMONS
    if 'search' in request.GET:
        pokemons_data_by_cached = casts.GetPokemonsData(pokemons=page_pokemons.object_list)
    else:
        pokemons_data_by_cached = cache.get(f'pokemons_data{page}')
    if not pokemons_data_by_cached:
        pokemons_data_by_cached = casts.GetPokemonsData(pokemons=page_pokemons.object_list) # list of dicts
        cache.set(f'pokemons_data{page}', pokemons_data_by_cached, 3600)

    
    print(page_pokemons.object_list)

    data_2_page:dict = {
        'pokemons_data': pokemons_data_by_cached,
        'page_pokemons' : page_pokemons
        }
    return render(request, "main/catalog.html", data_2_page)



def PokemonDetail(request, pokemon: str = None):
    return render(request, 'main/detailed.html', {'pokemon_data': casts.GetPokemonData(pokemon)})


def PokemonBattle(request, pokemon: str = None):
    user_pokemon_data = casts.GetPokemonData(pokemon)
    
    #check if it start
    if request.method != 'POST':
        battle_form = forms.BattleForm()
        battle_round: int = 0

        enemy_pokemon_data = casts.GetRandomPokemonData(exception_pokemons=[pokemon])

        user_pokemon_stats: typing.Dict[str,str] = battle.InitPokemonStats(user_pokemon_data)
        enemy_pokemon_stats: typing.Dict[str,str] = battle.InitPokemonStats(enemy_pokemon_data)
        
        logs: typing.List[str] = ['[LOG] Starting battle.... Lets fight!']
        
        battle.SyncSession(request, 
                           ['user_pokemon_stats', 'enemy_pokemon_stats', 'battle_round', 'logs', 'hitted_object'],
                           [user_pokemon_stats, enemy_pokemon_stats,  battle_round, logs, {'is_user': 'false', 'is_enemy': 'false'}])

    else:

        battle_form = forms.BattleForm(request.POST)
        if battle_form.is_valid():
            battle_round = request.session.get('battle_round') + 1
            logs_of_battle: typing.List[str] = [f'[LOG] Round #{battle_round}']

            user_roll = battle_form.cleaned_data['user_roll']
            logs_of_battle.append(f' | User roll: {user_roll}')

            user_pokemon_stats: typing.Dict[str,str] = request.session.get('user_pokemon_stats')
            enemy_pokemon_stats: typing.Dict[str,str] = request.session.get('enemy_pokemon_stats')

            battle.AttackPart(request, user_roll, logs_of_battle, user_pokemon_stats, enemy_pokemon_stats)

            if user_pokemon_stats['hp'] <= 0 or enemy_pokemon_stats['hp'] <= 0:
                pokemon_winner = user_pokemon_stats if user_pokemon_stats['hp'] > 0 else enemy_pokemon_stats

                battle.SaveBattleResult(battle_round, user_pokemon_stats['name'], enemy_pokemon_stats['name'], pokemon_winner['name'])

                logs: typing.List[str] = request.session.get('logs')
                logs.append("".join(logs_of_battle))
                logs.append(f"[LOG] Battle end! Congratulation {pokemon_winner['name'].upper()}!")
                request.session['logs'] = logs


                data_2_render: dict = {
                    'winner': pokemon_winner,
                    'battle_round': battle_round,
                    'battle_logs': request.session.get('logs')
                }
                return render(request, 'main/battle_end.html', data_2_render)

            logs: typing.List[str] = request.session.get('logs')
            logs.append("".join(logs_of_battle))


            battle.SyncSession(request,
                               ['user_pokemon_stats', 'enemy_pokemon_stats', 'battle_round', 'logs'], 
                               [ user_pokemon_stats,  enemy_pokemon_stats, battle_round, logs])


    print( request.session.get('hitted_object'))
    data_2_render: dict = {
        'user_pokemon_stats': request.session.get('user_pokemon_stats'),
        'enemy_pokemon_stats': request.session.get('enemy_pokemon_stats'),
        'battle_form': battle_form,
        'battle_round': battle_round,
        'battle_logs': request.session.get('logs'),
        'hitted_object': request.session.get('hitted_object')
    }
    return render(request, 'main/battle.html', data_2_render)


