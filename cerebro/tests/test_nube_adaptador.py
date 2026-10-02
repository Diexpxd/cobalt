"""Bloques Q1-Q3 (adaptador en cerebro.py): enrutador de la nube, modelo local unico, plazos, plantillas de plano y biblioteca."""
import io
import json
import os
import re
import tempfile
import time
import types as pytypes

import requests as requests_real

from _cargar import Resultados, cargar_cerebro

ns = cargar_cerebro()
r = Resultados()
tmp = tempfile.mkdtemp()
for var, nombre in [("CONFIG_FILE", "cobalt_config.json"), ("NUBE_GASTO_FILE", "nube_gasto.json"), ("NUBE_REGISTRO_FILE", "nube_registro.jsonl"),
                    ("BIBLIOTECA_ESTADO_FILE", "biblioteca_planos.json"), ("STATUS_FILE", "nox_status.json"), ("COMMAND_FILE", "command.json")]:
    ns[var] = os.path.join(tmp, nombre)
ns["BLUEPRINTS_DIR"] = os.path.join(tmp, "blueprints")
ns["_leer_variable_usuario_windows"] = lambda nombre: ""  # nunca leer el registro real de Windows en las pruebas
ns["subprocess"] = pytypes.SimpleNamespace(run=lambda *a, **k: (_ for _ in ()).throw(AssertionError("una prueba intentó ejecutar un programa de verdad")),
                                           TimeoutExpired=__import__("subprocess").TimeoutExpired, CREATE_NO_WINDOW=0x08000000, Popen=None, DEVNULL=None,
                                           CREATE_NEW_PROCESS_GROUP=0)
ns["registrar_mensaje_disco_python"] = lambda *a, **k: None
nn = ns["nox_nube"]


def config(**claves):
    io.open(ns["CONFIG_FILE"], "w", encoding="utf-8").write(json.dumps(claves))
    ns["_CONFIG_CACHE"]["t"] = 0.0


def reiniciar(**claves):
    config(**claves)
    ns["_ENRUTADOR"]["obj"] = None
    ns["_ROTOR_GEMINI"]["obj"] = None
    ns["_ESTADO_BIBLIOTECA"]["obj"] = None
    ns["_UNICO_DISPONIBLE"].update({"t": -1e9, "ok": False, "avisado": False})
    for f in (ns["NUBE_GASTO_FILE"], ns["NUBE_REGISTRO_FILE"], ns["BIBLIOTECA_ESTADO_FILE"]):
        if os.path.exists(f):
            os.remove(f)
    if os.path.isdir(ns["BLUEPRINTS_DIR"]):
        for f in os.listdir(ns["BLUEPRINTS_DIR"]):
            os.remove(os.path.join(ns["BLUEPRINTS_DIR"], f))
    os.environ.pop("COBALT_CLAUDE_KEY", None)
    ns["API_KEYS_POOL"] = []


class Resp:
    def __init__(self, status=200, datos=None):
        self.status_code, self._d = status, datos if datos is not None else {}

    def json(self):
        return self._d


class FalsoRequests:
    exceptions = requests_real.exceptions

    def __init__(self):
        self.modelos = []
        self.posts = []
        self.respuesta_post = Resp(200, {"response": "ok"})

    def get(self, url, timeout=None, **kw):
        return Resp(200, {"models": [{"name": m} for m in self.modelos]})

    def post(self, url, json=None, timeout=None, **kw):
        self.posts.append((url, json))
        return self.respuesta_post


fr = FalsoRequests()
ns["requests"] = fr


def respuesta_claude(texto, entrada=100, salida=20, busquedas=0):
    uso = {"input_tokens": entrada, "output_tokens": salida}
    if busquedas:
        uso["server_tool_use"] = {"web_search_requests": busquedas}
    return 200, {"content": [{"type": "text", "text": texto}], "stop_reason": "end_turn", "usage": uso}, {}


llamadas_http = []


def http_falso(respuestas):
    cola = list(respuestas)

    def f(url, cabeceras, cuerpo, timeout):
        llamadas_http.append({"url": url, "cabeceras": cabeceras, "cuerpo": json.loads(json.dumps(cuerpo)), "timeout": timeout})
        x = cola.pop(0) if len(cola) > 1 else cola[0]
        if isinstance(x, Exception):
            raise x
        return x
    return f


class FalsoGenai:
    def __init__(self, programa):
        self.programa, self.usadas = programa, []
        outer = self

        class Client:
            def __init__(self, api_key=None, http_options=None):
                self.api_key = api_key

                class Modelos:
                    def generate_content(inner, model=None, contents=None, config=None):
                        outer.usadas.append((api_key, model, contents))
                        resultado = outer.programa[api_key]
                        if isinstance(resultado, Exception):
                            raise resultado
                        return resultado

                self.models = Modelos()
        self.Client = Client


def gem_ok(texto, t_in=50, t_out=10, pensando=100):
    return pytypes.SimpleNamespace(text=texto, usage_metadata=pytypes.SimpleNamespace(prompt_token_count=t_in, candidates_token_count=t_out, thoughts_token_count=pensando))


