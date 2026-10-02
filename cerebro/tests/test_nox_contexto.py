"""Presupuesto de contexto del LLM y detector de bucles: piezas puras + extremo a extremo con el prompt real de cerebro.py."""
import io
import json
import os
import sys
import tempfile

from _cargar import RAIZ, Resultados, cargar_cerebro

sys.path.insert(0, os.path.join(RAIZ, "cerebro"))
import nox_contexto as nc  # noqa: E402

r = Resultados()

r.check("limitar_texto: un texto corto no se toca; None -> ''", nc.limitar_texto("hola", 50) == "hola" and nc.limitar_texto(None, 5) == "")
t = nc.limitar_texto("uno dos tres cuatro cinco seis siete", 20)
r.check("limitar_texto: respeta el máximo (marca incluida), corta en límite de palabra (nunca 'cuat…') y termina en '…'", t == "uno dos tres…" and len(t) <= 20)
r.check("limitar_texto: máximo 0 o negativo -> ''; máximo 1 -> solo la marca", nc.limitar_texto("hola", 0) == "" and nc.limitar_texto("hola", -3) == "" and nc.limitar_texto("hola mundo", 1) == "…")
r.check("limitar_texto: NUNCA supera el máximo, para cualquier longitud", all(len(nc.limitar_texto("palabra " * 50, n)) <= n for n in range(0, 120)))
r.check("limitar_texto: prefiere cortar en un separador de campo ' | '", nc.limitar_texto("'a': X=1 | 'b': X=2 | 'c': X=3", 22) == "'a': X=1 | 'b': X=2…")

pesos = {"a": 1.0, "b": 1.0, "c": 2.0}
rep = nc.repartir({"a": 10, "b": 5000, "c": 5000}, pesos, 1000)
r.check("repartir: el campo pequeño se queda ENTERO y su sobra se reasigna a los grandes", rep["a"] == 10 and rep["b"] + rep["c"] <= 990 and rep["b"] + rep["c"] >= 985)
r.check("repartir: entre dos grandes, la cuota es proporcional a su peso (1:2)", abs(rep["c"] - 2 * rep["b"]) <= 3)
r.check("repartir: la suma NUNCA supera el total", sum(nc.repartir({"a": 900, "b": 900, "c": 900}, pesos, 1000).values()) <= 1000)
r.check("repartir: si todo cabe, nadie se recorta", nc.repartir({"a": 10, "b": 20, "c": 30}, pesos, 1000) == {"a": 10, "b": 20, "c": 30})
r.check("repartir: total 0 o negativo -> todos 0; campos vacíos -> 0", nc.repartir({"a": 100, "b": 0}, {"a": 1, "b": 1}, 0) == {"a": 0, "b": 0} and nc.repartir({"a": 100}, {"a": 1}, -50) == {"a": 0})
r.check("repartir: un campo sin peso declarado usa peso 1 (no revienta)", sum(nc.repartir({"x": 500, "y": 500}, {}, 400).values()) <= 400)

lecs = [f"Lección número {i}: no te acerques a los creepers sin cobertura." for i in range(200)]
sel = nc.recortar_lecciones(lecs, 500)
r.check("lecciones: entran las MÁS RECIENTES, en orden cronológico, y caben en el presupuesto", sel[-1] == lecs[-1] and sel == lecs[-len(sel):] and len(" ".join(sel)) <= 500 and 3 <= len(sel) <= 12)
una = ["Si estás en el agua cambia a 'swim' para nadar y mantenerte a flote."]
r.check("lecciones: UNA lección que cabe justo en su cuota entra (antes se descartaba: 'memoria 107->0')", nc.recortar_lecciones(una, len(una[0])) == una)
tres = ["Primera lección de prueba.", "Segunda lección de prueba.", "Tercera lección de prueba."]
r.check("lecciones: tres lecciones que caben justo en len(' '.join) entran las tres", nc.recortar_lecciones(tres, len(" ".join(tres))) == tres)
r.check("lecciones: con un carácter menos se pierde solo la MÁS ANTIGUA", nc.recortar_lecciones(tres, len(" ".join(tres)) - 1) == tres[1:])
r.check("lecciones: nunca se pasa del presupuesto (el largo de ' '.join) para ningún tope entre 0 y 300",
        all(len(" ".join(nc.recortar_lecciones(lecs, m))) <= m for m in range(0, 300, 7)))
