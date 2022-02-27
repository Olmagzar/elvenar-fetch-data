This is a python script to fetch data from the game to be able to analyse it.
The json file generated is parsable by the elvenar-world-map project as it was
the main goal.

usage: fetchData.py [-h] [--prefix-path PREFIX_PATH] username passwd
                                                     country world

Generate json database from web requests.

positional arguments:
  username                      Player login
  passwd                        Player password
  country                       Country server
  world                         World to fetch data from

optional arguments:
  -h, --help                    show this help message and exit
  --prefix-path PREFIX_PATH     Path to load and store database from
                                (<prefix-path>/<country>/<world>/players.json)

The script also creates a report file in a local 'reports/<country>' directory,
name <World>_report-<timestamp-utc>.txt
It contains some stats from the visited cities. For instance:

reports/fr/Felyndral_report-20211211_1904.txt contains:
Over 37511 cities:
    9620 were put in storage,
    106 were new players,
    4325 actively participated in tournament,
[3038, 877, 2261, 749, 473, 590, 365, 393, 216, 157, 114, 133, 81, 78, 68, 17, 9, 1, 0]

Notes:
This script was inspired by another github project the reading of which helped
to understand the web connection requests part.
(https://github.com/Saerwynn/Elvenar-Ancient-Wonders-Scraper)