class ErrCodigo(Exception):
    def __init__(self, code):
        super().__init__(f"error {code}")
        self.code = code


ollama_llamadas = []


def ollama_falso(respuesta="respuesta local"):
    def f(modelo, prompt):
        ollama_llamadas.append((modelo, prompt))
        return respuesta
    return f


reiniciar(a="  hola  ", b="", c=5, d=True)
r.check("config_texto: devuelve el texto recortado", ns["config_texto"]("a", "x") == "hola")
r.check("config_texto: vacío, número, booleano o ausente -> el valor por defecto", ns["config_texto"]("b", "x") == "x" and ns["config_texto"]("c", "x") == "x"
        and ns["config_texto"]("d", "x") == "x" and ns["config_texto"]("no_existe", "x") == "x")

reiniciar()
r.check("interruptor apagado (por defecto): los modelos de siempre, para cada tarea",
        [ns["modelo_local"](t) for t in ("coordinador", "ejecutor", "respaldo", "vision")] == ["llama3.1", "qwen2.5:7b-instruct", "qwen2.5-coder:7b", "llava"])
fr.modelos = ["qwen3.5:9b", "llava:latest"]
reiniciar(modelo_local_unico=True)
r.check("interruptor encendido y el modelo descargado: qwen3.5:9b para TODO (texto, decisiones, respaldo y visión)",
        {ns["modelo_local"](t) for t in ("coordinador", "ejecutor", "respaldo", "vision")} == {"qwen3.5:9b"})
fr.modelos = ["otro:1b"]
reiniciar(modelo_local_unico=True, modelo_local_nombre="otro:1b")
r.check("nombre configurable: usa 'otro:1b' si es el que está descargado", ns["modelo_local"]("ejecutor") == "otro:1b")

fr.modelos = ["llava:latest"]
reiniciar(modelo_local_unico=True)
import contextlib  # noqa: E402
salida = io.StringIO()
with contextlib.redirect_stdout(salida):
    a = ns["modelo_local"]("ejecutor")
    b = ns["modelo_local"]("respaldo")
r.check("encendido pero SIN el modelo descargado: sigue con los de siempre (nunca se queda sin cerebro local)", a == "qwen2.5:7b-instruct" and b == "qwen2.5-coder:7b")
r.check("y avisa UNA sola vez cómo descargarlo", salida.getvalue().count("no está descargado") == 1 and "ollama pull qwen3.5:9b" in salida.getvalue())
fr.modelos = ["qwen3.5:9b"]
r.check("la disponibilidad se cachea 60 s: aún no lo ve", ns["modelo_local"]("ejecutor") == "qwen2.5:7b-instruct")
ns["_UNICO_DISPONIBLE"]["t"] = -1e9
r.check("pasado el caché lo detecta y cambia solo", ns["modelo_local"]("ejecutor") == "qwen3.5:9b")
r.check("modelos_ollama_faltantes con el modelo único: solo pide ese", ns["modelos_ollama_faltantes"]() == [])
fr.modelos = ["llava:latest"]
r.check("modelos_ollama_faltantes con el interruptor: avisa de qwen3.5:9b, no de los cuatro antiguos", ns["modelos_ollama_faltantes"]() == ["qwen3.5:9b"])

# consultar_ollama: think:false y keep_alive
fr.modelos = ["qwen3.5:9b"]
reiniciar(modelo_local_unico=True, ollama_keep_alive_min=30)
fr.posts.clear()
ns["consultar_ollama"]("qwen3.5:9b", "hola")
url, payload = fr.posts[-1]
r.check("qwen3.5 recibe think:false (si no, gasta todos los tokens pensando y no responde) y keep_alive de 30 min", payload.get("think") is False and payload.get("keep_alive") == "30m")
reiniciar(ollama_keep_alive_min=30)
fr.posts.clear()
ns["consultar_ollama"]("llama3.1", "hola")
payload = fr.posts[-1][1]
r.check("con el interruptor apagado los modelos de siempre NO reciben ni think ni keep_alive (comportamiento intacto)", "think" not in payload and "keep_alive" not in payload)
ns["consultar_ollama"]("gemma4:12b", "hola")
r.check("gemma4 (también razona) recibe think:false aunque no sea el modelo único", fr.posts[-1][1].get("think") is False)
reiniciar(modelo_local_unico=True, ollama_keep_alive_min=10)
ns["consultar_ollama"]("qwen3.5:9b", "hola")
r.check("keep_alive configurable (10 min)", fr.posts[-1][1].get("keep_alive") == "10m")

# visión
img = os.path.join(tmp, "captura.png")
open(img, "wb").write(b"\x89PNGfalso")
fr.modelos = ["qwen3.5:9b"]
reiniciar(modelo_local_unico=True)
fr.posts.clear()
fr.respuesta_post = Resp(200, {"response": "Bosque de noche con árboles"})
txt = ns["analizar_vision_local"](img)
payload = fr.posts[-1][1]
r.check("la visión usa el modelo único (qwen3.5) con think:false y devuelve su descripción", payload["model"] == "qwen3.5:9b" and payload.get("think") is False and payload["images"] and txt == "Bosque de noche con árboles")
reiniciar()
fr.posts.clear()
ns["analizar_vision_local"](img)
r.check("con el interruptor apagado la visión sigue usando llava, sin think", fr.posts[-1][1]["model"] == "llava" and "think" not in fr.posts[-1][1])
fr.respuesta_post = Resp(200, {"response": "ok"})

