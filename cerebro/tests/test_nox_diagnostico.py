"""H6: diagnóstico."""
import io
import json
import random
import os
import sys
import threading
import time

from _cargar import Resultados

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cerebro"))
import nox_diagnostico as dg  # noqa: E402
import nox_voz  # noqa: E402

r = Resultados()

GEMINI = "AIzaSyD" + "a" * 32
CLAUDE = "sk-ant-api03-" + "b" * 30
casos = {
    "usando " + GEMINI + " para el chat": "AIza",
    "header Authorization: Bearer " + "g" * 40 + " enviado": "g" * 40,
    "solo Bearer " + "h" * 40: "h" * 40,
    "COBALT_CLAUDE_KEY=" + "d" * 20: "d" * 20,
    'api_key: "eeeeeeeeeeee"': "eeeeeeeeeeee",
    "token=ffffffff1234": "ffffffff1234",
    "clave " + CLAUDE + " fin": "sk-ant",
    "escribeme a usuario@ejemplo.com por favor": "ejemplo",
    "hash " + "0123456789abcdef" * 3 + " visto": "0123456789abcdef0123456789abcdef",
    "password: hunter22": "hunter22",
}
fugas = [k for k, secreto in casos.items() if secreto in dg.redactar(k)]
r.check("redactar oculta claves de Gemini y Claude, Bearer, KEY=, api_key, token, correos, hashes largos y contraseñas: fugas=" + str(fugas), not fugas)
normales = ["Plano 'casa' cargado. Empiezo a construir en 'base'.", r"C:\\Proyectos\\cobalt", "[Reflejo Radar] 2 amenaza(s) de 3", "Hostiles cerca: 1 (el más cercano, Zombie a 7 bloques)."]
r.check("redactar no toca texto normal ni rutas", all(dg.redactar(x) == x for x in normales))
r.check("redactar deja una marca legible: «clave», «oculto», «correo»", "«clave»" in dg.redactar(GEMINI) and "«oculto»" in dg.redactar("token=abcdefgh") and dg.redactar("a@b.co") == "«correo»")
r.check("redactar acota el largo con '…'", len(dg.redactar("x" * 1000)) == dg.MAX_LINEA and dg.redactar("x" * 1000).endswith("…") and dg.redactar("x" * 50, 10) == "x" * 9 + "…")
r.check("redactar es idempotente", all(dg.redactar(dg.redactar(k)) == dg.redactar(k) for k in list(casos) + normales))
r.check("redactar tolera None, números, bytes y objetos raros (devuelve str)", all(isinstance(dg.redactar(x), str) for x in (None, 5, b"abc", [1, 2], {"a": 1}, object())))


class Explota:
    def __str__(self):
        raise RuntimeError("no se puede convertir")


r.check("redactar con un objeto cuyo __str__ lanza -> «ilegible», sin lanzar", dg.redactar(Explota()) == "«ilegible»")

t = [0.0]
a = dg.Anillo(3, reloj=lambda: t[0])
for i in range(5):
    t[0] = float(i)
    a.anotar(f"linea {i}")
r.check("anillo: conserva solo las últimas N (capacidad 3) en orden, con su hora", a.ultimas() == [(2.0, "linea 2"), (3.0, "linea 3"), (4.0, "linea 4")])
r.check("anillo: ultimas(n) devuelve las n últimas; n=0 -> []", a.ultimas(2) == [(3.0, "linea 3"), (4.0, "linea 4")] and a.ultimas(0) == [] and len(a.ultimas(99)) == 3)
b = dg.Anillo(10)
b.anotar("uno\ndos\r\n\n   \ntres " + GEMINI)
r.check("anillo: separa líneas, salta las vacías, recorta y REDACTA al entrar: " + str([x for _, x in b.ultimas()]), [x for _, x in b.ultimas()] == ["uno", "dos", "tres «clave»"] and "AIza" not in str(b.ultimas()))
r.check("anillo: capacidad mínima 1 aunque pidan 0 o negativa", len(dg.Anillo(0)._d.maxlen * [1]) == 1 and dg.Anillo(-5)._d.maxlen == 1)
c = dg.Anillo(50)
hilos = [threading.Thread(target=lambda k=k: [c.anotar(f"h{k} l{i}") for i in range(500)]) for k in range(4)]
[h.start() for h in hilos]
[h.join() for h in hilos]
r.check("anillo: 4 hilos x 500 líneas a la vez no rompen nada y respetan la capacidad", len(c.ultimas()) == 50)

