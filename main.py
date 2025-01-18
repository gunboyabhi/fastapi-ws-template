import os
import httpx  # Use httpx for async HTTP requests
from fastapi import FastAPI
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

app = FastAPI()

origins = [
    "http://localhost:3000",
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


from pydantic import BaseModel

class MessageRequest(BaseModel):
    message: str

@app.post("/process")
async def process_message(request: MessageRequest):
    return await run_flow_via_http(request.message)