fuente = io.open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cerebro", "cerebro.py"), encoding="utf-8").read()
r.check("ninguna llamada a Ollama usa ya una constante de modelo fija (todas pasan por modelo_local)", re.search(r"consultar_ollama\(MODELO_", fuente) is None)
llamadas_nube = re.findall(r"consultar_gemini_o_fallback\([^\n]*", fuente)
llamadas_nube = [l for l in llamadas_nube if not l.startswith("consultar_gemini_o_fallback(prompt_completo")]
r.check("las 6 llamadas a la nube declaran su rol: " + str([l[:60] for l in llamadas_nube if "rol=" not in l]), len(llamadas_nube) == 6 and all("rol=" in l for l in llamadas_nube))
r.check("los roles usados son jefes, planos, estudio (x2), tactica y chat",
        sorted(re.findall(r'rol="(\w+)"', "\n".join(llamadas_nube))) == ["chat", "estudio", "estudio", "jefes", "planos", "tactica"])

ns["consultar_ollama"] = ollama_falso("respuesta local")
reiniciar()  # nube_router apagado
ns["API_KEYS_POOL"] = []
ollama_llamadas.clear()
res = ns["consultar_gemini_o_fallback"]("hola", 8.0, rol="chat")
r.check("con nube_router APAGADO y sin claves: la ruta de siempre (modelo local de respaldo), comportamiento intacto", res == "respuesta local" and ollama_llamadas[-1][0] == "qwen2.5-coder:7b")

reiniciar()
ns["API_KEYS_POOL"] = ["G1", "G2"]
ns["genai"] = FalsoGenai({"G1": gem_ok("carrera clásica"), "G2": gem_ok("carrera clásica")})
os.environ["COBALT_CLAUDE_KEY"] = "K"
llamadas_http.clear()
res = ns["consultar_gemini_o_fallback"]("hola", 8.0, rol="chat")
r.check("router APAGADO con claves: gana la carrera de siempre entre las claves de Gemini y el enrutador ni se crea",
        res == "carrera clásica" and ns["_ENRUTADOR"]["obj"] is None and not os.path.exists(ns["NUBE_REGISTRO_FILE"]) and llamadas_http == [])
r.check("...y la carrera usa los modelos del pool de siempre (3.5/3.6), no el de la configuración del router",
        all(u[1] in ns["GEM_MODELS_POOL"] for u in ns["genai"].usadas))

# claude primero en datos
os.environ["COBALT_CLAUDE_KEY"] = "sk-ant-CLAVE-FALSA-123"
reiniciar(nube_router=True, nube_orden_datos="claude,local", nube_ubicacion="Springfield,Illinois,US,America/Chicago")
os.environ["COBALT_CLAUDE_KEY"] = "sk-ant-CLAVE-FALSA-123"
llamadas_http.clear()
ns["_http_post"] = http_falso([respuesta_claude("El Warden tiene 500 puntos de vida.", 300, 20)])
res = ns["consultar_nube_resultado"]("datos", "¿Cuánta vida tiene el Warden?")
c = llamadas_http[0]
r.check("router encendido: Claude contesta el dato", res.proveedor == "claude" and "500" in res.texto)
r.check("la petición lleva el modelo de la configuración, la clave en x-api-key y el sistema de Cobalt con la fecha de hoy",
        c["cuerpo"]["model"] == "claude-sonnet-5" and c["cabeceras"]["x-api-key"] == "sk-ant-CLAVE-FALSA-123" and ns["fecha_hoy_es"]() in c["cuerpo"]["system"])
r.check("sin búsqueda web en 'datos' (solo en 'internet')", "tools" not in c["cuerpo"] and c["timeout"] == 12)
r.check("el coste de la llamada (300·$2 + 20·$10 por millón) se suma al gasto de hoy", abs(json.load(open(ns["NUBE_GASTO_FILE"]))["usd"] - 0.0008) < 1e-9)
linea = json.loads(open(ns["NUBE_REGISTRO_FILE"], encoding="utf-8").read().strip().splitlines()[-1])
r.check("el registro anota la llamada sin el prompt ni la respuesta ni la clave", linea["proveedor"] == "claude" and "Warden" not in json.dumps(linea) and "CLAVE" not in json.dumps(linea))

ns["_http_post"] = http_falso([respuesta_claude("La versión es la 26.3.", 500, 30, busquedas=1)])
llamadas_http.clear()
res = ns["consultar_nube_resultado"]("internet", "¿versión de minecraft?")
c = llamadas_http[0]["cuerpo"]
r.check("internet: Claude lleva la herramienta de búsqueda web con ubicación (Springfield, IL, US) y max_uses 3",
        c["tools"][0]["type"] == "web_search_20250305" and c["tools"][0]["max_uses"] == 3 and c["tools"][0]["user_location"]["country"] == "US"
        and c["tools"][0]["user_location"]["city"] == "Springfield" and llamadas_http[0]["timeout"] == 45)
