"""H2 (adaptador en cerebro.py): el prompt del chat recibe lo relevante de lo estudiado y de las lecciones; lo estudiado se guarda sin negativas ni repetidos y sin"""
import io
import json
import os
import tempfile
import time

from _cargar import Resultados, cargar_cerebro

ns = cargar_cerebro()
r = Resultados()
tmp = tempfile.mkdtemp()
for var, nombre in [("CONFIG_FILE", "cobalt_config.json"), ("MOD_KNOWLEDGE_FILE", "conocimiento_mods.json"), ("ARCHIVO_EXPERIENCIA", "experiencia_combate.json"),
                    ("STATUS_FILE", "nox_status.json")]:
    ns[var] = os.path.join(tmp, nombre)
ns["registrar_mensaje_disco_python"] = lambda *a, **k: None
nm = ns["nox_memoria"]

MEKANISM = "El reactor de fisión de Mekanism necesita combustible, refrigerante y una carcasa de acero multibloque para funcionar sin sobrecalentarse."
ENDER = "Los conduits de Ender IO son el sistema de transporte central, utilizados para items, energía, líquidos y señales de redstone."
NEGATIVA = "Lo siento, pero no puedo proporcionar un resumen sobre un modo de Minecraft sin acceso a internet. El texto que me proporcionaste solo indica que no hay conexión."


def config(**c):
    io.open(ns["CONFIG_FILE"], "w", encoding="utf-8").write(json.dumps(c))
    ns["_CONFIG_CACHE"]["t"] = 0.0


