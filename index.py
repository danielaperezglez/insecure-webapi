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
from bottle import route, run, template, post, request, static_file

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
        sjson = False
        if pathjs.exists():
                with pathjs.open() as data:
                        sjson = json.load(data)
        return sjson


def getToken():
        tiempo = datetime.now().timestamp()
        numero = random.random()
        cadena = str(tiempo) + str(numero)
        numero2 = random.random()
        cadena2 = str(numero) + str(tiempo) + str(numero2)

        m = hashlib.sha1()
        m.update(cadena.encode())
        P = m.hexdigest()

        m = hashlib.md5()
        m.update(cadena.encode())
        Q = m.hexdigest()

        return f"{P[:20]}{Q[20:]}"


@post('/Registro')
def Registro():
        dbcnf = loadDatabaseSettings('db.json')

        db = mysql.connector.connect(
                host='localhost',
                port=dbcnf['port'],
                database=dbcnf['dbname'],
                user=dbcnf['user'],
                password=dbcnf['password']
        )

        if not request.json:
                return {"R": -1}

        R = 'uname' in request.json and 'email' in request.json and 'password' in request.json
        if not R:
                return {"R": -1}

        try:
                with db.cursor() as cursor:
                        cursor.execute(
                            "INSERT INTO Usuario VALUES(NULL,%s,%s,md5(%s))",
                            (request.json["uname"], request.json["email"], request.json["password"])
                        )
                        R = cursor.lastrowid
                        db.commit()

                db.close()

        except Exception as e:
                logging.error(str(e))
                return {"R": -2}

        return {"R": 0, "D": R}


@post('/Login')
def Login():
        dbcnf = loadDatabaseSettings('db.json')

        db = mysql.connector.connect(
                host='localhost',
                port=dbcnf['port'],
                database=dbcnf['dbname'],
                user=dbcnf['user'],
                password=dbcnf['password']
        )

        if not request.json:
                return {"R": -1}

        R = 'uname' in request.json and 'password' in request.json
        if not R:
                return {"R": -1}

        try:
                with db.cursor() as cursor:
                        cursor.execute(
                            "SELECT id FROM Usuario WHERE uname=%s AND password=md5(%s)",
                            (request.json["uname"], request.json["password"])
                        )
                        R = cursor.fetchall()

        except Exception as e:
                logging.error(str(e))
                db.close()
                return {"R": -2}


        try:
                with db.cursor() as cursor:
                        cursor.execute(
                            "DELETE FROM AccesoToken WHERE id_Usuario=%s",
                            (R[0][0],)
                        )

                        cursor.execute(
                            "INSERT INTO AccesoToken VALUES(%s,%s,NOW())",
                            (R[0][0], T)
                        )

                        db.commit()
                        db.close()
                        return {"R": 0, "D": T}

        except Exception as e:
                logging.error(str(e))
                db.close()
                return {"R": -4}


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

        extensiones_permitidas = ["png", "jpg", "jpeg", "gif"]

        if request.json["ext"].lower() not in extensiones_permitidas:
                return {"R": -5, "MSG": "Extensión no permitida"}

        R = (
                'name' in request.json and
                'data' in request.json and
                'ext' in request.json and
                'token' in request.json
        )

        if not R:
                return {"R": -1}
        request.json["name"] = html.escape(request.json["name"])

        dbcnf = loadDatabaseSettings('db.json')

        db = mysql.connector.connect(
                host='localhost',
                port=dbcnf['port'],
                database=dbcnf['dbname'],
                user=dbcnf['user'],
                password=dbcnf['password']
        )

        TKN = request.json['token']

        try:
                with db.cursor() as cursor:
                        cursor.execute(
                            "SELECT id_Usuario FROM AccesoToken WHERE token = %s",
                            (TKN,)
                        )
                        R = cursor.fetchall()

        except Exception as e:
                logging.error(str(e))
                db.close()
                return {"R": -2}

        id_Usuario = R[0][0]

        try:
                with db.cursor() as cursor:
                        cursor.execute(
                            "INSERT INTO Imagen VALUES(NULL,%s,%s,%s)",
                            (request.json["name"], "img/", id_Usuario)
                        )

                        cursor.execute(
                            "SELECT MAX(id) AS idImagen FROM Imagen WHERE id_Usuario=%s",
                            (id_Usuario,)
                        )

                        R = cursor.fetchall()
                        idImagen = R[0][0]

                        ruta = f"img/{idImagen}.{request.json['ext']}"

                        cursor.execute(
                            "UPDATE Imagen SET ruta=%s WHERE id=%s",
                            (ruta, idImagen)
                        )

                        db.commit()

                        shutil.move(
                                "tmp/" + str(id_Usuario),
                                ruta
                        )

                        return {"R": 0, "D": idImagen}
                        return {"R": 0, "D": idImagen}

        except Exception as e:
                logging.error(str(e))
                db.close()
                return {"R": -3}


@post('/Descargar')
def Descargar():
        dbcnf = loadDatabaseSettings('db.json')

        db = mysql.connector.connect(
                host='localhost',
                port=dbcnf['port'],
                database=dbcnf['dbname'],
                user=dbcnf['user'],
                password=dbcnf['password']
        )

        if not request.json:
                return {"R": -1}

        R = 'token' in request.json and 'id' in request.json

        if not R:
                return {"R": -1}

        TKN = request.json['token']
        idImagen = request.json['id']

        try:
                with db.cursor() as cursor:
                    cursor.execute(
                            "SELECT id_Usuario FROM AccesoToken WHERE token = %s",
                            (TKN,)
                            )

                    R = cursor.fetchall()

        except Exception as e:
                logging.error(str(e))
                db.close()
                return {"R": -2}

        try:
                with db.cursor() as cursor:
                    cursor.execute(
                            "SELECT name, ruta FROM Imagen WHERE id = %ss",
                            (idImagen,)
                            )

                    R = cursor.fetchall()

        except Exception as e:
                logging.error(str(e))
                db.close()
                return {"R": -3}

        print(Path("img").resolve(), R[0][1])

        return static_file(
                R[0][1],
                Path(".").resolve()
        )


if __name__ == '__main__':
        run(
                host='0.0.0.0',
                port=8080,
                debug=False,
                server='cheroot',
                certfile='localhost+1.pem',
                keyfile='localhost+1-key.pem'
                

)
