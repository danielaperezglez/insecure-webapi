import json
import random
import hashlib
import mysql.connector
import base64
import shutil
import html
import logging

from datetime import datetime
from pathlib import Path
from bottle import route, run, post, request, static_file

logging.basicConfig(
    filename='api.log',
    level=logging.ERROR,
    format='%(asctime)s %(levelname)s:%(message)s'
)

@route('/')
def home():
    return {"status": "API funcionando"}

def loadDatabaseSettings(pathjs):

    pathjs = Path(pathjs)

    if pathjs.exists():

        with pathjs.open() as data:
            return json.load(data)

    return False

def getToken():

    tiempo = datetime.now().timestamp()

    numero = random.random()

    cadena = str(tiempo) + str(numero)

    m = hashlib.sha1()
    m.update(cadena.encode())
    P = m.hexdigest()

    m = hashlib.md5()
    m.update(cadena.encode())
    Q = m.hexdigest()

    return f"{P[:20]}{Q[20:]}"

@post('/Registro')
def Registro():

    if not request.json:
        return {"R": -1}

    campos = ['uname', 'email', 'password']

    for campo in campos:
        if campo not in request.json:
            return {"R": -1}

    uname = html.escape(
        request.json["uname"].strip()
    )

    email = html.escape(
        request.json["email"].strip()
    )

    password = request.json["password"]

    if len(uname) > 50:
        return {"R": -1}

    if len(email) > 100:
        return {"R": -1}

    dbcnf = loadDatabaseSettings('db.json')

    db = mysql.connector.connect(
        host='localhost',
        port=dbcnf['port'],
        database=dbcnf['dbname'],
        user=dbcnf['user'],
        password=dbcnf['password']
    )

    try:

        with db.cursor() as cursor:

            query = """
            INSERT INTO Usuario
            VALUES(NULL,%s,%s,MD5(%s))
            """

            values = (
                uname,
                email,
                password
            )

            cursor.execute(query, values)

            db.commit()

            nuevo_id = cursor.lastrowid

        db.close()

        return {"R": 0, "D": nuevo_id}

    except Exception as e:

        logging.error(str(e))

        db.close()

        return {"R": -2}

@post('/Login')
def Login():

    if not request.json:
        return {"R": -1}

    campos = ['uname', 'password']

    for campo in campos:
        if campo not in request.json:
            return {"R": -1}

    uname = request.json["uname"].strip()

    password = request.json["password"]

    dbcnf = loadDatabaseSettings('db.json')

    db = mysql.connector.connect(
        host='localhost',
        port=dbcnf['port'],
        database=dbcnf['dbname'],
        user=dbcnf['user'],
        password=dbcnf['password']
    )

    try:

        with db.cursor() as cursor:

            query = """
            SELECT id
            FROM Usuario
            WHERE uname=%s
            AND password=MD5(%s)
            """

            values = (
                uname,
                password
            )

            cursor.execute(query, values)

            R = cursor.fetchall()

        if not R:

            db.close()

            return {"R": -3}

        id_Usuario = R[0][0]

        T = getToken()

        with db.cursor() as cursor:

            cursor.execute(
                "DELETE FROM AccesoToken WHERE id_Usuario=%s",
                (id_Usuario,)
            )

            cursor.execute(
                "INSERT INTO AccesoToken VALUES(%s,%s,NOW())",
                (id_Usuario, T)
            )

            db.commit()

        db.close()

        return {"R": 0, "D": T}

    except Exception as e:

        logging.error(str(e))

        db.close()

        return {"R": -2}

@post('/Imagen')
def Imagen():

    tmp = Path('tmp')

    if not tmp.exists():
        tmp.mkdir()

    img = Path('img')

    if not img.exists():
        img.mkdir()

    if not request.json:
        return {"R": -1}

    campos = ['name', 'data', 'ext', 'token']

    for campo in campos:

        if campo not in request.json:
            return {"R": -1}

    nombre = html.escape(
        request.json["name"].strip()
    )

    if nombre == "":
        return {"R": -1}

    if len(nombre) > 100:
        return {"R": -1}

    extensiones_permitidas = [
        "png",
        "jpg",
        "jpeg",
        "gif"
    ]

    extension = request.json["ext"].lower()

    if extension not in extensiones_permitidas:

        return {
            "R": -5,
            "MSG": "Extensión no permitida"
        }

    if len(request.json["data"]) > 5000000:

        return {
            "R": -6,
            "MSG": "Archivo demasiado grande"
        }

    dbcnf = loadDatabaseSettings('db.json')

    db = mysql.connector.connect(
        host='localhost',
        port=dbcnf['port'],
        database=dbcnf['dbname'],
        user=dbcnf['user'],
        password=dbcnf['password']
    )

    TKN = request.json["token"]

    try:

        with db.cursor() as cursor:

            cursor.execute(
                "SELECT id_Usuario FROM AccesoToken WHERE token=%s",
                (TKN,)
            )

            R = cursor.fetchall()

        if not R:

            db.close()

            return {"R": -3}

        id_Usuario = R[0][0]

        ruta_tmp = f"tmp/{id_Usuario}"

        with open(ruta_tmp, "wb") as imagen:

            imagen.write(
                base64.b64decode(
                    request.json["data"].encode()
                )
            )

        with db.cursor() as cursor:

            cursor.execute(
                """
                INSERT INTO Imagen
                VALUES(NULL,%s,%s,%s)
                """,
                (
                    nombre,
                    "img/",
                    id_Usuario
                )
            )

            db.commit()

            idImagen = cursor.lastrowid

            ruta = f"img/{idImagen}.{extension}"

            cursor.execute(
                """
                UPDATE Imagen
                SET ruta=%s
                WHERE id=%s
                """,
                (
                    ruta,
                    idImagen
                )
            )

            db.commit()

        shutil.move(
            ruta_tmp,
            ruta
        )

        db.close()

        return {
            "R": 0,
            "D": idImagen
        }

    except Exception as e:

        logging.error(str(e))

        db.close()

        return {"R": -2}

@post('/Descargar')
def Descargar():

    if not request.json:
        return {"R": -1}

    campos = ['token', 'id']

    for campo in campos:

        if campo not in request.json:
            return {"R": -1}

    TKN = request.json["token"]

    idImagen = request.json["id"]

    dbcnf = loadDatabaseSettings('db.json')

    db = mysql.connector.connect(
        host='localhost',
        port=dbcnf['port'],
        database=dbcnf['dbname'],
        user=dbcnf['user'],
        password=dbcnf['password']
    )

    try:

        with db.cursor() as cursor:

            cursor.execute(
                """
                SELECT id_Usuario
                FROM AccesoToken
                WHERE token=%s
                """,
                (TKN,)
            )

            R = cursor.fetchall()

        if not R:

            db.close()

            return {"R": -3}

        with db.cursor() as cursor:

            cursor.execute(
                """
                SELECT name, ruta
                FROM Imagen
                WHERE id=%s
                """,
                (idImagen,)
            )

            R = cursor.fetchall()

        if not R:

            db.close()

            return {"R": -4}

        ruta = R[0][1]

        db.close()

        return static_file(
            ruta,
            root=Path(".").resolve()
        )

    except Exception as e:

        logging.error(str(e))

        db.close()

        return {"R": -2}

if __name__ == '__main__':
    run(
        host='0.0.0.0',
        port=8080,
        debug=False,
        server='cheroot',
        certfile='localhost+1.pem',
        keyfile='localhost+1-key.pem'
    )
