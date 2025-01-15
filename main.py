import os
import aiohttp
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
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

async def run_flow_via_websocket(message: str, websocket: WebSocket):
    try:
        api_url = f"{BASE_API_URL}/lf/{LANGFLOW_ID}/api/v1/run/{ENDPOINT}?stream=true"
        
        payload = {
            "input_value": message,
            "output_type": "chat",
            "input_type": "chat",
        }
        
        headers = {
            "Authorization": f"Bearer {APPLICATION_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # Initiate the flow with streaming enabled
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=payload, headers=headers) as response:
                if response.status != 200:
                    await websocket.send_text(f"Error: {response.status} - {await response.text()}")
                    return
                
                # Parse the JSON response to get the stream URL
                response_data = await response.json()
                outputs = response_data.get("outputs", [])
                if outputs:
                    first_output = outputs[0].get("outputs", [])
                    if first_output:
                        artifacts = first_output[0].get("artifacts", {})
                        stream_url = artifacts.get("stream_url")
                        if stream_url:
                            # Construct the full stream URL if necessary
                            full_stream_url = f"{BASE_API_URL}{stream_url}?session_id={response_data.get('session_id')}"
                        else:
                            await websocket.send_text("Error: No stream_url found in the response.")
                            return
                    else:
                        await websocket.send_text("Error: No outputs found in the response.")
                        return
                else:
                    await websocket.send_text("Error: No outputs found in the response.")
                    return


            # Connect to the stream URL and process the streaming data
            async with session.get(full_stream_url, headers=headers) as stream_response:
                if stream_response.status != 200:
                    await websocket.send_text(f"Error: {stream_response.status} - {await stream_response.text()}")
                    return

                async for chunk in stream_response.content.iter_any():
                    if chunk:
                        await websocket.send_text(chunk.decode("utf-8"))


    except WebSocketDisconnect:
        print("Client disconnected")
        
    except Exception as e:
        await websocket.send_text(f"An error occurred: {str(e)}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Receive message from the WebSocket client
            message = await websocket.receive_text()
            
            # Process the message via LangFlow and stream the result
            await run_flow_via_websocket(message, websocket)
    except WebSocketDisconnect:
        print("Client disconnected")
