import math
from functools import partial
import geopandas as gpd
import pyproj
from shapely.ops import nearest_points, transform
from shapely.geometry import Polygon, Point


def dist_to_nearest_neighbour(df, epsg = 3857):
    
    '''
    Считает минимальное расстояние до ближайшего соседнего банкомата
    
    df -- геофрейм с данными о банкоматах
    epsg -- желаемая проекция геофрейма (default:Pseudo-Mercator)
    '''
    
    df = df.copy().to_crs(epsg)
    for index, row in df.iterrows():
        point = row['geometry']
        multipoint = df.drop(index, axis=0)['geometry'].unary_union
        _, nearest_geom = nearest_points(point, multipoint)
        df.loc[index, 'nearest_neighbour_atm'] = nearest_geom.distance(point)
        
    return df


def geodesic_point_buffer(lon, lat, m):
    
    '''
    Чертит корректный буфер вокург точки с учетом проекции
    
    coords -- tuple с долготой и широтой точки
    m -- радиус буфера
    '''
    
    proj_wgs84 = pyproj.Proj('+proj=longlat +datum=WGS84') 
    
    aeqd_proj = '+proj=aeqd +lat_0={lat} +lon_0={lon} +x_0=0 +y_0=0'
    project = partial(
        pyproj.transform, 
        pyproj.Proj(aeqd_proj.format(lon=lon, lat=lat)),
        proj_wgs84)
    
    buf = Point(0, 0).buffer(m)
    
    return transform(project, buf)


def points_in_buffer(point_df, poly_df, name, m=250):

    '''
    Считает количество точек из points_df в каждом полигоне из poly_df

    point_df -- Геофрейм с объектами инфраструктуры
    poly_df -- Геофрейм с омновной информацией по банкоматам
    m -- Радиус для буффера
    '''

    # Считаем буффер
    poly_df['{}m_buffer'.format(m)] = poly_df['geometry'].buffer(m)
    # Меняем геометрию с точек на полигоны (буфферы)
    poly_df.set_geometry('{}m_buffer'.format(m), inplace=True)

    # Считаем количество точек из point_df в каждом полигоне из poly_df
    pts_in_poly = gpd.sjoin(point_df, poly_df, how='left')
    pts_in_poly['const'] = 1
    counter = pts_in_poly.groupby('index_right')['const'].sum()
    counter.name = '{}_in_{}m'.format(name, m)

    # Чистим фрейм от колонки буффера и возвращаем исходную геометрию
    poly_df.drop('{}m_buffer'.format(m), axis=1, inplace=True)
    poly_df.set_geometry('geometry', inplace=True)

    return counter


def find_epsg(lon, lat) :
    '''Находит корректный EPSG по долготе и широте'''
    
    zone = (math.floor((lon + 180) / 6) ) + 1 
    epsg_code = 32600
    epsg_code += int(zone)
    if (lat < 0):
        epsg_code += 100    
    return epsg_code