destino = io.StringIO()
anillo = dg.Anillo(20)
tee = dg.Tee(destino, anillo)
n = tee.write("hola ")
tee.write("mundo\nsegunda linea\ntercera sin cerrar")
r.check("tee: lo escrito llega intacto al destino (la consola no cambia) y devuelve lo mismo que el destino", destino.getvalue() == "hola mundo\nsegunda linea\ntercera sin cerrar" and n == len("hola "))
r.check("tee: solo guarda líneas COMPLETAS (la 3.ª sigue pendiente): " + str([x for _, x in anillo.ultimas()]), [x for _, x in anillo.ultimas()] == ["hola mundo", "segunda linea"])
tee.write("\n")
r.check("tee: al cerrar la línea, se guarda", [x for _, x in anillo.ultimas()][-1] == "tercera sin cerrar")
tee.write("clave " + GEMINI + "\n")
r.check("tee: una clave impresa en la consola NO entra en el anillo", "AIza" not in str(anillo.ultimas()) and "«clave»" in str(anillo.ultimas()))
tee.write("y" * 5000)
r.check("tee: una 'línea' sin salto de 5000 caracteres no crece sin límite (se vuelca acotada)", len(tee._pendiente) <= dg.Tee.MAX_PENDIENTE and any(len(x) <= dg.MAX_LINEA for _, x in anillo.ultimas()))


class AnilloRoto:
    def anotar(self, _):
        raise RuntimeError("anillo roto")


d2 = io.StringIO()
tr = dg.Tee(d2, AnilloRoto())
try:
    tr.write("linea\n")
    ok = d2.getvalue() == "linea\n"
except Exception:  # noqa: BLE001
    ok = False
r.check("tee: si el anillo falla, la consola sigue funcionando (nunca rompe un print)", ok)
r.check("tee: flush y atributos (encoding...) pasan al flujo original", tee.flush() is None and hasattr(tee, "getvalue") and tee.getvalue() == destino.getvalue())

r.check("describir_orden: acción, material, objetivo y chat recortado", dg.describir_orden({"action": "mine", "material": "iron_ore", "target": "Steve", "chat_message": "Voy a minar"}) == "action=mine material=iron_ore target=Steve chat='Voy a minar'")
r.check("describir_orden: 'cualquiera' y vacíos no se listan; algo que no es dict no rompe", dg.describir_orden({"action": "ninguna", "material": "cualquiera"}) == "action=ninguna" and dg.describir_orden(None) == "orden no válida")
r.check("describir_orden: redacta secretos del chat y acota el chat a 60", "AIza" not in dg.describir_orden({"action": "x", "chat_message": GEMINI}) and len(dg.describir_orden({"action": "x", "chat_message": "z" * 500})) < 120)

r.check("edad_s: segundos desde mtime; None si falta; nunca negativa; bool/str no valen", dg.edad_s(100.0, 90.0) == 10.0 and dg.edad_s(100.0, None) is None and dg.edad_s(100.0, 150.0) == 0.0 and dg.edad_s(1, True) is None and dg.edad_s(1, "x") is None)
r.check("texto_edad: s, min, h y 'no existe'", [dg.texto_edad(x) for x in (None, 5, 89, 90, 3600, 5399, 5400, 20000)] == ["no existe", "hace 5 s", "hace 89 s", "hace 1 min", "hace 60 min", "hace 89 min", "hace 1 h", "hace 5 h"])

lineas = [json.dumps({"rol": "chat", "proveedor": "gemini", "ok": True, "seg": 1.0}), json.dumps({"rol": "chat", "proveedor": "gemini", "ok": True, "seg": 3.0}),
          json.dumps({"rol": "chat", "proveedor": "gemini", "ok": False, "error": "timeout", "seg": 12}), json.dumps({"rol": "internet", "proveedor": "claude", "ok": False, "error": "429"}),
          "esto no es json", "[1,2]", "5", json.dumps({"rol": "x"}), None, json.dumps({"rol": "chat", "proveedor": "gemini", "ok": True, "seg": True})]
tabla = dg.resumen_nube(lineas)
g = tabla[("chat", "gemini")]
r.check("resumen_nube: cuenta ok y fallos por (rol, proveedor), tiempo medio (ignora bool) y tipos de error: " + str(g), g["ok"] == 3 and g["fallo"] == 1 and g["errores"] == {"timeout": 1} and g["seg_medio"] == round((1 + 3 + 12) / 3, 1))
r.check("resumen_nube: un fallo sin tiempo tiene seg_medio None; basura ignorada; entrada None/vacía -> {}", tabla[("internet", "claude")]["seg_medio"] is None and dg.resumen_nube(None) == {} and dg.resumen_nube([]) == {} and ("x", "?") in tabla)
r.check("resumen_nube: solo mira las últimas max_lineas", dg.resumen_nube([json.dumps({"rol": "viejo", "proveedor": "p", "ok": True})] * 5 + [json.dumps({"rol": "nuevo", "proveedor": "p", "ok": True})], max_lineas=1).keys() == {("nuevo", "p")})