r.check("la búsqueda cuesta $0,01 más los tokens", abs(json.load(open(ns["NUBE_GASTO_FILE"]))["usd"] - (0.0008 + (500 * 2 + 30 * 10) / 1e6 + 0.01)) < 1e-9)
reiniciar(nube_router=True, nube_busqueda_claude=False, nube_orden_internet="claude,local")
os.environ["COBALT_CLAUDE_KEY"] = "K"
llamadas_http.clear()
ns["_http_post"] = http_falso([respuesta_claude("x")])
ns["consultar_nube_resultado"]("internet", "p")
r.check("nube_busqueda_claude=false apaga la búsqueda web de Claude", "tools" not in llamadas_http[0]["cuerpo"])

reiniciar(nube_router=True, nube_orden_planos="claude", plazo_planos_s=7)
os.environ["COBALT_CLAUDE_KEY"] = "K"
llamadas_http.clear()
ns["_http_post"] = http_falso([respuesta_claude('{"layers": []}')])
ns["consultar_nube_resultado"]("planos", "diseña")
r.check("planos: sin 'system' (el planificador trae sus instrucciones), max_tokens 12000 y el plazo de la configuración (7 s)",
        "system" not in llamadas_http[0]["cuerpo"] and llamadas_http[0]["cuerpo"]["max_tokens"] == 12000 and llamadas_http[0]["timeout"] == 7)

# sin claves configuradas: no cuenta como fallo, simplemente no se usa
reiniciar(nube_router=True)
r.check("sin clave de Claude ni de Gemini, 'datos' solo tiene el modelo local", ns["orden_nube"]("datos") == ["local"])
ns["API_KEYS_POOL"] = ["G1"]
r.check("solo con Gemini: gemini,local", ns["orden_nube"]("datos") == ["gemini", "local"])
os.environ["COBALT_CLAUDE_KEY"] = "K"
r.check("con las dos: el orden de defecto de 'datos' (claude primero)", ns["orden_nube"]("datos") == ["claude", "gemini", "local"])
reiniciar(nube_router=True, nube_orden_datos="gemini , claude")
os.environ["COBALT_CLAUDE_KEY"] = "K"
ns["API_KEYS_POOL"] = ["G1"]
r.check("el orden se configura en cobalt_config.json (nube_orden_datos)", ns["orden_nube"]("datos") == ["gemini", "claude"])
reiniciar(nube_router=True, nube_orden_datos="basura")
os.environ["COBALT_CLAUDE_KEY"] = "K"
r.check("un orden inválido cae al de defecto", ns["orden_nube"]("datos") == ["claude", "local"])
reiniciar(nube_router=True)
ns["consultar_ollama"] = ollama_falso("")
r.check("planos sin ninguna nube configurada: agotado, y devuelve texto vacío (el planificador usará la plantilla)", ns["consultar_gemini_o_fallback"]("p", 45.0, rol="planos") == "")

# fallo de Claude -> Gemini
os.environ["COBALT_CLAUDE_KEY"] = "K"
reiniciar(nube_router=True, nube_orden_datos="claude,gemini,local")
os.environ["COBALT_CLAUDE_KEY"] = "K"
ns["API_KEYS_POOL"] = ["G1", "G2"]
ns["genai"] = FalsoGenai({"G1": gem_ok("Respuesta de Gemini", 40, 10, 50), "G2": gem_ok("otra")})
ns["_http_post"] = http_falso([(529, {"error": {"type": "overloaded_error"}}, {})])
res = ns["consultar_nube_resultado"]("datos", "x")
r.check("Claude sobrecargado (529): contesta Gemini", res.proveedor == "gemini" and res.texto == "Respuesta de Gemini" and res.intentos[0]["tipo"] == "sobrecarga")
r.check("Gemini gratis: coste 0 (no gasta el tope)", res.coste_usd == 0.0)
ns["_http_post"] = http_falso([requests_real.exceptions.Timeout("lento")])
res = ns["consultar_nube_resultado"]("datos", "x")
r.check("un timeout de red de Claude se convierte en fallo 'timeout' y pasa a Gemini", res.proveedor == "gemini" and res.intentos[0]["tipo"] == "timeout")
ns["_http_post"] = http_falso([requests_real.exceptions.ConnectionError("sin red")])
res = ns["consultar_nube_resultado"]("datos", "x")
r.check("sin red: fallo 'red' y pasa a Gemini", res.proveedor == "gemini" and res.intentos[0]["tipo"] == "red")

# Gemini de pago: el coste cuenta
reiniciar(nube_router=True, nube_orden_estudio="gemini", nube_gemini_de_pago=True)
ns["API_KEYS_POOL"] = ["G1"]
ns["genai"] = FalsoGenai({"G1": gem_ok("resumen", 1000, 100, 400)})
res = ns["consultar_nube_resultado"]("estudio", "x")
r.check("Gemini de pago: 1000 entrada + 500 de salida (100 + 400 pensando) a $0,75/$3,75", abs(res.coste_usd - (1000 * 0.75 + 500 * 3.75) / 1e6) < 1e-12 and ns["genai"].usadas[0][1] == "gemini-3.6-flash")

