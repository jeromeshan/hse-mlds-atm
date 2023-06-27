import uvicorn
from pydantic import BaseModel
from enum import Enum
from fastapi import FastAPI
from fastapi.responses import FileResponse
app = FastAPI()

from inference_global import overall

class Atm(str, Enum):
	atm1 = '32.0'
	atm2 = '496.5'
	atm3 = '1022.0'
	atm4 = '1942.0'
	atm5 = '3185.5'
	atm6 = '5478.0'
	atm7 = '8083.0'

class Input(BaseModel):
	lat: float
	lon: float
	atm: Atm

class Output(BaseModel):
	ranking: float

@app.get("/")
async def root():
	return FileResponse('index.html')

@app.post("/inference")
async def inference_fastapi(input: Input) -> Output:
	return Output(ranking=overall(float(input.atm), input.lat, input.lon))


if __name__ == '__main__':
	uvicorn.run(app, host="0.0.0.0", port=8000)
