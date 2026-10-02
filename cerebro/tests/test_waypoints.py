"""Pruebas del Bloque 0: waypoints (nombres, reparación de claves, protección ante archivo corrupto, posición del jugador)."""
import io
import json
import os
import tempfile

from _cargar import Resultados, cargar_cerebro

ns = cargar_cerebro()
r = Resultados()
tmp = tempfile.mkdtemp()
ns["WAYPOINTS_FILE"] = os.path.join(tmp, "waypoints.json")
ns["GPS_FILE"] = os.path.join(tmp, "gps.json")


def escribir(ruta, contenido):
    io.open(ruta, "w", encoding="utf-8").write(contenido if isinstance(contenido, str) else json.dumps(contenido))


def leer(ruta):
    return io.open(ruta, encoding="utf-8").read()


def borrar_waypoints():
    for f in (ns["WAYPOINTS_FILE"], ns["WAYPOINTS_FILE"] + ".tmp"):
        if os.path.exists(f):
            os.remove(f)


norm = ns["normalizar_nombre_waypoint"]

# 1. Normalización de nombres
r.check("normaliza comilla final (el bug real: 'zona_industrial\"')", norm('zona_industrial"') == "zona_industrial")
r.check("normaliza comillas alrededor", norm('"Zona Industrial"') == "zona_industrial")
r.check("quita artículos y puntuación", norm("la zona_industrial!") == "zona_industrial")
r.check("'plaza' NO se destroza (antes replace('la','') daba 'pza')", norm("Plaza") == "plaza")
r.check("'hotel' y 'cielo' intactos (antes replace('el',''))", norm("hotel") == "hotel" and norm("cielo") == "cielo")
r.check("quita acentos y eñes", norm("Ñandú") == "nandu")
r.check("'mi base' -> 'base'", norm("mi base") == "base")

# 2. Extracción del nombre desde el chat
ext = ns["extraer_nombre_waypoint"]
r.check("'como base' -> base", ext("guarda este lugar como base") == "base")
r.check("'para la base' -> base (frase real del historial)", ext("guarda este lugar para la base") == "base")
r.check("'como base secundaria' NO pisa 'base'", ext("guarda este lugar como base secundaria") == "base_secundaria")
r.check("'como la plaza' -> plaza", ext("guarda este lugar como la plaza") == "plaza")
r.check("'llamada Mina Norte' -> mina_norte", ext("guarda esta zona llamada Mina Norte") == "mina_norte")
r.check("sin nombre ni 'base' -> vacío (se genera punto_NNN)", ext("guarda este lugar") == "")
r.check("sin separador pero nombrando la base -> base", ext("marca este punto cerca de la base") == "base")

# 3. Reparación de claves sucias en disco, conservando TODO
borrar_waypoints()
escribir(ns["WAYPOINTS_FILE"], {'zona_industrial"': {"x": 9, "y": 69, "z": 37}, "base": {"x": 647, "y": 118, "z": 3},
                                "nota": "entrada rara sin coordenadas"})
wp = ns["cargar_waypoints"]()
r.check("repara 'zona_industrial\"' -> 'zona_industrial'", "zona_industrial" in wp and 'zona_industrial"' not in wp)
r.check("conserva coordenadas y la entrada rara", wp["zona_industrial"] == {"x": 9, "y": 69, "z": 37} and wp["nota"] == "entrada rara sin coordenadas")
en_disco = json.loads(leer(ns["WAYPOINTS_FILE"]))
r.check("la reparación se persistió en disco", "zona_industrial" in en_disco and 'zona_industrial"' not in en_disco)
r.check("no queda waypoints.json.tmp", not os.path.exists(ns["WAYPOINTS_FILE"] + ".tmp"))

escribir(ns["GPS_FILE"], {"x": 1, "y": 2, "z": 3})
corrupto = '{"base": {"x": 647, "y": 118, "z"'
escribir(ns["WAYPOINTS_FILE"], corrupto)
r.check("cargar_waypoints devuelve None si está corrupto", ns["cargar_waypoints"]() is None)
msg = ns["gestionar_waypoints"]("guardar", "guarda este lugar como casa")
r.check("guardar se niega y avisa", "ilegible" in msg)
r.check("el archivo corrupto queda BYTE A BYTE intacto", leer(ns["WAYPOINTS_FILE"]) == corrupto)
r.check("listar avisa en vez de decir 'no tienes ninguno'", "ilegible" in ns["gestionar_waypoints"]("listar"))

# 5. Guardar: posición del JUGADOR con respaldo en Cobalt
borrar_waypoints()
escribir(ns["GPS_FILE"], {"x": 10, "y": 64, "z": 20, "owner": {"x": 100, "y": 70, "z": 200}})
msg = ns["gestionar_waypoints"]("guardar", "guarda este lugar como la plaza")
wp = json.loads(leer(ns["WAYPOINTS_FILE"]))
r.check("guarda la posición del JUGADOR (owner), no la de Cobalt", wp.get("plaza") == {"x": 100, "y": 70, "z": 200})
r.check("el mensaje indica el origen", "jugador" in msg and "'plaza'" in msg)