mods = {"minecraft": "1.20.1", "mods": [{"id": "create", "version": "0.5.1.f"}, {"id": "mekanism", "version": "10.4.8"}, {"id": "evil$(rm -rf)", "version": "1"}, {"id": 5}, "x", {"id": "sin_version"},
                                         {"id": "raro", "version": "1.0\nmalo"}]}
rm = dg.resumen_mods(mods)
r.check("resumen_mods: total real, ids válidos ordenados con versión, los ids con caracteres raros (inyección) se descartan: " + str(rm), rm["total"] == 7 and rm["ids"] == ["create@0.5.1.f", "mekanism@10.4.8", "raro", "sin_version"] and rm["minecraft"] == "1.20.1")
r.check("resumen_mods: sin datos válidos -> None; tope de ids", dg.resumen_mods(None) is None and dg.resumen_mods({}) is None and dg.resumen_mods({"mods": "x"}) is None
        and len(dg.resumen_mods({"mods": [{"id": f"mod{i}"} for i in range(300)]}, max_ids=60)["ids"]) == 60 and dg.resumen_mods({"mods": [{"id": f"mod{i}"} for i in range(300)]})["total"] == 300)

AHORA = 1_800_000_000.0
datos = {"ahora": AHORA, "config": {"a": True, "b": False, "c": False, "_nota": False, "n": 5, "d": True}, "sensores": {"gps.json": 3.0, "nox_status.json": 400.0, "entities.json": None},
         "hechos": ["Jugador a 5 bloques, vida 18/20.", "Sin hostiles cerca."], "mods": mods, "ordenes": [(AHORA - 5, "action=mine material=iron")],
         "consola": [(AHORA - 9, "[-] No se pudo escribir command.json: X"), (AHORA - 8, "todo bien"), (AHORA - 7, "clave " + GEMINI)],
         "nube": dg.resumen_nube(lineas), "ollama": {"responde": True, "modelo": "qwen3.5:9b", "unico": True}}
texto, meta = dg.generar_informe(datos)
r.check("informe: título y todas las secciones", all(s in texto for s in ("# Diagnóstico de Cobalt", "## Resumen", "## Sensores", "## Lo que ve Cobalt ahora", "## Mods", "## Interruptores apagados",
                                                                          "## Últimas órdenes", "## Nube", "## Consola de Python")))
r.check("informe: Java 'ESCRIBIENDO' porque gps.json tiene 3 s; 2 interruptores apagados (b, c; '_nota' y numéricos no cuentan); Ollama y modelo único", "ESCRIBIENDO" in texto and "- b, c" in texto and "2 apagados" in texto and "qwen3.5:9b (modelo único)" in texto)
r.check("informe: sensores con su edad ('hace 3 s', 'hace 6 min', 'no existe'), mods y órdenes", "gps.json: hace 3 s" in texto and "nox_status.json: hace 6 min" in texto and "entities.json: no existe" in texto and "7 mods cargados" in texto
        and "action=mine material=iron" in texto)
r.check("informe: los errores de la consola se destacan (1 de 3 líneas) y la CLAVE no aparece en ninguna parte del informe", "1 de 3 líneas" in texto and "[-] No se pudo escribir" in texto.split("### Cola completa")[0] and "AIza" not in texto)
r.check("informe: meta con los datos para el chat", meta == {"apagados": 2, "java_vivo": True, "errores": 1, "mods": 7})
t2, m2 = dg.generar_informe({"ahora": AHORA, "sensores": {"gps.json": 400.0}})
r.check("informe: si ningún sensor se escribió en los últimos 30 s, Java figura SIN ACTIVIDAD (y el informe admite que no hay mods)", "SIN ACTIVIDAD" in t2 and m2["java_vivo"] is False and "no ha exportado" in t2 and m2["mods"] is None)
r.check("informe: el umbral de 'Java vivo' es de 30 s (29 s sí, 31 s no) y basta con que UN sensor esté fresco",
        dg.generar_informe({"ahora": AHORA, "sensores": {"a": 29.0}})[1]["java_vivo"] is True and dg.generar_informe({"ahora": AHORA, "sensores": {"a": 31.0}})[1]["java_vivo"] is False
        and dg.generar_informe({"ahora": AHORA, "sensores": {"a": 500.0, "b": 2.0, "c": None}})[1]["java_vivo"] is True)
