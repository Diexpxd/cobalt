"""H6 (adaptador en cerebro.py): las órdenes enviadas quedan anotadas, «diagnóstico» genera un archivo con lo que sabe Cobalt (sin claves) y responde en el chat sin"""
import io
import json
import os
import sys
import tempfile
import time

from _cargar import Resultados, cargar_cerebro

ns = cargar_cerebro()
r = Resultados()
tmp = tempfile.mkdtemp()
for var, nombre in [("CONFIG_FILE", "cobalt_config.json"), ("STATUS_FILE", "nox_status.json"), ("GPS_FILE", "gps.json"), ("ENTIDADES_FILE", "entities.json"), ("COMMAND_FILE", "command.json"),
                    ("MODS_FILE", "mods.json"), ("NUBE_REGISTRO_FILE", "nube_registro.jsonl")]:
    ns[var] = os.path.join(tmp, nombre)
ns["DIAGNOSTICO_DIR"] = os.path.join(tmp, "diagnostico")
ns["registrar_mensaje_disco_python"] = lambda *a, **k: None
dg = ns["nox_diagnostico"]
nv = ns["nox_voz"]
GEMINI = "AIzaSyD" + "z" * 32


def w(nombre, datos):
    io.open(os.path.join(tmp, nombre), "w", encoding="utf-8").write(datos if isinstance(datos, str) else json.dumps(datos))


def config(**c):
    w("cobalt_config.json", c)
    ns["_CONFIG_CACHE"]["t"] = 0.0


config()
r.check("las pruebas no secuestran la consola (el Tee solo se instala al arrancar el cerebro de verdad)", not isinstance(sys.stdout, dg.Tee))

anillo = ns["ANILLO_ORDENES"]
n0 = len(anillo.ultimas())
ok = ns["escribir_comando"]([{"action": "mine", "material": "iron_ore", "chat_message": "Voy a minar hierro"}])
ultimas = [x for _, x in anillo.ultimas()][n0:]
r.check("escribir_comando: la orden enviada queda en el anillo con su estado: " + str(ultimas), ok and len(ultimas) == 1 and ultimas[0].startswith("[enviada] action=mine material=iron_ore chat='Voy a minar hierro'"))
n1 = len(anillo.ultimas())
r.check("escribir_comando(sobrescribir=False) con la orden anterior sin consumir: no la envía y lo anota 'en espera'", ns["escribir_comando"]({"action": "stop"}, sobrescribir=False) is False
        and [x for _, x in anillo.ultimas()][n1:][0].startswith("[en espera: Java no consumió la anterior] action=stop"))
os.remove(ns["COMMAND_FILE"])
os.makedirs(ns["COMMAND_FILE"])  # un DIRECTORIO donde debería ir el archivo: escribir falla con OSError
n2 = len(anillo.ultimas())
r.check("escribir_comando que falla al escribir: devuelve False y lo anota 'FALLÓ'", ns["escribir_comando"]({"action": "stop"}) is False and [x for _, x in anillo.ultimas()][n2:][0].startswith("[FALLÓ al escribir]"))
os.rmdir(ns["COMMAND_FILE"])
r.check("escribir_comando: una orden con una clave en el chat no la deja en claro en el anillo", (ns["escribir_comando"]({"action": "ninguna", "chat_message": GEMINI}) or True)
        and "AIza" not in str(anillo.ultimas()))
os.remove(ns["COMMAND_FILE"])

AHORA = 1_800_000_000.0
w("gps.json", {"x": 0, "y": 64, "z": 0, "dimension": "minecraft:overworld", "owner": {"x": 3, "y": 64, "z": 4, "hp": 18.0, "max_hp": 20.0, "alive": True}})
w("nox_status.json", {"is_deployed": True, "hp": 20.0, "max_hp": 20.0})
w("entities.json", {"bot_id": "Cobalt_1", "deployed": True, "updated_ms": AHORA * 1000, "entities": [], "hazards": [], "bot": {"x": 0, "y": 64, "z": 0}})
for nombre, edad in (("gps.json", 4), ("nox_status.json", 400)):
    os.utime(os.path.join(tmp, nombre), (AHORA - edad, AHORA - edad))
os.remove(os.path.join(tmp, "entities.json"))  # sin entities.json: debe figurar 'no existe'
w("mods.json", {"minecraft": "1.20.1", "count": 2, "mods": [{"id": "create", "version": "0.5.1"}, {"id": "mekanism", "version": "10.4"}]})
w("nube_registro.jsonl", "\n".join(json.dumps(x) for x in ({"rol": "chat", "proveedor": "gemini", "ok": True, "seg": 2.0}, {"rol": "chat", "proveedor": "gemini", "ok": False, "error": "timeout", "seg": 12})) + "\nbasura\n")
ns["ANILLO_CONSOLA"].anotar("[-] No se pudo escribir command.json: X")
ns["ANILLO_CONSOLA"].anotar("usando la clave " + GEMINI)
ns["ollama_responde"] = lambda timeout=1.5: True
config(voz_natural=True, nube_router=False, schematics_import=False)
ruta, meta = ns["generar_diagnostico_archivo"](ahora=AHORA)
texto = io.open(ruta, encoding="utf-8").read()
r.check("genera un .md dentro de DIAGNOSTICO_DIR con nombre diagnostico_AAAAMMDD_HHMMSS.md: " + os.path.basename(ruta), os.path.dirname(ruta) == ns["DIAGNOSTICO_DIR"] and __import__("re").fullmatch(r"diagnostico_\d{8}_\d{6}\.md", os.path.basename(ruta)))
r.check("recoge los sensores con su edad (gps 4 s, estado 6 min, entities no existe)", "gps.json: hace 4 s" in texto and "nox_status.json: hace 6 min" in texto and "entities.json: no existe" in texto)
r.check("Java figura ESCRIBIENDO (gps.json de hace 4 s), y el informe muestra lo que ve Cobalt (jugador a 5 bloques)", "ESCRIBIENDO" in texto and "Jugador a 5 bloques" in texto and meta["java_vivo"] is True)
r.check("incluye los mods que exportó Java y los interruptores apagados (nube_router, schematics_import)", "2 mods cargados" in texto and "create@0.5.1" in texto and "nube_router" in texto and "schematics_import" in texto)
r.check("incluye la nube (gemini: 1 ok, 1 fallo, timeout) sin romperse con la línea basura", "chat → gemini: 1 ok, 1 fallos" in texto and "timeout" in texto)
r.check("incluye Ollama y el modelo local, y la consola con el error destacado", "Ollama: responde" in texto and "[-] No se pudo escribir command.json" in texto.split("### Cola completa")[0])
r.check("la CLAVE que salió por la consola NO aparece en el archivo, ni en las órdenes", "AIza" not in texto and "«clave»" in texto)
r.check("incluye las órdenes enviadas que quedaron anotadas", "action=mine material=iron_ore" in texto)

