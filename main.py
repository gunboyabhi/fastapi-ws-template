import os
import httpx  # Use httpx for async HTTP requests
from fastapi import FastAPI
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import requests
import base64
import json
import uuid

load_dotenv()

app = FastAPI()


ACCESS_KEY = os.environ.get("ACCESS_KEY")
DB_KEY = os.environ.get("DB_KEY")
origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_API_URL = "https://api.langflow.astra.datastax.com"
LANGFLOW_ID = os.environ.get("LANGFLOW_ID")
ENDPOINT = "social_stats"
APPLICATION_TOKEN = os.environ.get("APP_TOKEN")


async def run_flow_via_http(message: str):
    try:
        api_url = f"{BASE_API_URL}/lf/{LANGFLOW_ID}/api/v1/run/{ENDPOINT}"

        prompt = """
            You are an expert in analyzing media posts and providing detailed and accurate information. 
            Your primary role is to utilize the provided tools to efficiently look up posts likes, comments, shares, engagement rate.
            Always aim to deliver clear, concise, and helpful responses, ensuring the user's needs are fully met. \n
            Response Format: Markdown
        """
        payload = {
            "input_value": f"{prompt} \n {message}",
            "output_type": "chat",
            "input_type": "chat",
        }

        headers = {
            "Authorization": f"Bearer {APPLICATION_TOKEN}",
            "Content-Type": "application/json"
        }

        # Use httpx for async HTTP requests
        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, json=payload, headers=headers)

        if response.status_code != 200:
            return {"error": f"Error: {response.status_code} - {response.text}"}, 500

        response_data = response.json()
        message = (
            response_data
            .get("outputs")[0]
            .get("outputs")[0]
            .get("results")
            .get("message")
            .get("text")
        )
        return {"ai_response": message}, 200

    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}


def get_lat_lon(city, state, api_key):
    url = f"https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": f"{city}, {state}", "key": api_key}
    response = requests.get(url, params=params).json()
    if response['status'] == 'OK':
        location = response['results'][0]['geometry']['location']
        return {"lat": location['lat'], "lon": location['lng']}
    return {"error": "Invalid location"}



def get_data(request):

    url = "https://json.freeastrologyapi.com/planets"

    payload = json.dumps({
    "name": request.name,
    "year": request.year,
    "month": request.month,
    "date": request.date,
    "hours": request.hours,
    "minutes": request.minutes,
    "seconds": request.seconds,
    "latitude": 90,
    "longitude": 180,
    "timezone": 5.5,
    "settings": {
        "observation_point": "topocentric",
        "ayanamsha": "lahiri"
    }
    })

    headers = {
    'Content-Type': 'application/json',
    'x-api-key': ACCESS_KEY
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    if response:
        json_res = json.loads(response.text)
        print(json_res)
        return json_res


def insert_data_into_astra_db(data):
    from astrapy import DataAPIClient

    # Initialize the client
    client = DataAPIClient(DB_KEY)
    db = client.get_database_by_api_endpoint(
    "https://299ee1d3-7813-4d96-8ea6-9684f8b9b124-us-east-2.apps.astra.datastax.com"
    )

    keyspace = "default_keyspace" 
    collection_name = "stored_responses"
    collection = db.get_collection(collection_name)
    collection.insert_one(data)
    print("Data inserted successfully.")

from pydantic import BaseModel

class chatRequest(BaseModel):
    name: str
    day: int
    month: int
    date: int
    year: int
    hours: int
    minutes: int
    seconds: int
    gender: str
    state: str
    city: str

@app.post("/process")
def process_message(request: chatRequest):
    # get token
    data = get_data(request)
    insert_data_into_astra_db(data=data)
    return {"message": "successfully submitted", 'status': 200}