campos_l, informe_l = nc.aplicar_presupuesto({"memoria": " ".join(una)}, {"memoria": 1.0}, 5000, lecciones=una)
r.check("aplicar_presupuesto: si el campo de memoria cabe entero, las lecciones NO se recortan (informe vacío)", campos_l["memoria"] == una[0] and "memoria" not in informe_l)
r.check("lecciones: respeta max_n y se salta las repetidas", len(nc.recortar_lecciones(lecs, 100000, max_n=5)) == 5 and nc.recortar_lecciones(["a", "A", "a", "b"], 100) == ["a", "b"])
r.check("lecciones: una lección enorme se acota a max_cada", all(len(x) <= 280 for x in nc.recortar_lecciones(["x" * 5000, "y" * 5000], 10000)))
r.check("lecciones: vacías, None o basura no rompen", nc.recortar_lecciones([], 100) == [] and nc.recortar_lecciones(None, 100) == [] and nc.recortar_lecciones(["", "  ", None, 5], 100) == ["5"])
r.check("lecciones: presupuesto 0 -> ninguna", nc.recortar_lecciones(lecs, 0) == [])

wps = {"base": {"x": 100, "y": 64, "z": 100}, "mina": {"x": 5000, "y": 12, "z": 5000}, "granja": {"x": 110, "y": 64, "z": 95},
       "torre": {"x": 130, "y": 70, "z": 100}, "nether_hub": {"x": 10, "y": 60, "z": 10, "dimension": "minecraft:the_nether"},
       "roto": {"x": "1"}, "basura": 5}
res = nc.resumir_waypoints(wps, (108.0, 64.0, 98.0), "minecraft:overworld", max_n=3)
r.check("waypoints: 'base' primero y luego los más cercanos (granja, torre); los lejanos y de otra dimensión, fuera", res.index("'base'") < res.index("'granja'") < res.index("'torre'") and "'mina'" not in res and "nether_hub" not in res)
r.check("waypoints: informa de cuántos quedan fuera y descarta los inválidos", "(+2 más guardados" in res and "roto" not in res and "basura" not in res)
r.check("waypoints: 'base' entra AUNQUE esté lejos", "'base'" in nc.resumir_waypoints(wps, (9000.0, 64.0, 9000.0), "minecraft:overworld", max_n=1))
r.check("waypoints: sin posición conocida sigue funcionando (base y luego por nombre)", nc.resumir_waypoints(wps, None, None, max_n=2).startswith("'base'"))
grandes = {f"lugar_{i}": {"x": i, "y": 64, "z": i} for i in range(60)}
res = nc.resumir_waypoints(grandes, (0.0, 64.0, 0.0), None, max_n=60, max_chars=300)
r.check("waypoints: con 60 waypoints y 300 caracteres de tope, cabe (por entradas completas) e indica los omitidos", len(res) <= 300 + 60 and "más guardados" in res and res.count("'lugar_") >= 3)
r.check("waypoints: sin ninguno válido -> ''; dimensión incluida cuando existe", nc.resumir_waypoints({}, None, None) == "" and nc.resumir_waypoints(None, None, None) == ""
        and "[the_nether]" in nc.resumir_waypoints({"n": {"x": 1, "y": 2, "z": 3, "dimension": "minecraft:the_nether"}}, None, None))

