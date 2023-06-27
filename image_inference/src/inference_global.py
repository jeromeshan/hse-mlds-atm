import glob
import math
import numpy as np
import pandas as pd
from itertools import product
from functools import partial

import geopandas as gpd
from geopy.distance import geodesic
from shapely.ops import nearest_points, transform
from shapely.geometry import Polygon, Point
import pyproj

import warnings
warnings.filterwarnings('ignore')

import pickle

from catboost import CatBoostRegressor
ATM_GROUPS = ['32.0', '496.5', '1022.0', '1942.0', '3185.5', '5478.0', '8083.0']

MAX_DISTANCE_KM = 200 / 1000
FILTER_DIST = 0.01

DF_AREA = pd.read_csv("data/inference/inference_area.csv")
DF_OBJS = pd.read_csv("data/inference/inference_objects.csv")
CAT = pickle.load(open('cat.pkl', 'rb'))

ALL_COLS = set("atm_group,lat,lon,fed_dist,region,nearest_bank,nearest_railway,nearest_food,nearest_hospital,nearest_atm,nearest_college,nearest_office,nearest_school,nearest_airport,nearest_gov_building,nearest_kgarden,nearest_MFC,nearest_subway,nearest_neighbour_atm,bank_in_500m,railway_in_500m,food_in_500m,hospital_in_500m,atm_in_500m,college_in_500m,office_in_500m,school_in_500m,airport_in_500m,gov_building_in_500m,kgarden_in_500m,MFC_in_500m,subway_in_500m,dist,area".split(','))

def dist_to_nearest_neighbour(df, epsg=3857):

    df = df.copy().to_crs(epsg)
    for index, row in df.iterrows():
        point = row['geometry']
        multipoint = df.drop(index, axis=0)['geometry'].unary_union
        _, nearest_geom = nearest_points(point, multipoint)
        df.loc[index, 'nearest_neighbour_atm'] = nearest_geom.distance(point)

    return df


def geodesic_point_buffer(lon, lat, m):

    proj_wgs84 = pyproj.Proj('+proj=longlat +datum=WGS84')

    aeqd_proj = '+proj=aeqd +lat_0={lat} +lon_0={lon} +x_0=0 +y_0=0'
    project = partial(
        pyproj.transform,
        pyproj.Proj(aeqd_proj.format(lon=lon, lat=lat)),
        proj_wgs84)

    buf = Point(0, 0).buffer(m)

    return transform(project, buf)


def points_in_buffer(point_df, poly_df, name, m=250):

    poly_df['{}m_buffer'.format(m)] = poly_df['geometry'].buffer(m)
    poly_df.set_geometry('{}m_buffer'.format(m), inplace=True)

    pts_in_poly = gpd.sjoin(point_df, poly_df, how='left')
    pts_in_poly['const'] = 1
    counter = pts_in_poly.groupby('index_right')['const'].sum()
    counter.name = '{}_in_{}m'.format(name, m)

    poly_df.drop('{}m_buffer'.format(m), axis=1, inplace=True)
    poly_df.set_geometry('geometry', inplace=True)

    return counter


def find_epsg(lon, lat):

    zone = (math.floor((lon + 180) / 6)) + 1
    epsg_code = 32600
    epsg_code += int(zone)
    if (lat < 0):
        epsg_code += 100
    return epsg_code


def test_df(group, lat, lon):
    return pd.DataFrame.from_dict({
        'id': [1],
        'atm_group': [group],
        'lat': [lat],
        'lon': [lon]
    })


def value_checker(x, y):
    return abs(x - y) <= FILTER_DIST


def dist(row, pt1):
    return geodesic(pt1, (row['lat'], row['lon'])).km


def transform(df_objs, df_area, atm):
    df_1 = {
        'df_objs': df_objs.copy(),
        'df_area': df_area.copy()
    }

    for df_k in df_1:
        for i, k in enumerate(('lat', 'lon')):
            df = df_1[df_k]
            df = df_1[df_k] = df[df[k].apply(value_checker, args=(atm[i],))]
        if len(df):
            df['dist'] = df.apply(dist, args=(atm,), axis=1)

    return df_1


def result_fn(df, fn):
    return sum(df[df['dist'] <= MAX_DISTANCE_KM].apply(fn, axis=1)) if len(df) else 0


def result_cnt(df):
    return len(df[df['dist'] <= MAX_DISTANCE_KM]) if len(df) else 0


