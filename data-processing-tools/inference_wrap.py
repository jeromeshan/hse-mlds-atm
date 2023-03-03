import pandas as pd
from dist_area_inference import inference

FEATURES_PATH = "../../data/inference/inference_features.csv"
COLS = ['dist', 'area']

def _inference_processing(enriched_data)
	x = enriched_data.apply(lambda dfed: inference(dfed['lat'], dfed['lon']), axis=1)
	dist = x.apply(lambda y:y[0]).tolist()
	area = x.apply(lambda y:y[1]).tolist()
	df = pd.DataFrame([dist, area], columns=COLS)
	df.to_csv(FEATURES_PATH, index=False)
	return df

def inference_features(enriched_data):
	
	try:
		df = pd.read_csv(FEATURES_PATH)
	except:
		df = _inference_processing(enriched_data)
	
	enriched_data[COLS] = df[COLS]
	return enriched_data