campos = {"memoria": "", "vision": "v" * 4000, "tech": "t" * 4000, "terreno": "Terreno seguro."}
salida, informe = nc.aplicar_presupuesto(campos, {"memoria": 0.2, "vision": 0.2, "tech": 0.1, "terreno": 0.05}, 1200, lecciones=lecs)
r.check("presupuesto: el total no supera lo permitido, lo corto queda intacto y se informa de lo recortado",
        sum(len(v) for v in salida.values()) <= 1200 and salida["terreno"] == "Terreno seguro." and "vision" in informe and "tech" in informe and "terreno" not in informe)
r.check("presupuesto: la memoria se rehace con las lecciones más recientes (no cortada a mitad de frase)", salida["memoria"].endswith(lecs[-1]))

def acc(a="mine", **kw):
    o = {"action": a, "material": "iron_ore", "amount": 8}
    o.update(kw)
    return o


d = nc.DetectorBucles(maximo=4, ventana_s=60.0, pausa_s=30.0)
t0 = 1000.0
r.check("bucles: 4 repeticiones en 60 s (varias respuestas) pasan", all(len(d.revisar([acc()], t0 + i * 10)[0]) == 1 for i in range(4)))
perm, av = d.revisar([acc()], t0 + 41.0)
r.check("bucles: la 5.ª se BLOQUEA y avisa una sola vez (qué repite, cuántas veces, cuánto para)", perm == [] and len(av) == 1 and "Llevo 4 veces" in av[0]["chat_message"] and "mine" in av[0]["chat_message"] and "30 s" in av[0]["chat_message"])
r.check("bucles: durante la pausa se descarta en SILENCIO (no spamea avisos)", d.revisar([acc()], t0 + 50.0) == ([], []) and d.revisar([acc()], t0 + 60.0) == ([], []))
perm, av = d.revisar([acc()], t0 + 75.0)
r.check("bucles: terminada la pausa (30 s) vuelve a permitirse", len(perm) == 1 and av == [])
r.check("bucles: otra orden distinta NUNCA se ve afectada", len(d.revisar([acc(material="coal_ore")], t0 + 45.0)[0]) == 1 and len(d.revisar([acc("go_to", x=1, y=2, z=3)], t0 + 46.0)[0]) == 1)
d2 = nc.DetectorBucles(maximo=4, ventana_s=60.0)
for i in range(4):
    d2.revisar([acc()], i * 20.0)  # 0, 20, 40, 60: la primera sale de la ventana antes de la 5.ª
r.check("bucles: las repeticiones LENTAS (fuera de la ventana de 60 s) no cuentan", len(d2.revisar([acc()], 100.0)[0]) == 1)
d3 = nc.DetectorBucles()
perm, av = d3.revisar([acc() for _ in range(20)], 0.0)
r.check("bucles: una respuesta con 20 órdenes idénticas se recorta a 3 y avisa", len(perm) == 3 and len(av) == 1 and "17 órdenes repetidas" in av[0]["chat_message"])
perm, av = nc.DetectorBucles().revisar([acc(material=f"m{i}") for i in range(20)], 0.0)
r.check("bucles: una respuesta con 20 órdenes DISTINTAS se recorta a 8 (tope por respuesta)", len(perm) == 8 and len(av) == 1)
perm, av = nc.DetectorBucles().revisar([acc(), acc("go_to", x=1), acc(), acc("go_to", x=1)], 0.0)
r.check("bucles: repeticiones NO consecutivas (mine, go_to, mine, go_to) son un plan legítimo", len(perm) == 4 and av == [])
d4 = nc.DetectorBucles(maximo=2)
for i in range(3):
    o_ = d4.revisar([{"action": "ninguna", "chat_message": "¿Qué dices?"}], float(i))