escribir(ns["GPS_FILE"], {"x": 10, "y": 64, "z": 20})
ns["gestionar_waypoints"]("guardar", "guarda este lugar como mina")
r.check("sin 'owner' cae a la posición de Cobalt", json.loads(leer(ns["WAYPOINTS_FILE"])).get("mina") == {"x": 10, "y": 64, "z": 20})

escribir(ns["GPS_FILE"], {"x": 5.6, "y": 64.2, "z": -7.5})
ns["gestionar_waypoints"]("guardar", "guarda este lugar como punto_float")
v = json.loads(leer(ns["WAYPOINTS_FILE"]))["punto_float"]
r.check("las coordenadas se guardan como enteros", all(isinstance(v[c], int) for c in "xyz"))

ns["gestionar_waypoints"]("guardar", "guarda este lugar como base")
escribir(ns["GPS_FILE"], {"x": 1, "y": 1, "z": 1})
msg = ns["gestionar_waypoints"]("guardar", "guarda este lugar como base")
r.check("al re-guardar 'base' avisa de dónde estaba antes", "Antes estaba" in msg)

escribir(ns["GPS_FILE"], "")
r.check("sin GPS no guarda", "GPS" in ns["gestionar_waypoints"]("guardar", "guarda este lugar como x"))

nombres = set()
borrar_waypoints()
escribir(ns["GPS_FILE"], {"x": 1, "y": 2, "z": 3})
for _ in range(5):
    ns["gestionar_waypoints"]("guardar", "guarda este lugar")
r.check("sin nombre: 5 guardados -> 5 punto_NNN distintos", len(json.loads(leer(ns["WAYPOINTS_FILE"]))) == 5)

# 6. Búsqueda tolerante
borrar_waypoints()
escribir(ns["WAYPOINTS_FILE"], {"zona_industrial": {"x": 9, "y": 69, "z": 37}, "base": {"x": 647, "y": 118, "z": 3},
                                "mina_norte": {"x": 1, "y": 2, "z": 3}, "mina_sur": {"x": 4, "y": 5, "z": 6}})
buscar = ns["buscar_waypoint"]
r.check("exacto con artículo y comillas", buscar('la "Zona_Industrial"')[0] == "zona_industrial")
r.check("parcial única: 'zona' -> zona_industrial", buscar("zona")[0] == "zona_industrial")
r.check("parcial ambigua: 'mina' -> None (no adivina)", buscar("mina") is None)
r.check("inexistente -> None", buscar("castillo") is None)

# 7. base exacta y perímetro de seguridad
r.check("obtener_coordenadas_base exacta", ns["obtener_coordenadas_base"]() == {"x": 647, "y": 118, "z": 3})
r.check("a 10 bloques de la base: bloqueado", ns["es_zona_segura"](657, 118, 3) is False)
r.check("a 50 bloques de la base: permitido", ns["es_zona_segura"](697, 118, 3) is True)
escribir(ns["WAYPOINTS_FILE"], {"base_secundaria": {"x": 0, "y": 0, "z": 0}})
r.check("una 'base_secundaria' NO se toma como la base", ns["obtener_coordenadas_base"]() is None)

# 8. Parseo de "construye ..."
pd = ns["extraer_plano_y_destino"]
r.check("'construye fission_reactor en zona_industrial\"' (sucio)", pd('construye fission_reactor en zona_industrial"') == ("fission_reactor", "zona_industrial"))
r.check("'construye un reactor en la base' (antes daba plano='un')", pd("construye un reactor en la base") == ("reactor", "base"))
r.check("'construye el fission reactor en la zona industrial'", pd("construye el fission reactor en la zona industrial") == ("fission_reactor", "zona_industrial"))
r.check("'edifica' funciona igual", pd("edifica fission_reactor hacia mina_norte") == ("fission_reactor", "mina_norte"))
r.check("corta el destino en 'y'/'luego'", pd("construye fission_reactor en la base y luego ven") == ("fission_reactor", "base"))
r.check("solo 'construye' -> valores por defecto", pd("construye") == ("fission_reactor", "zona_industrial"))
r.check("el plano nunca contiene barras ni puntos (ruta segura)", not set(pd("construye ../../secreto en base")[0]) & set("./\\"))

# 9. Integración: aplicar_cortocircuito (con iniciar_construccion simulada)
borrar_waypoints()
escribir(ns["WAYPOINTS_FILE"], {'zona_industrial"': {"x": 9.4, "y": 69, "z": 37}})  # exactamente el archivo roto del usuario
llamadas = []
ns["iniciar_construccion"] = lambda *a: llamadas.append(a)
res = ns["aplicar_cortocircuito"]("construye fission_reactor en zona_industrial", "Dev")
import time
time.sleep(0.2)  # el hilo daemon
r.check("con el archivo roto del usuario ahora SÍ encuentra 'zona_industrial'", "Empiezo a construir en 'zona_industrial'" in res[0]["chat_message"])
r.check("lanza la construcción con enteros", llamadas and llamadas[0] == ("fission_reactor", 9, 69, 37, "Dev"))
res = ns["aplicar_cortocircuito"]("construye fission_reactor en castillo", "Dev")
r.check("waypoint inexistente: avisa y lista los conocidos", "castillo" in res[0]["chat_message"] and "zona_industrial" in res[0]["chat_message"])

r.terminar()