os.remove(ns["MODS_FILE"])
ruta2, meta2 = ns["generar_diagnostico_archivo"](ahora=AHORA + 5)
t2 = io.open(ruta2, encoding="utf-8").read()
r.check("con un Java antiguo (sin mods.json): el informe lo dice y meta['mods'] es None", "no ha exportado" in t2 and meta2["mods"] is None)
w("mods.json", "{roto")
r.check("con mods.json a medio escribir no lanza", ns["generar_diagnostico_archivo"](ahora=AHORA + 6)[1]["mods"] is None)
for nombre in ("gps.json", "nox_status.json", "nube_registro.jsonl"):
    os.remove(os.path.join(tmp, nombre))
t3 = io.open(ns["generar_diagnostico_archivo"](ahora=AHORA + 7)[0], encoding="utf-8").read()
r.check("sin ningún archivo de sensores ni de nube: informe válido, Java SIN ACTIVIDAD", "SIN ACTIVIDAD" in t3 and "sin llamadas registradas" in t3)

d = ns["DIAGNOSTICO_DIR"]
for i in range(30):
    io.open(os.path.join(d, f"diagnostico_20200101_0000{i:02d}.md"), "w", encoding="utf-8").write("viejo")
for propio in ("notas.txt", "diagnostico_manual.md", "diagnostico_20200101_000000.md.bak"):
    io.open(os.path.join(d, propio), "w", encoding="utf-8").write("mio")
ns["generar_diagnostico_archivo"](ahora=AHORA + 20)
restantes = sorted(os.listdir(d))
propios = [n for n in restantes if __import__("re").fullmatch(r"diagnostico_\d{8}_\d{6}\.md", n)]
r.check(f"rotación: quedan como máximo {ns['DIAGNOSTICO_MAX_ARCHIVOS']} informes (los más recientes) y sobrevive el nuevo: {len(propios)}", len(propios) == ns["DIAGNOSTICO_MAX_ARCHIVOS"] and propios[-1].startswith("diagnostico_2027"))
r.check("rotación: NO borra archivos ajenos (notas.txt, diagnostico_manual.md, .bak)", all(x in restantes for x in ("notas.txt", "diagnostico_manual.md", "diagnostico_20200101_000000.md.bak")))

config()
o = ns["aplicar_cortocircuito"]("diagnóstico", "Steve")
t = o[0]["chat_message"] if o else ""
r.check("'diagnóstico' -> orden de solo chat con el resumen: " + repr(t), o and o[0]["action"] == "ninguna" and o[0]["target"] == "Steve" and t.startswith("Diagnóstico guardado en diagnostico_") and t.endswith("interruptores apagados.")
        and not nv.linter_voz(t) and len(t) <= nv.MAX_CHAT)
o = ns["aplicar_cortocircuito"]("haz un diagnóstico de mi granja de Create", "Steve")
r.check("una pregunta sobre otro diagnóstico NO lo dispara (va al modelo)", not o or "Diagnóstico guardado" not in (o[0].get("chat_message") or ""))
config(diagnostico=False)
o = ns["aplicar_cortocircuito"]("diagnóstico", "Steve")
r.check("diagnostico=false: el atajo no responde", not o or "Diagnóstico guardado" not in (o[0].get("chat_message") or ""))
config()
original = ns["generar_diagnostico_archivo"]
ns["generar_diagnostico_archivo"] = lambda *a, **k: (_ for _ in ()).throw(OSError("disco lleno"))
o = ns["aplicar_cortocircuito"]("diagnóstico", "Steve")
r.check("si generar el informe falla (disco lleno...), Cobalt lo admite con una frase del banco y no rompe el chat: " + repr(o), o and o[0]["chat_message"] in nv.BANCO["diagnostico_fallo"])
ns["generar_diagnostico_archivo"] = original

enviados, llamadas = [], []
ns["escribir_comando"] = lambda ordenes, **k: enviados.extend(x.get("chat_message") for x in ordenes)
ns["consultar_ollama"] = lambda *a, **k: llamadas.append(a) or "[]"
ns["consultar_gemini_o_fallback"] = lambda *a, **k: llamadas.append(a) or "[]"
ns["procesar_mensaje_async"]("Steve", "diagnóstico")
r.check("procesar_mensaje_async('diagnóstico'): responde por el chat y no llama a ningún modelo: " + repr(enviados), len(enviados) == 1 and enviados[0].startswith("Diagnóstico guardado en") and not llamadas)
r.check("la frase nueva del banco pasa el linter de voz", all(not nv.linter_voz(x) for x in nv.BANCO["diagnostico_fallo"]))

r.terminar()
