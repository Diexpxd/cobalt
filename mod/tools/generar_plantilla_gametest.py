"""Genera la plantilla de estructura de las GameTests: 9x6x9 con un suelo de piedra (y=0) y aire encima.
Uso (una vez, o al cambiar el tamano):  python tools/generar_plantilla_gametest.py
Escribe src/main/resources/data/cobaltmod/structures/empty.nbt (NBT sin dependencias, comprimido con gzip)."""
import gzip
import os
import struct

ANCHO, ALTO, LARGO = 9, 6, 9
DATA_VERSION = 3465  # Minecraft 1.20.1


def cad(s):
    b = s.encode("utf-8")
    return struct.pack(">H", len(b)) + b


def etiqueta(tipo, nombre, carga):
    return bytes([tipo]) + cad(nombre) + carga


def compuesto(hijos):
    return b"".join(hijos) + b"\x00"


def lista(tipo, elementos):
    return bytes([tipo]) + struct.pack(">i", len(elementos)) + b"".join(elementos)


def entero(v):
    return struct.pack(">i", v)


bloques = []
for x in range(ANCHO):
    for z in range(LARGO):
        bloques.append(compuesto([etiqueta(9, "pos", lista(3, [entero(x), entero(0), entero(z)])), etiqueta(3, "state", entero(0))]))
raiz = compuesto([
    etiqueta(3, "DataVersion", entero(DATA_VERSION)),
    etiqueta(9, "size", lista(3, [entero(ANCHO), entero(ALTO), entero(LARGO)])),
    etiqueta(9, "palette", lista(10, [compuesto([etiqueta(8, "Name", cad("minecraft:stone"))])])),
    etiqueta(9, "blocks", lista(10, bloques)),
    etiqueta(9, "entities", lista(10, [])),
])
destino = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "main", "resources", "data", "cobaltmod", "structures", "empty.nbt")
os.makedirs(os.path.dirname(destino), exist_ok=True)
with open(destino, "wb") as f:
    f.write(gzip.compress(b"\x0a" + cad("") + raiz))
print("escrito", os.path.normpath(destino), os.path.getsize(destino), "bytes")
