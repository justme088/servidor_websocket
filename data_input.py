import mysql.connector
from cryptography.fernet import Fernet
import random

def tsv(x):
    return Fernet(b'mAIkxJHsxMR4pTO17afKGLOg6M2xptgZ49n_P2P3xoQ=').decrypt(x).decode()

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

def connect_to_database():
    return mysql.connector.connect(**config)

def create_random_row(cursor):
    random_values = [random.randint(1, 100) for _ in range(3)]
    cursor.execute("INSERT INTO columnas (columna1, columna2, columna3) VALUES (%s, %s, %s)", random_values)

def delete_last_row(cursor):
    cursor.execute("DELETE FROM columnas ORDER BY id DESC LIMIT 1")

def show_table_contents(cursor):
    cursor.execute("SELECT columna1, columna2, columna3 FROM columnas ORDER BY id")
    rows = cursor.fetchall()
    for row in rows:
        print(row)

def main():
    while True:
        print("\n1. Agregar nueva fila con números aleatorios")
        print("2. Eliminar última fila")
        print("3. Mostrar contenidos de la tabla")
        print("4. Salir")
        choice = input("Seleccione una opción: ")
        print()

        if choice == "1":
            connection = connect_to_database()
            cursor = connection.cursor()
            create_random_row(cursor)
            connection.commit()
            cursor.close()
            connection.close()
            print("Nueva fila agregada con éxito.")

        elif choice == "2":
            connection = connect_to_database()
            cursor = connection.cursor()
            delete_last_row(cursor)
            connection.commit()
            cursor.close()
            connection.close()
            print("Última fila eliminada con éxito.")

        elif choice == "3":
            connection = connect_to_database()
            cursor = connection.cursor()
            print("Contenidos de la tabla:")
            show_table_contents(cursor)
            cursor.close()
            connection.close()

        elif choice == "4":
            print("Saliendo del programa...")
            break

        else:
            print("Opción inválida. Inténtelo de nuevo.")


if __name__ == "__main__":
	    main()
