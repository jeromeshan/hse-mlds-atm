import requests
import glob

files = [
    "central-fed-district-latest.osm.pbf",
    "crimean-fed-district-latest.osm.pbf",
    "far-eastern-fed-district-latest.osm.pbf",
    "north-caucasus-fed-district-latest.osm.pbf",
    "northwestern-fed-district-latest.osm.pbf",
    "siberian-fed-district-latest.osm.pbf",
    "south-fed-district-latest.osm.pbf",
    "ural-fed-district-latest.osm.pbf",
    "volga-fed-district-latest.osm.pbf",
    "kaliningrad-latest.osm.pbf",
]

if not any(glob.glob("../../data/external/*.osm.pbf")):
    for file in files:
        # Формируем URL на скачивание PBF дампа федерального округа России
        URL = "https://download.geofabrik.de/russia/" + file

        # Скачиваем данные по сформированному URL
        responce = requests.get(URL)

        # Записываем данные в PBF файл
        open("../../data/external/" + file, "wb").write(responce.content)

    print("All PBF dumps were downloaded successfully")
