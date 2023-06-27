import glob
import pandas as pd
import geopandas as gpd
from itertools import product
from geo_functions import *
from inference_wrap import inference_features

import warnings

warnings.filterwarnings("ignore")

# Проверяем директорию с обрезанными дампами
if not any(glob.glob("../../data/interim/*.csv")):
    # Если в ней нет нужных CSV файлов, то исполняем cut_external_pbf.py
    exec(open("cut_external_pbf.py").read())

# Загружаем тренировочные и тестовые данные
train = pd.read_csv("../../data/raw/train.csv", index_col=0)
test = pd.read_csv("../../data/raw/test.csv", index_col=0)
# Склеиваем их в единый датасет
concat = pd.concat([train, test]).rename(columns={"long": "lon"}).reset_index(drop=True)

# Настраиваем геодатафрейм
geometry = gpd.points_from_xy(concat["lon"], concat["lat"])
data = gpd.GeoDataFrame(concat, geometry=geometry, crs="EPSG:4326")

# Заполняем пропущенные координаты обратным геокодингом
for index, row in data[data.lat.isna()].iterrows():
    idx = row["id"]
    address = row["address"]
    try:
        geocoder_data = fetch_coordinates(address)
        lon, lat = geocoder_data
        data.loc[data.id == idx, "lat"] = float(lat)
        data.loc[data.id == idx, "lon"] = float(lon)
    except:
        pass

# Удалим строки, где нам не удалось найти координаты
data.dropna(subset=["lon", "lat"], inplace=True)

# Добавим UTM зону, будем использовать ее для получения корректных значений в последующих вычислениях
data["utm"] = data.apply(lambda x: find_epsg(x.lon, x.lat), axis=1)

# Загружаем доп. данные с полигонами федеральных округов и регионов РФ
fed_dist = gpd.read_file(
    "../../data/external/federal_districts.csv", sep=";", crs="EPSG:4326"
).rename(columns={"name": "fed_dist"})
regions = gpd.read_file(
    "../../data/external/regions.csv", sep=";", crs="EPSG:4326"
).rename(columns={"name": "region"})

# Добавляем федеральный округ и регион к каждому наблюдению
data = data.sjoin(fed_dist[["geometry", "fed_dist"]], how="left", predicate="within")
data.drop("index_right", axis=1, inplace=True)
data = data.sjoin(regions[["geometry", "region"]], how="left", predicate="within")
data.drop("index_right", axis=1, inplace=True)

# Загружаем файлы с информацией об инфраструктурных объектах
files_path = glob.glob("../../data/interim/*.csv")
files = [pd.read_csv(f, index_col=0) for f in files_path]
concat_files = pd.concat(files).reset_index(drop=True)
geometry_files = gpd.points_from_xy(concat_files["lon"], concat_files["lat"])

# Настраиваем геодатафрейм
infrastructure = gpd.GeoDataFrame(
    concat_files, geometry=geometry_files, crs="EPSG:4326"
)

infrastructure["utm"] = infrastructure.apply(lambda x: find_epsg(x.lon, x.lat), axis=1)

# Вытаскиваем массив UTM зон встречающихся в наших данных
utm_zones = data["utm"].unique()
# Вытаскиваем массив типов инфраструктуры
infr_obj = infrastructure["type"].unique()
# Пары зона - объект
utm_obj = list(product(utm_zones, infr_obj))

# Разделяем датафреймы по UTM зоне и записываем в словарь с соответсвующем ключем
utm_data = {}
for utm in utm_zones:
    utm_data[utm] = data[data["utm"] == utm]

utm_infrastructure = {}
for utm, obj in utm_obj:
    mask = (infrastructure["utm"] == utm) & (infrastructure["type"] == obj)
    utm_infrastructure[(utm, obj)] = infrastructure[mask]

# Считаем расстояния до ближайшего объекта инфраструктуры
for utm, obj in utm_obj:
    # Имя будущей колонки с дистанцией
    dist_col_name = f"nearest_{obj}"
    # Корректируем проекцию для текущей итерации
    cur_data = utm_data[utm].to_crs(f"EPSG:{utm}")
    cur_obj = utm_infrastructure[(utm, obj)].to_crs(f"EPSG:{utm}")
    # Добавляем колонку с дистанцией до ближайшего объекта инфраструктуры
    dist_to_nearest = (
        cur_data.sjoin_nearest(cur_obj, how="left", distance_col="dist")[["id", "dist"]]
        .rename(columns={"dist": dist_col_name})
        .drop_duplicates(subset="id")
    )
    utm_data[utm] = pd.merge(utm_data[utm], dist_to_nearest, on="id")

# Считаем расстояние до ближайшего соседнего банкомата из первичного датасета
for utm in utm_zones:
    try:
        utm_data[utm] = dist_to_nearest_neighbour(
            utm_data[utm], epsg=f"EPSG:{utm}"
        ).to_crs("EPSG:4326")
    except:
        pass

# Считаем количество объектов в радиусе 500м
for utm, obj in utm_obj:
    # Корректируем проекцию для текущей итерации
    cur_data = utm_data[utm].to_crs(f"EPSG:{utm}")
    cur_obj = utm_infrastructure[(utm, obj)].to_crs(f"EPSG:{utm}")
    utm_data[utm] = utm_data[utm].join(points_in_buffer(cur_obj, cur_data, obj, 500))
    utm_data[utm].columns.str.contains

# Соеденяем обогащенные данные по зонам в единую таблицу
enriched_data = pd.concat(utm_data.values()).reset_index(drop=True)
# Заполняем пропуски в колонках 'объекты в радиусе' на ноль
mask = enriched_data.columns.str.contains("_in_")
enriched_data.loc[:, mask] = enriched_data.loc[:, mask].fillna(0)

# Добавляем признаки "area" и "dist" - вызов функции инференса:
enriched_data = inference_features(enriched_data)

# Сохраняем обработанные данные
enriched_data.to_csv("../../data/processed/enriched_data.csv", index=False)