# rotación de claves de Gemini: de una en una, y la que da 429 se enfría
reiniciar(nube_router=True, nube_orden_estudio="gemini")
ns["API_KEYS_POOL"] = ["G1", "G2", "G3"]
ns["genai"] = FalsoGenai({"G1": ErrCodigo(429), "G2": gem_ok("de G2"), "G3": gem_ok("de G3")})
res = ns["consultar_nube_resultado"]("estudio", "x")
r.check("una clave con 429 se salta a la siguiente (G1 falló, contesta G2) en UNA sola consulta", res.texto == "de G2" and [u[0] for u in ns["genai"].usadas] == ["G1", "G2"])
res = ns["consultar_nube_resultado"]("estudio", "x")
r.check("la siguiente consulta rota a G3 (no gasta las 3 a la vez) y G1 sigue enfriándose", res.texto == "de G3" and [u[0] for u in ns["genai"].usadas][2:] == ["G3"])
res = ns["consultar_nube_resultado"]("estudio", "x")
r.check("y después vuelve a G2 SALTÁNDOSE G1 (enfriada 60 s): en esa consulta solo se usó G2", res.texto == "de G2" and [u[0] for u in ns["genai"].usadas][3:] == ["G2"])

reiniciar(nube_router=True, nube_orden_estudio="gemini")
ns["API_KEYS_POOL"] = ["G1", "G2"]
ns["genai"] = FalsoGenai({"G1": ErrCodigo(503), "G2": gem_ok("no debería llamarse")})
res = ns["consultar_nube_resultado"]("estudio", "x")
r.check("503 (sobrecarga del modelo entero): no se prueban las demás claves, se pasa de proveedor", res.agotado and len(ns["genai"].usadas) == 1 and res.intentos[0]["tipo"] == "sobrecarga")
ns["genai"] = FalsoGenai({"G1": ErrCodigo(404), "G2": gem_ok("x")})
reiniciar(nube_router=True, nube_orden_estudio="gemini")
ns["API_KEYS_POOL"] = ["G1", "G2"]
res = ns["consultar_nube_resultado"]("estudio", "x")
r.check("404 (modelo inexistente) = error de configuración: se aparta 10 min, no se insiste con cada clave", res.intentos[0]["tipo"] == "config" and len(ns["genai"].usadas) == 1)
reiniciar(nube_router=True, nube_orden_estudio="gemini")
ns["API_KEYS_POOL"] = ["G1", "G2"]
ns["genai"] = FalsoGenai({"G1": ErrCodigo(429), "G2": ErrCodigo(429)})
res = ns["consultar_nube_resultado"]("estudio", "x")
r.check("todas las claves con 429: fallo de cuota y quedan enfriadas", res.agotado and res.intentos[0]["tipo"] == "cuota")
res = ns["consultar_nube_resultado"]("estudio", "x")
r.check("mientras descansan no se llama a Gemini de nuevo", len(ns["genai"].usadas) == 2)

# tope diario: Claude fuera, Gemini responde
os.environ["COBALT_CLAUDE_KEY"] = "K"
reiniciar(nube_router=True, nube_orden_datos="claude,gemini", nube_tope_diario_usd=0.5)
os.environ["COBALT_CLAUDE_KEY"] = "K"
ns["API_KEYS_POOL"] = ["G1"]
ns["genai"] = FalsoGenai({"G1": gem_ok("gratis")})
json.dump({"dia": time.strftime("%Y-%m-%d"), "usd": 0.6}, open(ns["NUBE_GASTO_FILE"], "w"))
llamadas_http.clear()
ns["_http_post"] = http_falso([respuesta_claude("de pago")])
res = ns["consultar_nube_resultado"]("datos", "x")
r.check("gasto de hoy por encima del tope: Claude ni se llama (0 peticiones) y contesta Gemini gratis", res.proveedor == "gemini" and llamadas_http == [] and res.intentos[0]["estado"] == "tope_diario")

reiniciar(nube_router=True, nube_orden_tactica="claude", plazo_tactica_s=9)
os.environ["COBALT_CLAUDE_KEY"] = "K"
llamadas_http.clear()
ns["_http_post"] = http_falso([respuesta_claude("Mantén la distancia.")])
r.check("consultar_gemini_o_fallback(rol='tactica') con router: texto del enrutador y el plazo de la configuración (9 s)",
        ns["consultar_gemini_o_fallback"]("p", 15.0, rol="tactica") == "Mantén la distancia." and llamadas_http[0]["timeout"] == 9)

reiniciar(nube_router=True)
ns["API_KEYS_POOL"] = ["G1"]
os.environ["COBALT_CLAUDE_KEY"] = "K"
r.check("con todo disponible el orden de 'datos' es claude (API), gemini, local", ns["orden_nube"]("datos") == ["claude", "gemini", "local"])
r.check("y el de 'estudio' empieza por Gemini gratis", ns["orden_nube"]("estudio")[0] == "gemini")

