import osmium 
import pandas as pd
import geopandas as gpd
import glob
import os


# Список OSM тэгов
tag_list = [
    {'station': ['subway']},
    {'highway': ['stop_position']},
    {'government': ['administrative']},
    {'amenity': ['college', 'university']},
    {'amenity': ['school']},
    {'amenity': ['kindergarten', 'childcare']},
    {'amenity': ['bank']},
    {'amenity': ['atm']},
    {'amenity': ['hospital']},
    {'office': ['company']},
    {'amenity': ['cafe', 'fast_food', 'bar', 'pub', 'canteen']},
    {'government': ['public_service']},
    {'aeroway': ['aerodrome']},
    {'railway': ['station']}
]

# Human-readable имена тегов 
tag_names = [
    'subway',
    'bus_stop',
    'gov_building',
    'college',
    'school',
    'kgarden',
    'bank',
    'atm',
    'hospital',
    'office',
    'food',
    'MFC',
    'airport',
    'railway'
]

tags = dict(zip(tag_names, tag_list))


def get_osmium_script(initial_file, output_file, tags):
    
    '''Функция возвращает скрипт osmium-tool обрезающий PBF дамп по листу тегов
    
    initial_file -- путь к целому pbf файлу
    output_file --  название/путь файла обрезанного pbf файла 
    tags -- словарь с osm тегами
    '''
    
    osmium_string = f'osmium tags-filter {initial_file} '
    for name, tag in tags.items():
        for key, value_list in tag.items():
            if len(value_list) == 1:
                osmium_string += r'n/{}={} '.format(key, value_list[0])
            else:
                for value in value_list:
                    osmium_string += r'n/{}={} '.format(key, value)
    osmium_string += f'-o {output_file}'
    
    return osmium_string


# Собираем лист с путями к цельным дампам
input_files = glob.glob('../../data/external/*.osm.pbf')

# Проверяем директорию с обрезанными дампами
if not any(glob.glob('../../data/interim/*.osm.pbf')):
    # Если она пуста, то исполняем load_external_pbf.py
    exec(open('load_external_pbf.py').read())

    for file in input_files:
        # Собираем скрипт для каждого файла из списка
        file_name = file.replace('../../data/external/', '')
        # Исполняем их и сохраняем обрезанные файлы в отдельную дерикторию с промежуточными данными
        os.system(get_osmium_script(file, '../../data/interim/cutted-{}'.format(file_name), tags))
        print(file + ' was cutted successfully')
        # Удаляем цельный PBF дамп
        #os.remove(file)
    

# Создаем SimpleHandler для парсинга нужной информации из обрезанных pbf
class OSMHandler(osmium.SimpleHandler):
    def __init__(self):
        super(OSMHandler, self).__init__()
        self.infrastructure = []

    def node(self, o):
        for name, tag in tags.items():
            for key, value_list in tag.items():
                if len(value_list) == 1:
                    if o.tags.get(key) == value_list[0]:
                        self.infrastructure.append(
                            [name, o.location.lon, o.location.lat]
                        )
                else:
                    for value in value_list:
                        if o.tags.get(key) == value:
                            self.infrastructure.append(
                                [name, o.location.lon, o.location.lat]
                            )
    
# Названия обрезанных pbf файлов
cutted_files = glob.glob('../../data/interim/*.osm.pbf')

# Инициализируем словарь геофреймов
districts_gdfs = {}

# Итерируем над обрезанными pbf файлами
for district in cutted_files:
    # Парсим из них инфо по тегам
    handler = OSMHandler()
    handler.apply_file(district, locations=True)
    # Записываем в геофрейм и крепим к словарю
    df = pd.DataFrame(handler.infrastructure, columns=['type', 'lon', 'lat'])
    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df['lon'], df['lat']))
    gdf.crs = 'EPSG:4326'
    districts_gdfs[district.replace('../../data/interim/', '').replace('-latest.osm.pbf', '')] = gdf  
    
# Сохраняем все в csv
for name, gdf in districts_gdfs.items():
    gdf.to_csv('../../data/interim/' + name + '.csv')
    
print('All PBF dumps were cutted successfully')