r.check("bucles: el mismo mensaje de chat repetido también se detecta ('¿Qué dices?' en bucle)", o_[0] == [] and len(o_[1]) == 1 and "mensaje" in o_[1][0]["chat_message"])
r.check("bucles: dos mensajes de chat DISTINTOS no se confunden", len(nc.DetectorBucles(maximo=1).revisar([{"action": "ninguna", "chat_message": "a"}, {"action": "ninguna", "chat_message": "b"}], 0.0)[0]) == 2)
d5 = nc.DetectorBucles(maximo=1)
for _ in range(5):
    perm, av = d5.revisar([{"action": "halt_all"}, {"action": "stop"}, {"action": "flush"}, {"action": "resume"}, {"action": "recall_drones"}], 0.0)
r.check("bucles: las órdenes de SEGURIDAD (halt_all, stop, flush, resume, recall_drones) jamás se filtran, por muchas veces que se repitan", len(perm) == 5 and av == [])
r.check("bucles: entradas raras (None, str, vacío) no rompen", nc.DetectorBucles().revisar(None, 0.0) == ([], []) and nc.DetectorBucles().revisar(["x", None, 5, {}], 0.0) == ([{}], []))
d6 = nc.DetectorBucles()
d6.configurar(maximo=1, ventana_s=10, pausa_s=5)
r.check("bucles: configurar() cambia los límites (con maximo=1 la 2.ª ya se bloquea)", len(d6.revisar([acc()], 0.0)[0]) == 1 and d6.revisar([acc()], 1.0)[0] == [] and d6.bloqueos_totales == 1)

ns = cargar_cerebro()
tmp = tempfile.mkdtemp()
ns["CONFIG_FILE"] = os.path.join(tmp, "cobalt_config.json")
ns["WAYPOINTS_FILE"] = os.path.join(tmp, "waypoints.json")
ns["GPS_FILE"] = os.path.join(tmp, "gps.json")


def config(**claves):
    io.open(ns["CONFIG_FILE"], "w", encoding="utf-8").write(json.dumps(claves))
    ns["_CONFIG_CACHE"]["t"] = 0.0


config()
ns["cargar_experiencia"] = lambda: [f"Lección {i}: " + "evita el fuego enemigo y no te quedes sin comida. " * 3 for i in range(500)]
gigante = "Z" * 80000
presupuesto = ns["presupuesto_prompt_chars"]()
prompt = ns["generar_prompt_maestro"]("V" * 30000, "T" * 5000, "F" * 40000, gigante, "A" * 9000, gigante, "W" * 30000)
r.check(f"prompt real: con lecciones/radar/datos/web GIGANTES cabe en la ventana (presupuesto {presupuesto} chars, con {ns['RESERVA_MENSAJE_CHARS']} de reserva para el mensaje)",
        len(prompt) + ns["RESERVA_MENSAJE_CHARS"] <= presupuesto + 300)
r.check("prompt real: las REGLAS y las ACCIONES PERMITIDAS siguen intactas (nunca se recortan)", "REGLAS ESTRICTAS DE PENSAMIENTO" in prompt and "VALORES DE ACCIÓN PERMITIDOS" in prompt
        and "'deploy_drones'" in prompt and "'harvest'" in prompt and "FILTRO DE BASURA" in prompt and prompt.count("REGLAS ESTRICTAS") == 1)
r.check("prompt real: la lección MÁS RECIENTE está y las antiguas no", "Lección 499:" in prompt and "Lección 0:" not in prompt)
config(presupuesto_contexto=False)
prompt_sin = ns["generar_prompt_maestro"]("V" * 30000, "T" * 5000, "F" * 40000, gigante, "A" * 9000, gigante, "W" * 30000)
r.check("prompt real: con presupuesto_contexto=false se comporta como antes (sin tope: >150 000 chars)", len(prompt_sin) > 150000)
config()
p_chico = ns["generar_prompt_maestro"]("Visión: nada", "Terreno seguro.", "Estado bien", "", "", "Sin datos técnicos.", "")
r.check("prompt real: un caso NORMAL (campos pequeños) no pierde nada de sus datos", "Visión: nada" in p_chico and "Estado bien" in p_chico and "Sin datos técnicos." in p_chico)
config(ollama_num_ctx=8192)
r.check("presupuesto: escala con ollama_num_ctx (8192 da más caracteres que 4096)", ns["presupuesto_prompt_chars"]() > presupuesto and ns["presupuesto_prompt_chars"]() == int((8192 - 500 - 300) * 3.0))
config(ollama_num_ctx=100)
r.check("presupuesto: una ventana absurda (100) no deja un presupuesto negativo (mínimo 1500 tokens)", ns["presupuesto_prompt_chars"]() == int(1500 * 3.0))
config()

