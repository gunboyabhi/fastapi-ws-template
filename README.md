
1. create virtual env
```
python -m venv env

```
2. activate env
```
env\Scripts\activate
```
3. install libraries 
```
pip install -r requirements.txt
```
4. Create .env file
```
APP_TOKEN = "<app-token>"
LANGFLOW_ID = "<langflow-id>"
FLOW_ID = "<flow-id>"
```
5. Run the application
```
fastapi run
```

6. endpoint for websocket connection (use in react side)
```
ws://localhost:8000/ws
```