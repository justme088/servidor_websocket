from fastapi import FastAPI, WebSocket, Request
from cryptography.fernet import Fernet
from starlette.middleware.cors import CORSMiddleware
import mysql.connector
import json
from collections import defaultdict
from threading import Lock, Thread, Event
import asyncio
import signal
import os

def tsv(x):
    return Fernet(b'mAIkxJHsxMR4pTO17afKGLOg6M2xptgZ49n_P2P3xoQ=').decrypt(x).decode()

app = FastAPI()

ip = '0.0.0.0'
puerto = 5000
nombre_tabla = "columnas"
cantidad_datos = 10

# Configuración CORS
origins = ["*"]  # Permitir todas las solicitudes
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

# Configuración de la base de datos
config = {
    'user': u,
    'password': p,
    'host': h,
    'port': P,
    'database': d
}

thread_lock = Lock()
column_data = defaultdict(list)

data_updated_event = asyncio.Event()

updated_column_data = None

def background_thread_1():
    global column_data, updated_column_data
    while True:
        try:
            connection = mysql.connector.connect(**config)
            if connection.is_connected():
                cursor = connection.cursor(dictionary=True)
                cursor.execute(f"SELECT * FROM (SELECT * FROM {nombre_tabla} ORDER BY id DESC LIMIT {str(cantidad_datos)}) AS sub ORDER BY id ASC;")
                new_data = cursor.fetchall()

                # Agrupar los datos por columnas
                updated_column_data = defaultdict(list)
                for row in new_data:
                    for column, value in row.items():
                        if column != 'id':  # Ignorar la columna 'id'
                            updated_column_data[column].append(value)

                # Actualizar los datos de la columna
                if column_data != updated_column_data:
                    column_data = updated_column_data
                    data_updated_event.set()
                else:
                    data_updated_event.clear()

        except mysql.connector.Error as e:
            print(f"Error de MySQL: {e}")

        except Exception as e:
            print(f"Error desconocido: {e}")

        finally:
            if 'connection' in locals() and connection.is_connected():
                cursor.close()
                connection.close()

async def background_thread_2(websocket: WebSocket):
    while True:
        await data_updated_event.wait()
        if len(column_data) > 0:
            try:
                # Enviar los datos al cliente
                print("Datos en el json: "+str(len(column_data)))
                await websocket.send_json(column_data)
                print('Datos enviados')

                # Esperar un tiempo antes de enviar los datos nuevamente
                await asyncio.sleep(0.005)
            except Exception as e:
                #print(f"Error al enviar datos al cliente: {e}")
                pass
        if column_data == updated_column_data:
            data_updated_event.clear()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        global column_data, data_updated_event, updated_column_data
        data_updated_event.set()
        if len(column_data) <= 0:  # Iniciar el hilo solo si los datos están vacíos
            background_thread_thread_1 = Thread(target=background_thread_1)
            background_thread_thread_1.start()

        # Ejecutar el background_thread_2 en un hilo separado y esperar a que termine
        await background_thread_2(websocket)

    except Exception as e:
        #print("Error:", e)
        pass
    finally:
        updated_column_data = None
        await websocket.close()

@app.post("/open_connection")
async def open_connection(request: Request):
    global data_updated_event #, updated_column_data
    #updated_column_data = None
    data = await request.json()
    message = data.get("message", "")
    if message == 'conectado':
    	data_updated_event.set()
    print(f"Closing to reconnect WebSocket connection with message: {message}")
    return {"message": "WebSocket connection closed"}

def signal_handler(sig, frame):
    print("\nInterrupción de teclado detectada. Cerrando el programa...")
    os._exit(1)

signal.signal(signal.SIGINT, signal_handler)

if __name__ == "__main__":
	#importar contenedor e iniciar el servidor
    import uvicorn
    uvicorn.run(app, host=ip, port=puerto)
    