# waypoints para el prompt (con un archivo real de 60 lugares)
io.open(ns["WAYPOINTS_FILE"], "w", encoding="utf-8").write(json.dumps({**{f"lugar_{i}": {"x": i * 10, "y": 64, "z": i * 10} for i in range(60)}, "base": {"x": 5000, "y": 64, "z": 5000}}))
io.open(ns["GPS_FILE"], "w", encoding="utf-8").write(json.dumps({"x": 0, "y": 64, "z": 0, "dimension": "minecraft:overworld"}))
wp = ns["waypoints_para_prompt"]()
r.check("waypoints_para_prompt: con 61 lugares da la base + los más cercanos (<= 8) y dice cuántos faltan", "'base'" in wp and "'lugar_0'" in wp and wp.count("'") <= 2 * 8 + 4 and "más guardados" in wp and len(wp) < 1000)
config(presupuesto_contexto=False)
r.check("waypoints_para_prompt: con presupuesto apagado devuelve la lista COMPLETA de siempre", ns["waypoints_para_prompt"]().count("'lugar_") == 60)
config()
io.open(ns["WAYPOINTS_FILE"], "w", encoding="utf-8").write("{corrupto")
r.check("waypoints_para_prompt: archivo corrupto -> aviso, sin tocarlo", "ilegible" in ns["waypoints_para_prompt"]() and io.open(ns["WAYPOINTS_FILE"], encoding="utf-8").read() == "{corrupto")

# consultar_ollama: num_ctx explícito
capturas = []


class _Resp:
    status_code = 200

    def json(self):
        return {"response": "[]"}


ns["requests"].post = lambda url, json=None, timeout=None: capturas.append(json) or _Resp()
ns["consultar_ollama"]("modelo", "hola")
r.check("consultar_ollama: envía num_ctx=4096 y num_predict=500 explícitos", capturas[-1]["options"]["num_ctx"] == 4096 and capturas[-1]["options"]["num_predict"] == 500)
config(presupuesto_contexto=False)
ns["consultar_ollama"]("modelo", "hola")
r.check("consultar_ollama: con presupuesto apagado NO manda num_ctx (Ollama decide como antes)", "num_ctx" not in capturas[-1]["options"])
config()

# filtrar_bucles a través de cerebro.py
ns["registrar_mensaje_disco_python"] = lambda *a, **k: None
lote = [acc() for _ in range(10)]
salida = ns["filtrar_bucles"](lote, 5000.0)
r.check("filtrar_bucles: 10 órdenes idénticas -> 3 + un aviso al jugador", len([x for x in salida if x["action"] == "mine"]) == 3 and any("repetidas" in x.get("chat_message", "") for x in salida))
config(detector_bucles=False)
r.check("filtrar_bucles: con detector_bucles=false devuelve la lista intacta", ns["filtrar_bucles"]([acc() for _ in range(10)], 6000.0) and len(ns["filtrar_bucles"]([acc() for _ in range(10)], 6000.0)) == 10)
config()
ns["DETECTOR_BUCLES"].__init__()
ns["filtrar_bucles"]([{"action": "halt_all"}] * 30, 7000.0)
r.check("filtrar_bucles: 30 'halt_all' seguidos pasan todos", len(ns["filtrar_bucles"]([{"action": "halt_all"}] * 30, 7001.0)) == 30)

r.terminar()
