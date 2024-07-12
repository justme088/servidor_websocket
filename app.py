from fastapi import FastAPI, WebSocket, Request, WebSocketDisconnect
from cryptography.fernet import Fernet
from starlette.middleware.cors import CORSMiddleware
import mysql.connector
import json
from collections import defaultdict
from threading import Thread
from asyncio import Queue, Event, create_task, gather, sleep
import asyncio
import signal
import uuid
import os

def tsv(x):
    return Fernet(b'mAIkxJHsxMR4pTO17afKGLOg6M2xptgZ49n_P2P3xoQ=').decrypt(x).decode()

app = FastAPI()

ip = '0.0.0.0'
puerto = 5000
nombre_tabla = "columnas"
cantidad_datos = 10

# Configuración CORS
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

u = tsv(b'gAAAAABmW5Lxj7w68-gCjn6X594pWsQFywkyb72fpQ-dLSHYD66D7oTzLrTiXT6cCNJ1GfVQ4rmuOepxoBs_wqSR-mGs2D8enw==')
p = tsv(b'gAAAAABmW5L1e80sakke6Sbxhq6yRKldsxZWvcvkKLlo_eLPWL9Ruk8zV0VIvrDDA9vmjNq1JCnJQbibBjNV7Rlwyv1t6Eyxs5uoqUptbFMOgqrLi9Zq2IM=')
h = tsv(b'gAAAAABmW5L5JqmQn7tCq-yZLyFcXDYt65j8H-WXt4z-Fz8DwBB-X8kQE33EZo2Yiyikvm3aHK83nd2YD2mo8ecIiJx3-8wAw6qrTm3NOA7hbgOapXl2EGxVnCRMthDGMGbpw2edf1-7')
P = int(tsv(b'gAAAAABmW5L79yTu3nD1ouMESJ_KXq0wGHnlaZEyb4gQpQdlEV7zjoHwBQRmZY4-5eEHp-FK-Dwdr_0Z_Z7e1Pd6avR1wowI5Q=='))
d = tsv(b'gAAAAABmW5L83JtdOdRxjNmkT8-2-sUhdSTp9LjU7IGahvCGObZD2ewvidwnLRtZmlcn36FKEe_f_DjD5CYRYwcb4wqnMVQJMg==')

config = {
    'user': u,
    'password': p,
    'host': h,
    'port': P,
    'database': d
}

user_data = {}

async def fetch_data(user_id):
    while not user_data[user_id]['stop_event'].is_set():
        try:
            print(f"Fetching data for user: {user_id}")
            connection = mysql.connector.connect(**config)
            if connection.is_connected():
                cursor = connection.cursor(dictionary=True)
                cursor.execute(user_data[user_id]['sql_query'])
                new_data = cursor.fetchall()

                updated_column_data = defaultdict(list)
                for row in new_data:
                    for column, value in row.items():
                        if column != 'ns':
                            updated_column_data[column].append(value)

                if user_data[user_id]['column_data'] != updated_column_data:
                    user_data[user_id]['column_data'] = updated_column_data
                    user_data[user_id]['data_updated_event'].set()
                else:
                    user_data[user_id]['data_updated_event'].clear()

        except mysql.connector.Error as e:
            print(f"MySQL Error for user {user_id}: {e}")

        except Exception as e:
            print(f"Unknown Error for user {user_id}: {e}")

        finally:
            if 'connection' in locals() and connection.is_connected():
                cursor.close()
                connection.close()

        await sleep(0.001)

async def send_data(websocket: WebSocket, user_id: str):
    while True:
        await user_data[user_id]['data_updated_event'].wait()
        if len(user_data[user_id]['column_data']) >= 0:
            try:
                await websocket.send_json(user_data[user_id]['column_data'])
                user_data[user_id]['data_updated_event'].clear()
            except Exception as e:
                print(f"Error sending data to WebSocket client {user_id}: {e}")
                break

async def process_messages(user_id: str):
    while True:
        message = await user_data[user_id]['message_queue'].get()
        try:
            message_data = json.loads(message)
            if message_data['message'] == "Inicio":
                user_data[user_id]['sql_query'] = user_data[user_id]['str_a']
                create_task(fetch_data(user_id))
                user_data[user_id]['data_updated_event'].set()
            elif message_data['message'] == "Siguiente":
                user_data[user_id]['sql_query'] = user_data[user_id]['str_b']
                user_data[user_id]['data_updated_event'].set()
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error for user {user_id}: {e}")
        except Exception as e:
            print(f"Error processing message for user {user_id}: {e}")
        finally:
            user_data[user_id]['message_queue'].task_done()

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await websocket.accept()
    try:
        if user_id not in user_data:
            user_data[user_id] = {
                'column_data': '',
                'data_updated_event': Event(),
                'message_queue': Queue(),
                'sql_query': f"SELECT * FROM (SELECT * FROM {nombre_tabla} ORDER BY id DESC) AS sub ORDER BY id ASC;",
                'str_a': f"SELECT * FROM (SELECT * FROM {nombre_tabla} ORDER BY id DESC) AS sub ORDER BY id ASC;",
                'str_b': f"SELECT * FROM columnas ORDER BY id DESC LIMIT 1;",
                'updated_column_data': None,
                'stop_event': Event()
            }

        send_data_task = create_task(send_data(websocket, user_id))
        process_messages_task = create_task(process_messages(user_id))

        async def websocket_receive():
            try:
                while True:
                    data = await websocket.receive_text()
                    await user_data[user_id]['message_queue'].put(data)
            except WebSocketDisconnect:
                print(f"WebSocket connection closed for user: {user_id}")
                user_data[user_id]['stop_event'].set()
            except Exception as e:
                print(f"Error in websocket_receive for user {user_id}: {e}")

        await gather(websocket_receive(), send_data_task)

    except Exception as e:
        print(f"Error for user {user_id}: {e}")
    finally:
        user_data[user_id]['stop_event'].set()
        await websocket.close()

@app.get("/generate_user_id")
async def generate_user_id():
    user_id = str(uuid.uuid4())
    return {"user_id": user_id}

@app.post("/open_connection")
async def open_connection(request: Request):
    data = await request.json()
    message = data.get("message", "")
    if message == 'conectado':
        user_id = data.get("user_id")
        if user_id in user_data:
            user_data[user_id]['column_data'] = ''
            user_data[user_id]['data_updated_event'].set()
            user_data[user_id]['sql_query'] = user_data[user_id]['str_a']
        
    print(f"Closing to reconnect WebSocket connection with message: {message}")
    return {"message": "WebSocket connection closed"}

def signal_handler(sig, frame):
    print("\nKeyboard interrupt detected. Closing program...")
    os._exit(1)

signal.signal(signal.SIGINT, signal_handler)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=ip, port=puerto)
