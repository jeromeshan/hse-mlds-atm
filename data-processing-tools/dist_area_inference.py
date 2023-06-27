import pandas as pd
from geopy.distance import geodesic

MAX_DISTANCE_KM = 200 / 1000
FILTER_DIST = 0.01

DF_AREA = pd.read_csv("../../data/inference/inference_area.csv")
DF_OBJS = pd.read_csv("../../data/inference/inference_objects.csv")


def value_checker(x, y):
    return abs(x - y) <= FILTER_DIST


def dist(row, pt1):
    return geodesic(pt1, (row["lat"], row["lon"])).km


def transform(df_objs, df_area, atm):

    df_1 = {"df_objs": df_objs.copy(), "df_area": df_area.copy()}

    for df_k in df_1:
        for i, k in enumerate(("lat", "lon")):
            df = df_1[df_k]
            df = df_1[df_k] = df[df[k].apply(value_checker, args=(atm[i],))]
        if len(df):
            df["dist"] = df.apply(dist, args=(atm,), axis=1)

    return df_1


def result_fn(df, fn):
    return sum(df[df["dist"] <= MAX_DISTANCE_KM].apply(fn, axis=1)) if len(df) else 0


def result_cnt(df):
    return len(df[df["dist"] <= MAX_DISTANCE_KM]) if len(df) else 0


def inference(lat, lon):
    atm = (lat, lon)
    dfs = transform(DF_OBJS, DF_AREA, atm)
    count_objs, sum_area = (
        result_cnt(dfs["df_objs"]),
        result_fn(dfs["df_area"], lambda x: x["area_residential"]),
    )
    return count_objs, sum_area


if __name__ == "__main__":
    print("Input latitude and longitude")
    lat, lon = [float(i) for i in input().replace(",", "").split()]
    print("Count & Area result")
    print(inference(lat, lon))