t3, m3 = dg.generar_informe({})
r.check("informe: con dict vacío o basura no lanza y sigue siendo un informe", "# Diagnóstico de Cobalt" in t3 and m3["java_vivo"] is False and dg.generar_informe(None)[1]["errores"] == 0 and dg.generar_informe("x")[0].startswith("#"))
r.check("informe: los datos que llegan sin redactar (consola/órdenes/hechos) se redactan igualmente al generar", "AIza" not in dg.generar_informe({"consola": [(1.0, GEMINI)], "ordenes": [(1.0, GEMINI)], "hechos": [GEMINI]})[0])

rc = dg.resumen_chat(meta, "diagnostico_x.md")
r.check("resumen_chat: dice el archivo, el estado de Java, los errores y los interruptores: " + rc, rc == "Diagnóstico guardado en diagnostico_x.md: Java responde, 1 error(es) recientes en la consola, 2 interruptores apagados.")
r.check("resumen_chat: sin errores y con Java parado", dg.resumen_chat({"java_vivo": False, "errores": 0, "apagados": 0}, "f.md") == "Diagnóstico guardado en f.md: Java sin actividad reciente, sin errores recientes en la consola, 0 interruptores apagados."
        and "Java sin actividad" in dg.resumen_chat(None, "f.md"))
r.check("resumen_chat pasa el linter de voz y cabe en el chat", not nox_voz.linter_voz(rc) and len(rc) <= nox_voz.MAX_CHAT)

si = ["diagnóstico", "Diagnostico", "haz un diagnóstico", "Cobalt, diagnóstico", "dame un diagnóstico", "hazme el diagnóstico", "diagnóstico completo", "autodiagnóstico", "necesito un diagnóstico por favor",
      "genera un diagnóstico", "¡DIAGNÓSTICO!", "ejecuta diagnóstico", "quiero un diagnóstico completo"]
no = ["", "hola", "diagnóstico de mi granja de Create", "haz un diagnóstico del reactor de Mekanism", "diagnóstico médico", "explícame qué es un diagnóstico", "situación", "diagnostica", "x" * 200, None, 7]
r.check("pide_diagnostico: reconoce las formas naturales: " + str([x for x in si if not dg.pide_diagnostico(x)]), all(dg.pide_diagnostico(x) for x in si))
r.check("pide_diagnostico: NO se activa con preguntas sobre otro tema: " + str([x for x in no if dg.pide_diagnostico(x)]), not any(dg.pide_diagnostico(x) for x in no))
r.check("pide_diagnostico: un mensaje enorme no se procesa", not dg.pide_diagnostico("diagnóstico" + " " * 200) and dg.pide_diagnostico("diagnóstico" + " " * 20))

rng = random.Random(5)
cosas = [None, True, 0, -3, 1e30, float("nan"), "x", "{}", [], {}, [1, 2], (1, "a"), [(1.0, "linea")], {"a": 1}, object(), AHORA]
fallos = []
for _ in range(3000):
    d = {k: rng.choice(cosas) for k in ("ahora", "config", "sensores", "hechos", "mods", "ordenes", "consola", "nube", "ollama") if rng.random() < 0.8}
    try:
        tx, mt = dg.generar_informe(d)
        assert isinstance(tx, str) and isinstance(mt, dict) and isinstance(dg.resumen_chat(mt, "f.md"), str)
        dg.resumen_nube(rng.choice(cosas) if rng.random() < 0.5 else [rng.choice(cosas)])
        dg.resumen_mods(rng.choice(cosas))
        dg.describir_orden(rng.choice(cosas))
        dg.pide_diagnostico(rng.choice(cosas))
    except Exception as ex:  # noqa: BLE001
        fallos.append(repr(ex))
r.check("fuzz (3000 combinaciones de datos basura): nunca lanza: " + str(fallos[:2]), not fallos)

r.check("un aviso del radar de combate no cuenta como error", dg.es_linea_de_error("04:44:18 🚨 [Reflejo Radar] 1 amenaza(s) de 2, 0 a menos de 5m") is False)
r.check("un error de verdad sí (Traceback / [-] / Error)", dg.es_linea_de_error("Traceback (most recent call last):") and dg.es_linea_de_error("[-] No se pudo escribir command.json") and dg.es_linea_de_error("ValueError: x"))
r.check("otro 🚨 que no es del radar sigue contando (fallo grave del sistema)", dg.es_linea_de_error("🚨 Java dejó de responder"))

r.terminar()