enviados = []
ns["escribir_comando"] = lambda ordenes: enviados.append(ordenes[0]["chat_message"])
buscadas = []
ns["buscar_en_internet"] = lambda q: (buscadas.append(q), "fragmentos de prueba")[1]


def preparar_internet(orden="claude,gemini,local", claude=None, gemini=None, local="respuesta local"):
    reiniciar(nube_router=True, nube_orden_internet=orden)
    os.environ["COBALT_CLAUDE_KEY"] = "K"
    ns["API_KEYS_POOL"] = ["G1"]
    ns["_http_post"] = http_falso([claude or respuesta_claude("Claude lo encontró", busquedas=1)])
    ns["genai"] = FalsoGenai({"G1": gemini or gem_ok("Gemini con fragmentos")})
    ns["consultar_ollama"] = ollama_falso(local)
    enviados.clear()
    buscadas.clear()
    ollama_llamadas.clear()


preparar_internet()
ns["responder_internet_en_hilo"]("¿Cuál es la última versión?", "Steve")
r.check("internet: Claude contesta (con su búsqueda) y NO se hace la búsqueda de DuckDuckGo", enviados == ["Claude lo encontró"] and buscadas == [])
preparar_internet(claude=(529, {"error": {"type": "overloaded_error"}}, {}))
ns["responder_internet_en_hilo"]("¿Cuál es la última versión?", "Steve")
r.check("Claude cae: se busca en DuckDuckGo UNA vez y contesta Gemini con esos fragmentos", enviados == ["Gemini con fragmentos"] and buscadas == ["¿Cuál es la última versión?"])
prompt_gemini = ns["genai"].usadas[0][2]
r.check("el prompt de Gemini lleva los fragmentos y la orden de desconfiar si se contradicen (lo que evita inventar 'Caelum Update')", "fragmentos de prueba" in prompt_gemini and "contradicen" in prompt_gemini)
preparar_internet(claude=(529, {}, {}), gemini=ErrCodigo(503))
ns["responder_internet_en_hilo"]("¿Cuál es la última versión?", "Steve")
r.check("si solo queda el modelo local, la respuesta se DEGRADA: no da el dato, dice que no pudo comprobarlo", enviados == [nn.MENSAJE_NO_VERIFICADO])
preparar_internet(claude=(529, {}, {}), gemini=ErrCodigo(503), local="")
ns["responder_internet_en_hilo"]("¿Cuál es la última versión?", "Steve")
r.check("si nadie contesta: el mismo aviso honesto", enviados == [nn.MENSAJE_NO_VERIFICADO])
preparar_internet()
ns["escribir_comando"] = lambda ordenes: (_ for _ in ()).throw(OSError("disco lleno"))
try:
    ns["responder_internet_en_hilo"]("x", "Steve")
    r.check("un fallo al escribir en el chat no revienta el hilo", True)
except Exception:
    r.check("un fallo al escribir en el chat no revienta el hilo", False)
ns["escribir_comando"] = lambda ordenes: enviados.append(ordenes[0]["chat_message"])

io.open(ns["STATUS_FILE"], "w", encoding="utf-8").write(json.dumps({"is_deployed": True, "is_dead": False, "updated_ms": time.time() * 1000}))
hilos_lanzados = []
import threading as _th  # noqa: E402
_Thread = _th.Thread


pendientes = []


class HiloDiferido:
    def __init__(self, target=None, args=(), kwargs=None, daemon=None):
        self.target, self.args, self.kwargs = target, args, kwargs or {}

    def start(self):
        hilos_lanzados.append(self.target.__name__)
        pendientes.append((self.target, self.args, self.kwargs))


def correr_pendientes():
    while pendientes:
        t, a, k = pendientes.pop(0)
        t(*a, **k)


ns["threading"] = pytypes.SimpleNamespace(Thread=HiloDiferido, Lock=_th.Lock)
preparar_internet()
ns["consultar_ollama"] = lambda modelo, prompt: "SI" if "requiere internet" in prompt else "[{\"action\": \"ninguna\", \"chat_message\": \"cerebro local\"}]"
enviados.clear()
ns["escribir_comando"] = lambda ordenes: enviados.append(ordenes[0]["chat_message"])
llamadas_http.clear()
hilos_lanzados.clear()
ns["procesar_mensaje_async"]("Steve", "¿cuál es la última versión de minecraft hoy?")
aviso_inmediato = list(enviados)
r.check("router ENCENDIDO + el coordinador dice 'SI': responde 'voy a mirarlo' YA (antes de que llegue la respuesta) y lanza UN hilo",
        len(aviso_inmediato) == 1 and aviso_inmediato[0] in ("Déjame comprobarlo...", "Voy a mirarlo, dame un momento.", "Lo busco ahora mismo.")
        and hilos_lanzados == ["responder_internet_en_hilo"])
r.check("...y todavía no se ha llamado a Claude (eso ocurre en el hilo, no bloquea el bucle)", len(llamadas_http) == 0)
correr_pendientes()
r.check("...luego el hilo entrega la respuesta real de Claude por el chat", enviados == [aviso_inmediato[0], "Claude lo encontró"])

