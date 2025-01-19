import os
import httpx  # Use httpx for async HTTP requests
from fastapi import FastAPI, Request
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import requests
import base64
import json
import uuid
from starlette.middleware.sessions import SessionMiddleware
from astrapy import DataAPIClient
from pydantic import BaseModel
from geopy.geocoders import Nominatim

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

# Add Session Middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SECRET_KEY"), 
)
BASE_API_URL = "https://api.langflow.astra.datastax.com"
LANGFLOW_ID = os.environ.get("LANGFLOW_ID")
ENDPOINT = "social_stats"
APPLICATION_TOKEN = os.environ.get("APP_TOKEN")



@app.post("/chat")
def run_flow_via_http(message: str):
    try:
        
        api_url = f"{BASE_API_URL}/lf/{LANGFLOW_ID}/api/v1/run/{ENDPOINT}"

        payload = {
            "input_value": f"{message}",
            "output_type": "chat",
            "input_type": "chat",
        }

        headers = {
            "Authorization": f"Bearer {APPLICATION_TOKEN}",
            "Content-Type": "application/json"
        }

        # Use httpx for async HTTP requests
        response = requests.post(api_url, json=payload, headers=headers)

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

    state = request.state
    city = request.city
    geolocator = Nominatim(user_agent="soulBuddy")
    location = geolocator.geocode(city)

    payload = json.dumps({
        "name": request.name,
        "year": request.year,
        "month": request.month,
        "date": request.date,
        "hours": request.hours,
        "minutes": request.minutes,
        "seconds": request.seconds,
        "latitude": location.latitude,
        "longitude": location.longitude,
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
        json_res["name"] = request.name
        json_res["year"] = request.year
        json_res["month"] = request.month
        json_res["date"] = request.date
        json_res["hours"] = request.hours
        json_res["minutes"] = request.minutes
        json_res["seconds"] = request.seconds
        return json_res


def insert_data_into_astra_db(data):

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


def format_response_from_groq(prompt, msg):
    from groq import Groq

    client = Groq(
        api_key= os.environ.get("GROQ_API_KEY"),
    )

    # prompt = """
    #     You are a highly knowledgeable and intuitive astrology guide. Your role is to interpret detailed astrological data and provide meaningful, personalized insights in a natural and engaging format. Use the following structured data to generate user-friendly spiritual guidance, including zodiac-specific insights, recommendations, and actionable advice.

    #     ### User Input Details:
    #     - *Name*: {User Name}
    #     - *Date of Birth*: {DD/MM/YYYY}
    #     - *Time of Birth*: {HH:MM AM/PM}
    #     - *Location of Birth*: {City, Country}

    #     ### Planetary Details (API Response):
    #     {Insert API response data here, including planets, positions, zodiac signs, retrograde status, and ayanamsha.}

    #     ### Instructions:
    #     1. *Zodiac-Specific Insights*:
    #     - Explain the influence of each planet in its respective zodiac sign and house.
    #     - Mention the significance of retrograde planets, if any.

    #     2. *Personalized Recommendations*:
    #     - Suggest gemstones, rituals, or spiritual practices to enhance strengths or mitigate challenges.
    #     - Provide actionable tips tailored to the user’s astrological profile.

    #     3. *Spiritual Guidance*:
    #     - Offer meditation or workout suggestions based on planetary alignments.
    #     - Include sleep-related content, like affirmations or mindfulness techniques.

    #     4. *Practical Advice*:
    #     - Highlight "Do’s and Don’ts" for the user to follow based on the chart.

    #     5. *Output Structure*:
    #     Provide insights in a clear, readable format. For example:



    #     6. *Fallback Instructions*:
    #     If some data is missing, use general astrological principles to fill gaps and provide meaningful insights.

    #     Generate the output in a clear, engaging tone that resonates with users seeking spiritual guidance.
    # """

    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": f"{prompt} \n {msg}",
            }
        ],
        model="llama-3.1-8b-Instant",
    )
    response = chat_completion.choices[0].message.content
    return response

def get_zodiac_sign(day, month):
    if (month == 3 and day >= 21) or (month == 4 and day <= 19):
        return "Aries"
    elif (month == 4 and day >= 20) or (month == 5 and day <= 20):
        return "Taurus"
    elif (month == 5 and day >= 21) or (month == 6 and day <= 20):
        return "Gemini"
    elif (month == 6 and day >= 21) or (month == 7 and day <= 22):
        return "Cancer"
    elif (month == 7 and day >= 23) or (month == 8 and day <= 22):
        return "Leo"
    elif (month == 8 and day >= 23) or (month == 9 and day <= 22):
        return "Virgo"
    elif (month == 9 and day >= 23) or (month == 10 and day <= 22):
        return "Libra"
    elif (month == 10 and day >= 23) or (month == 11 and day <= 21):
        return "Scorpio"
    elif (month == 11 and day >= 22) or (month == 12 and day <= 21):
        return "Sagittarius"
    elif (month == 12 and day >= 22) or (month == 1 and day <= 19):
        return "Capricorn"
    elif (month == 1 and day >= 20) or (month == 2 and day <= 18):
        return "Aquarius"
    elif (month == 2 and day >= 19) or (month == 3 and day <= 20):
        return "Pisces"
    else:
        return "Invalid Date"

def get_zodiac_data_today(sign):
    url = "https://horoscope-app-api.vercel.app/api/v1/get-horoscope/daily"
    params = {
        "sign": f"{sign}", 
        "day": "TODAY"
    }

    headers = {
        "accept": "application/json"
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        horoscope_data = response.json()
        print("Horoscope Data:", horoscope_data)
        prompt = """Convert the given text into Markdown format and provide a detailed 
        explanation of its content in a comprehensive and elaborative manner, without 
        adding any introductory or concluding remarks."""
        formatted_response = format_response_from_groq(prompt=prompt, msg=horoscope_data)
        return formatted_response
    else:
        print("Error:", response.status_code, response.text)
        return {}


def get_zodiac_data_weekly(sign):
    url = "https://horoscope-app-api.vercel.app/api/v1/get-horoscope/monthly"
    params = {
        "sign": f"{sign}"
    }

    headers = {
        "accept": "application/json"
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        horoscope_data = response.json()
        print("Horoscope Data:", horoscope_data)
        prompt = """Convert the given text into Markdown format and provide a detailed 
        explanation of its content in a comprehensive and elaborative manner, without 
        adding any introductory or concluding remarks."""
        formatted_response = format_response_from_groq(prompt=prompt, msg=horoscope_data)
        return formatted_response
    else:
        print("Error:", response.status_code, response.text)
        return {}


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


@app.get('/daily')
def process_daily_horoscope(request: Request):
    zodiac_sign = request.session.get("zodiac_sign", 'Aries')
    return get_zodiac_data_today(zodiac_sign)

@app.get('/monthly')
def process_daily_horoscope(request: Request):
    zodiac_sign = request.session.get("zodiac_sign", 'Aries')
    return get_zodiac_data_weekly(zodiac_sign)



@app.post("/process")
def process_message(request: chatRequest, req: Request):
    # get token
    data = get_data(request)
    zodiac_sign = get_zodiac_sign(day=request.day, month=request.month)
    if zodiac_sign:
        req.session["zodiac_sign"] = zodiac_sign
    daily_data = get_zodiac_data_today(sign=zodiac_sign)
    weekly_data = get_zodiac_data_weekly(sign=zodiac_sign)
    data['daily_horoscope_data'] = daily_data
    data["weekly_horoscope_data"] = weekly_data
    insert_data_into_astra_db(data=data)
    return {"message": "successfully submitted", 'status': 200}