def escribir_conocimiento(d):
    io.open(ns["MOD_KNOWLEDGE_FILE"], "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False))
    os_utime_futuro()


def os_utime_futuro():
    t = time.time() + os_utime_futuro.n
    os_utime_futuro.n += 2
    os.utime(ns["MOD_KNOWLEDGE_FILE"], (t, t))


os_utime_futuro.n = 1


def prompt(consulta="", **kw):
    return ns["generar_prompt_maestro"](kw.get("vision", "visión"), "terreno", "feedback", "", "", "tech", "waypoints", consulta=consulta)


base = {"2026-09-01 10:00": {"tema": "Mekanism mod fission reactor setup guide", "resumen": MEKANISM},
        "2026-09-02 10:00": {"tema": "Ender IO conduits and power distribution setup", "resumen": ENDER},
        "2026-09-03 10:00": {"tema": "Mekanism mod energy cables recipe guide", "resumen": NEGATIVA}}
config()
escribir_conocimiento(base)
ns["_CACHE_CONOCIMIENTO"].update({"mtime": None, "datos": {}})

r.check("cargar_conocimiento_estudio lee el archivo", ns["cargar_conocimiento_estudio"]() == base)
escribir_conocimiento({"x": {"tema": "t", "resumen": "r"}})
r.check("y detecta que el archivo cambió (caché por fecha de modificación)", list(ns["cargar_conocimiento_estudio"]()) == ["x"])
io.open(ns["MOD_KNOWLEDGE_FILE"], "w", encoding="utf-8").write("{roto")
os_utime_futuro()
r.check("archivo roto -> {} sin lanzar", ns["cargar_conocimiento_estudio"]() == {})
io.open(ns["MOD_KNOWLEDGE_FILE"], "w", encoding="utf-8").write("[1, 2]")
os_utime_futuro()
r.check("archivo que no es un diccionario -> {}", ns["cargar_conocimiento_estudio"]() == {})
os.remove(ns["MOD_KNOWLEDGE_FILE"])
r.check("archivo ausente -> {}", ns["cargar_conocimiento_estudio"]() == {})
escribir_conocimiento(base)

sin = prompt("")
con = prompt("cómo funciona el reactor de fisión de Mekanism")
r.check("consulta sobre un mod que Cobalt estudió: el prompt incluye 'LO QUE HAS APRENDIDO' con el resumen", "LO QUE HAS APRENDIDO" in con and "carcasa de acero multibloque" in con)
r.check("el bloque va después de la memoria táctica y antes de las reglas", con.index("MEMORIA Y EXPERIENCIA TÁCTICA") < con.index("LO QUE HAS APRENDIDO") < con.index("REGLAS ESTRICTAS"))
r.check("la NEGATIVA guardada ('Lo siento... sin acceso a internet') NUNCA llega al prompt", "Lo siento" not in con and "sin acceso a internet" not in con)
r.check("consulta sin relación (mina hierro): el prompt queda EXACTAMENTE igual que sin consulta (cero ruido)", prompt("mina hierro por favor") == sin and "LO QUE HAS APRENDIDO" not in sin)
r.check("charla tampoco mete nada", prompt("hola cobalt, ¿cómo estás?") == sin)
r.check("otro tema: conduits -> Ender IO y NO Mekanism", "Ender IO" in prompt("para qué sirven los conduits de Ender IO") and "multibloque" not in prompt("para qué sirven los conduits de Ender IO"))
config(memoria_relevante=False)
r.check("memoria_relevante=false: nunca añade el bloque (comportamiento anterior)", prompt("cómo funciona el reactor de fisión de Mekanism") == sin)
config()
escribir_conocimiento({"2026-09-03 10:00": {"tema": "Mekanism cables", "resumen": NEGATIVA}})
r.check("si SOLO hay negativas guardadas para ese tema, no se añade nada", prompt("cables de Mekanism") == sin)
escribir_conocimiento(base)

relleno = " Detalles: " + "generadores, turbinas de vapor, cables de alta tensión y almacenes de energía conectados en serie. " * 5
enorme = {f"2026-09-{i % 28 + 1:02d} {i // 28:02d}:00": {"tema": f"Mod{i}x reactor guide", "resumen": f"El reactor de fisión del mod mod{i}x necesita combustible y refrigerante." + relleno} for i in range(60)}
escribir_conocimiento(enorme)
config(ollama_num_ctx=4096)
largo = ns["generar_prompt_maestro"]("v" * 8000, "t" * 3000, "f" * 8000, "w" * 3000, "", "x" * 5000, "wp" * 3000, consulta="cómo funciona el reactor del mod7x")
r.check(f"con muchísimo conocimiento y campos enormes el prompt sigue dentro del presupuesto ({len(largo)} <= {ns['presupuesto_prompt_chars']()})", len(largo) <= ns["presupuesto_prompt_chars"]())
bloque = largo[largo.find("LO QUE HAS APRENDIDO"):largo.find("REGLAS ESTRICTAS")] if "LO QUE HAS APRENDIDO" in largo else ""
r.check(f"y entra SOLO el recuerdo del mod pedido (mod7x), recortado (bloque de {len(bloque)} caracteres)", "mod7x" in bloque and bloque.count("- [") == 1 and "mod8x" not in bloque and len(bloque) < 800)
r.check("los resúmenes largos se recortan a 300 caracteres con '...'", "..." in bloque)
escribir_conocimiento(base)

lecciones = ["Ante un creeper aléjate cuanto antes y ataca desde lejos con plasma; no lo dejes acercarse a la base ni al jugador."] + \
            [f"Lección número {i}: guarda el material sobrante en el cofre de la zona {i} y apunta las coordenadas del punto de recogida para volver después." for i in range(60)]
io.open(ns["ARCHIVO_EXPERIENCIA"], "w", encoding="utf-8").write(json.dumps(lecciones, ensure_ascii=False))
config(ollama_num_ctx=4096)
antes = ns["generar_prompt_maestro"]("v", "t", "f", "", "", "x", "w", consulta="")
despues = ns["generar_prompt_maestro"]("v", "t", "f", "", "", "x", "w", consulta="hay un creeper cerca de la base")
r.check("SIN consulta, la lección más antigua (creeper) se pierde por el recorte de recencia (comportamiento anterior)", "creeper" not in antes)
r.check("CON consulta relevante, la lección del creeper SÍ entra aunque sea la más antigua", "Ante un creeper aléjate" in despues)
r.check("y las lecciones irrelevantes ceden su sitio (siguen dentro del presupuesto)", len(despues) <= ns["presupuesto_prompt_chars"]())
config()

if os.path.exists(ns["MOD_KNOWLEDGE_FILE"]):
    os.remove(ns["MOD_KNOWLEDGE_FILE"])
r.check("una negativa se descarta y NO se crea el archivo", ns["registrar_estudio"]("Mekanism", NEGATIVA) == "descartado" and not os.path.exists(ns["MOD_KNOWLEDGE_FILE"]))
r.check("un resumen bueno se guarda", ns["registrar_estudio"]("Mekanism reactor", MEKANISM) == "guardado" and len(json.load(open(ns["MOD_KNOWLEDGE_FILE"], encoding="utf-8"))) == 1)
r.check("el mismo tema con un resumen casi igual REEMPLAZA (no acumula repetidos)", ns["registrar_estudio"]("Mekanism reactor", MEKANISM + " Además necesita un puerto.") == "reemplazado"
        and len(json.load(open(ns["MOD_KNOWLEDGE_FILE"], encoding="utf-8"))) == 1)
r.check("otro tema se añade", ns["registrar_estudio"]("Ender IO", ENDER) == "guardado" and len(json.load(open(ns["MOD_KNOWLEDGE_FILE"], encoding="utf-8"))) == 2)
r.check("la escritura es atómica: no queda ningún .tmp", not os.path.exists(ns["MOD_KNOWLEDGE_FILE"] + ".tmp"))
io.open(ns["MOD_KNOWLEDGE_FILE"], "w", encoding="utf-8").write("{esto se corrompió a medias")
r.check("un archivo ROTO no se pisa en silencio: se aparta como .corrupto y se empieza uno nuevo", ns["registrar_estudio"]("Ender IO", ENDER) == "guardado"
        and open(ns["MOD_KNOWLEDGE_FILE"] + ".corrupto", encoding="utf-8").read().startswith("{esto se corrompió") and len(json.load(open(ns["MOD_KNOWLEDGE_FILE"], encoding="utf-8"))) == 1)
config(memoria_consolidar=False)
os.remove(ns["MOD_KNOWLEDGE_FILE"])
ns["registrar_estudio"]("Mekanism", NEGATIVA)
r.check("memoria_consolidar=false: comportamiento anterior (guarda hasta la negativa)", len(json.load(open(ns["MOD_KNOWLEDGE_FILE"], encoding="utf-8"))) == 1)
config()

if os.path.exists(ns["ARCHIVO_EXPERIENCIA"]):
    os.remove(ns["ARCHIVO_EXPERIENCIA"])
ns["aprender_leccion"]("Ante un creeper aléjate y ataca desde lejos.")
ns["aprender_leccion"]("Ante un creeper, aléjate y ataca desde lejos siempre.")
ns["aprender_leccion"]("Guarda el hierro en el cofre de la base.")
ns["aprender_leccion"]("Ante un creeper aléjate y ataca desde lejos.")
r.check("aprender_leccion no duplica ni las iguales ni las casi iguales (quedan 2)", len(json.load(open(ns["ARCHIVO_EXPERIENCIA"], encoding="utf-8"))) == 2)
config(memoria_consolidar=False)
ns["aprender_leccion"]("Ante un creeper, aléjate y ataca desde lejos siempre.")
r.check("memoria_consolidar=false: solo evita las idénticas (la casi igual sí entra)", len(json.load(open(ns["ARCHIVO_EXPERIENCIA"], encoding="utf-8"))) == 3)
config()

enviados = []
ns["escribir_comando"] = lambda ordenes: enviados.extend(o.get("chat_message") for o in ordenes)
ns["buscar_en_internet"] = lambda q: "fragmentos de prueba"
io.open(ns["STATUS_FILE"], "w", encoding="utf-8").write(json.dumps({"is_deployed": True, "is_dead": False, "updated_ms": time.time() * 1000}))
if os.path.exists(ns["MOD_KNOWLEDGE_FILE"]):
    os.remove(ns["MOD_KNOWLEDGE_FILE"])
ns["consultar_gemini_o_fallback"] = lambda p, timeout_s=8.0, rol=None: NEGATIVA
ns["procesar_mensaje_async"]("Steve", "estudia sobre el reactor de fisión de Mekanism")
r.check("estudio explícito con una NEGATIVA del modelo: NO se guarda y Cobalt dice que no encontró detalles claros (antes le repetía la disculpa como si fuera un dato): " + repr(enviados),
        not os.path.exists(ns["MOD_KNOWLEDGE_FILE"]) and enviados == ["Busqué en internet pero no encontré detalles claros."])
enviados.clear()
ns["consultar_gemini_o_fallback"] = lambda p, timeout_s=8.0, rol=None: MEKANISM
ns["procesar_mensaje_async"]("Steve", "estudia sobre el reactor de fisión de Mekanism")
r.check("estudio explícito con un buen resumen: se guarda y se lo cuenta", len(json.load(open(ns["MOD_KNOWLEDGE_FILE"], encoding="utf-8"))) == 1 and enviados and enviados[0].startswith("Estudié sobre ello: El reactor de fisión"))

os.remove(ns["MOD_KNOWLEDGE_FILE"])
ns["random"] = type("R", (), {"choice": staticmethod(lambda seq: "Mekanism mod fission reactor setup guide"), "randrange": staticmethod(lambda *a: 0),
                             "random": staticmethod(lambda: 0.5), "uniform": staticmethod(lambda a, b: a)})
ns["consultar_gemini_o_fallback"] = lambda p, timeout_s=8.0, rol=None: NEGATIVA
ns["estudiar_mods_afk"]()
r.check("estudio autónomo con una negativa: no guarda nada", not os.path.exists(ns["MOD_KNOWLEDGE_FILE"]))
ns["consultar_gemini_o_fallback"] = lambda p, timeout_s=8.0, rol=None: MEKANISM
ns["estudiar_mods_afk"]()
ns["estudiar_mods_afk"]()
guardado = json.load(open(ns["MOD_KNOWLEDGE_FILE"], encoding="utf-8"))
r.check("estudio autónomo repetido con el mismo resumen: UNA sola entrada (antes se acumulaban 14-23 por tema)", len(guardado) == 1 and list(guardado.values())[0]["tema"] == "Mekanism mod fission reactor setup guide")

escribir_conocimiento({"2026-09-01 10:00": {"tema": "Mekanism mod fission reactor setup guide", "resumen": MEKANISM}})
prompts = []
ns["consultar_ollama"] = lambda modelo, p: (prompts.append(p), "NO" if "requiere internet" in p else '[{"action": "ninguna", "chat_message": "ok"}]')[1]
ns["procesar_mensaje_async"]("Steve", "explícame cómo funciona el reactor de fisión de Mekanism")
principal = [p for p in prompts if "REGLAS ESTRICTAS" in p]
r.check("en el chat, la pregunta sobre un mod estudiado hace que el modelo local RECIBA lo aprendido", principal and "LO QUE HAS APRENDIDO" in principal[-1] and "carcasa de acero multibloque" in principal[-1])
prompts.clear()
ns["procesar_mensaje_async"]("Steve", "mina hierro por favor")
principal = [p for p in prompts if "REGLAS ESTRICTAS" in p]
r.check("y una orden normal no recibe ese bloque", principal and "LO QUE HAS APRENDIDO" not in principal[-1])

r.terminar()