preparar_internet()
ns["consultar_ollama"] = lambda modelo, prompt: "NO" if "requiere internet" in prompt else "[{\"action\": \"ninguna\", \"chat_message\": \"cerebro local\"}]"
enviados.clear()
hilos_lanzados.clear()
ns["procesar_mensaje_async"]("Steve", "¿cuánto cuesta un dólar hoy?")
correr_pendientes()
r.check("aunque el LLM clasifique 'NO', la regla en código manda a internet una pregunta de precio (aviso + respuesta de Claude)",
        len(enviados) == 2 and enviados[1] == "Claude lo encontró" and hilos_lanzados == ["responder_internet_en_hilo"])
config(nube_router=True, nube_orden_internet="claude,local", internet_por_reglas=False)
enviados.clear()
hilos_lanzados.clear()
ns["procesar_mensaje_async"]("Steve", "¿cuánto cuesta un dólar hoy?")
correr_pendientes()
r.check("internet_por_reglas=false: vuelve a decidir solo el LLM (aquí dice NO -> cerebro local)", enviados == ["Cerebro local"] and hilos_lanzados == [])

reiniciar(nube_router=False)
ns["API_KEYS_POOL"] = []
ns["consultar_ollama"] = lambda modelo, prompt: "SI" if "requiere internet" in prompt else "respuesta local con datos web"
enviados.clear()
hilos_lanzados.clear()
ns["procesar_mensaje_async"]("Steve", "¿cuál es la última versión de minecraft hoy?")
r.check("router APAGADO: la rama de siempre, síncrona, sin hilo ni mensaje de espera", hilos_lanzados == [] and len(enviados) == 1 and "respuesta local con datos web" in enviados[0].lower())

# datos de Minecraft
preparar_internet(orden="claude,local")
ns["_http_post"] = http_falso([respuesta_claude("El Warden tiene 500 puntos de vida (250 corazones).")])
ns["consultar_ollama"] = lambda modelo, prompt: "NO" if "requiere internet" in prompt else "[{\"action\": \"ninguna\", \"chat_message\": \"cerebro local\"}]"
config(nube_router=True, nube_orden_datos="claude,local", nube_orden_internet="claude,local")
enviados.clear()
ns["procesar_mensaje_async"]("Steve", "¿Cuántos puntos de vida tiene el Warden?")
r.check("router encendido + pregunta de DATOS de Minecraft: la contesta la nube (Claude), no el modelo local", enviados == ["El Warden tiene 500 puntos de vida (250 corazones)."])
enviados.clear()
ns["consultar_ollama"] = lambda modelo, prompt: "NO" if "requiere internet" in prompt else "[{\"action\": \"ninguna\", \"chat_message\": \"cerebro local\"}]"
ns["_http_post"] = http_falso([(529, {}, {})])
ns["procesar_mensaje_async"]("Steve", "¿Cuántos puntos de vida tiene el Warden?")
r.check("si la nube no contesta un dato, NO lo contesta el modelo local (45 % de acierto): dice que no puede comprobarlo", enviados == [nn.MENSAJE_NO_VERIFICADO])
enviados.clear()
llamadas_http.clear()
ns["procesar_mensaje_async"]("Steve", "hola cobalt, ¿cómo estás?")
r.check("la charla NO se desvía a la nube (0 peticiones a Claude; la atiende el cerebro local de siempre)", llamadas_http == [] and len(enviados) == 1)
enviados.clear()
ns["procesar_mensaje_async"]("Steve", "mina hierro por favor")
r.check("las órdenes tampoco", enviados == ["Cerebro local"] and llamadas_http == [])
config(nube_router=True, nube_datos=False, nube_orden_datos="claude,local")
enviados.clear()
ns["procesar_mensaje_async"]("Steve", "¿Cuántos puntos de vida tiene el Warden?")
r.check("nube_datos=false apaga solo esta desviación: el dato vuelve al modelo local", enviados == ["Cerebro local"])

ns["threading"] = _th
reiniciar()
ns["escribir_comando"] = lambda ordenes: enviados.append(ordenes[0]["chat_message"])
validar = ns["validar_blueprint"]
llamadas_plan = []


def nube_plan(respuestas):
    cola = list(respuestas)

    def f(prompt, timeout_s=8.0, rol=None):
        llamadas_plan.append(rol)
        return cola.pop(0) if len(cola) > 1 else cola[0]
    return f