def inference(lat, lon):
    atm = (lat, lon)
    dfs = transform(DF_OBJS, DF_AREA, atm)
    count_objs, sum_area = result_cnt(dfs['df_objs']), result_fn(dfs['df_area'], lambda x: x['area_residential'])
    return count_objs, sum_area


def inference_deploy(row):
    return inference(row['lat'], row['lon'])


def united(df_original):
    concat = df_original.copy()
    geometry = gpd.points_from_xy(concat['lon'], concat['lat'])
    data = gpd.GeoDataFrame(concat, geometry=geometry, crs='EPSG:4326')
    data['utm'] = data.apply(lambda x: find_epsg(x.lon, x.lat), axis=1)
    fed_dist = gpd.read_file('data/external/federal_districts.csv',
                             sep=';', crs='EPSG:4326').rename(columns={'name': 'fed_dist'})
    regions = gpd.read_file('data/external/regions.csv',
                            sep=';', crs='EPSG:4326').rename(columns={'name': 'region'})
    data = data.sjoin(fed_dist[['geometry', 'fed_dist']], how='left', predicate='within')
    data.drop('index_right', axis=1, inplace=True)
    data = data.sjoin(regions[['geometry', 'region']], how='left', predicate='within')
    data.drop('index_right', axis=1, inplace=True)
    files_path = glob.glob('data/interim/*.csv')
    files = [pd.read_csv(f, index_col=0) for f in files_path]
    concat_files = pd.concat(files).reset_index(drop=True)
    geometry_files = gpd.points_from_xy(concat_files['lon'], concat_files['lat'])
    infrastructure = gpd.GeoDataFrame(
        concat_files, geometry=geometry_files, crs='EPSG:4326'
    )

    infrastructure['utm'] = infrastructure.apply(lambda x: find_epsg(x.lon, x.lat), axis=1)
    utm_zones = data['utm'].unique()
    infr_obj = infrastructure['type'].unique()
    utm_obj = list(product(utm_zones, infr_obj))
    utm_data = {}
    for utm in utm_zones:
        utm_data[utm] = data[data['utm'] == utm]

    utm_infrastructure = {}
    for utm, obj in utm_obj:
        mask = (infrastructure['utm'] == utm) & (infrastructure['type'] == obj)
        utm_infrastructure[(utm, obj)] = infrastructure[mask]

    for utm, obj in utm_obj:
        dist_col_name = f'nearest_{obj}'
        cur_data = utm_data[utm].to_crs(f'EPSG:{utm}')
        cur_obj = utm_infrastructure[(utm, obj)].to_crs(f'EPSG:{utm}')
        dist_to_nearest = (
            cur_data.sjoin_nearest(cur_obj, how='left', distance_col='dist')[['id', 'dist']]
            .rename(columns={'dist': dist_col_name})
            .drop_duplicates(subset='id')
        )
        utm_data[utm] = pd.merge(utm_data[utm], dist_to_nearest, on='id')

    for utm in utm_zones:
        try:
            utm_data[utm] = dist_to_nearest_neighbour(
                utm_data[utm], epsg=f'EPSG:{utm}'
            ).to_crs('EPSG:4326')
        except:
            pass

    for utm, obj in utm_obj:
        cur_data = utm_data[utm].to_crs(f'EPSG:{utm}')
        cur_obj = utm_infrastructure[(utm, obj)].to_crs(f'EPSG:{utm}')
        utm_data[utm] = utm_data[utm].join(points_in_buffer(cur_obj, cur_data, obj, 500))
        utm_data[utm].columns.str.contains

    enriched_data = pd.concat(utm_data.values()).reset_index(drop=True)
    mask = enriched_data.columns.str.contains('_in_')
    enriched_data.loc[:, mask] = enriched_data.loc[:, mask].fillna(0)
    enriched_data['distarea'] = enriched_data.apply(inference_deploy, axis=1)
    enriched_data['dist'], enriched_data['area'] = enriched_data['distarea'].apply(lambda x: x[0]), enriched_data[
        'distarea'].apply(lambda x: x[1])
    enriched_data = enriched_data.drop(columns=['distarea', 'geometry', 'utm', 'id'])
    enriched_data['atm_group'] = enriched_data['atm_group'].astype('str')
    cols = ALL_COLS - set(enriched_data.columns)
    for col in cols:
        enriched_data[col] = np.nan
    return enriched_data

def overall(atm, lat, lon):
    return CAT.predict(united(test_df(atm, lat, lon)))[0]
