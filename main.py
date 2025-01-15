import os
import aiohttp
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()

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
                stream_url = response_data.get("stream_url")
                if not stream_url:
                    await websocket.send_text("Error: No stream_url found in the response.")
                    return

            # Connect to the stream URL and process the streaming data
            async with session.get(stream_url, headers=headers) as stream_response:
                if stream_response.status != 200:
                    await websocket.send_text(f"Error: {stream_response.status} - {await stream_response.text()}")
                    return

                async for line in stream_response.content:
                    if line:
                        await websocket.send_text(line.decode("utf-8"))

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