ns["consultar_gemini_o_fallback"] = nube_plan([""])
llamadas_plan.clear()
res = ns["generar_blueprint_con_nube"]("una casa de piedra y madera de 7x7 con 5 de alto")
r.check("la nube no responde: se construye una PLANTILLA (ok, origen 'plantilla', válida)", res["ok"] and res["origen"] == "plantilla" and res["bloques"] > 50)
r.check("...y solo se preguntó UNA vez (sin respuesta no se reintenta al instante) y con el rol 'planos'", llamadas_plan == ["planos"])
guardado = json.load(open(os.path.join(ns["BLUEPRINTS_DIR"], res["nombre"] + ".json"), encoding="utf-8"))
r.check("el plano de plantilla guardado pasa el validador real de Cobalt", validar(guardado)[0] is not None)
res = ns["generar_blueprint_con_nube"]("una estatua de dragón gigante")
r.check("si ninguna plantilla encaja, lo dice con honestidad (no inventa)", not res["ok"] and "ninguna plantilla" in res["motivo"])
config(plantillas_plano=False)
res = ns["generar_blueprint_con_nube"]("una casa de 7x7")
r.check("plantillas_plano=false apaga el respaldo", not res["ok"])
config()
res = ns["generar_blueprint_con_nube"]("una casa de 7x7", permitir_plantilla=False)
r.check("permitir_plantilla=False (lo usa la biblioteca) tampoco usa el respaldo", not res["ok"])
ns["consultar_gemini_o_fallback"] = nube_plan(["basura no json", "basura otra vez"])
llamadas_plan.clear()
res = ns["generar_blueprint_con_nube"]("una torre de piedra de 5x5 y 12 de alto")
r.check("la nube devuelve basura dos veces (2 intentos con el error del primero): entonces plantilla", res["ok"] and res["origen"] == "plantilla" and llamadas_plan == ["planos", "planos"])
bueno = {"blueprint_name": "torre_ia", "layers": [{"y": 0, "blocks": [{"x": 0, "z": 0, "block": "minecraft:stone"}, {"x": 1, "z": 0, "block": "minecraft:stone"}]}]}
ns["consultar_gemini_o_fallback"] = nube_plan([json.dumps(bueno)])
res = ns["generar_blueprint_con_nube"]("una torre de piedra")
r.check("si la nube da un plano válido se usa ese (origen 'nube'), no la plantilla", res["ok"] and res["origen"] == "nube" and res["bloques"] == 2)
res = ns["generar_blueprint_con_nube"]("una torre de piedra", nombre="lib_torre_vigia")
r.check("'nombre' fija el nombre del archivo (lo usa la biblioteca)", res["ok"] and res["nombre"] == "lib_torre_vigia" and os.path.exists(os.path.join(ns["BLUEPRINTS_DIR"], "lib_torre_vigia.json")))
ns["consultar_gemini_o_fallback"] = nube_plan([""])
enviados.clear()
ns["disenar_y_avisar"]("una casa de piedra de 7x7", "Steve")
r.check("el aviso al jugador dice cuando el plano es de plantilla", len(enviados) == 1 and "plantilla de código" in enviados[0] and "listo" in enviados[0])

generadas = []


def generar_falso(exito=True):
    def f(descripcion, intentos=2, nombre=None, permitir_plantilla=True):
        generadas.append((descripcion, nombre, permitir_plantilla))
        if not exito:
            return {"ok": False, "motivo": "la nube falló"}
        os.makedirs(ns["BLUEPRINTS_DIR"], exist_ok=True)
        open(os.path.join(ns["BLUEPRINTS_DIR"], nombre + ".json"), "w").write("{}")
        return {"ok": True, "nombre": nombre, "bloques": 100}
    return f


reiniciar()
ns["generar_blueprint_con_nube"] = generar_falso()
generadas.clear()
r.check("biblioteca_planos apagado (por defecto): no genera nada", ns["biblioteca_generar_uno"]() is None and generadas == [])
reiniciar(biblioteca_planos=True, biblioteca_max_dia=2)
ns["generar_blueprint_con_nube"] = generar_falso()
generadas.clear()
r.check("encendida: prepara el primero de la lista (el refugio) con nombre lib_refugio y SIN plantilla", ns["biblioteca_generar_uno"]() == "refugio" and generadas[0][1] == "lib_refugio" and generadas[0][2] is False)
r.check("el siguiente es la casa pequeña (el refugio ya existe)", ns["biblioteca_generar_uno"]() == "casa_pequena")
r.check("cupo diario de 2: el tercero no se genera", ns["biblioteca_generar_uno"]() is None and len(generadas) == 2)
reiniciar(biblioteca_planos=True, biblioteca_max_dia=10)
ns["generar_blueprint_con_nube"] = generar_falso(exito=False)
generadas.clear()
for _ in range(2):
    ns["biblioteca_generar_uno"]()
r.check("un plano que falla 2 veces el mismo día no se reintenta más (evita gastar en bucle)", [g[1] for g in generadas] == ["lib_refugio", "lib_refugio"])
ns["biblioteca_generar_uno"]()
r.check("...y pasa al siguiente plano de la lista", generadas[-1][1] == "lib_casa_pequena")
reiniciar(biblioteca_planos=True, planificador_nube=False)
generadas.clear()
r.check("con el planificador apagado la biblioteca tampoco genera", ns["biblioteca_generar_uno"]() is None and generadas == [])
reiniciar(biblioteca_planos=True)
ns["generar_blueprint_con_nube"] = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
r.check("una excepción al generar no revienta el hilo", ns["biblioteca_generar_uno"]() is None)

fuente_estudio = fuente[fuente.index("def estudiar_mods_afk"):fuente.index("def estudiar_mods_afk") + 4200]
r.check("al terminar de estudiar se lanza la biblioteca en un hilo, solo si el interruptor está encendido",
        'config_activa("biblioteca_planos", False)' in fuente_estudio and "target=biblioteca_generar_uno" in fuente_estudio)

r.terminar()
