"""Pruebas de configuración: carga de API keys (entorno + registro de Windows) y arranque automático de Ollama."""
import os
import subprocess
import tempfile
import time

from _cargar import Resultados, cargar_cerebro

ns = cargar_cerebro()
r = Resultados()

for k in [k for k in os.environ if k.startswith("GEMINI_API_KEY_")]:
    del os.environ[k]
registro = {"GEMINI_API_KEY_1": "reg1", "GEMINI_API_KEY_3": "reg3"}
ns["_leer_variable_usuario_windows"] = lambda nombre: registro.get(nombre, "")

r.check("sin variables de entorno: lee las keys del registro de Windows (no exige reiniciar el IDE)",
        ns["_cargar_api_keys"]() == ["reg1", "reg3"])

os.environ["GEMINI_API_KEY_1"] = "  env1  "
r.check("el entorno manda sobre el registro y se recorta el espacio", ns["_cargar_api_keys"]() == ["env1", "reg3"])

os.environ["GEMINI_API_KEY_2"] = "reg3"
r.check("una key repetida no se duplica en el pool", ns["_cargar_api_keys"]() == ["env1", "reg3"])

registro.clear()
for k in [k for k in os.environ if k.startswith("GEMINI_API_KEY_")]:
    del os.environ[k]
r.check("sin ninguna key: pool vacío (el cerebro sigue con Ollama, sin excepción)", ns["_cargar_api_keys"]() == [])

cerebro_real = cargar_cerebro()
r.check("lector real del registro: variable inexistente -> '' (sin excepción)",
        cerebro_real["_leer_variable_usuario_windows"]("NO_EXISTE_XYZ_123") == "")

if os.name == "nt":
    import certifi

    def _sin_vars_ssl():
        for v in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"):
            os.environ.pop(v, None)

    _sin_vars_ssl()
    r.check("certificados: crea el bundle y devuelve True", ns["_confiar_en_certificados_de_windows"]() is True)
    ruta_bundle = os.environ.get("SSL_CERT_FILE", "")
    r.check("SSL_CERT_FILE y REQUESTS_CA_BUNDLE apuntan al mismo archivo existente",
            os.path.isfile(ruta_bundle) and ruta_bundle == os.environ.get("REQUESTS_CA_BUNDLE"))
    contenido = open(ruta_bundle, encoding="utf-8").read()
    r.check("el bundle contiene TODO certifi (no lo sustituye) y añade las raíces de Windows",
            contenido.startswith(open(certifi.where(), encoding="utf-8").read()[:200])
            and contenido.count("BEGIN CERTIFICATE") > open(certifi.where(), encoding="utf-8").read().count("BEGIN CERTIFICATE"))
    r.check("no deja archivos .tmp en la carpeta temporal", not [f for f in os.listdir(os.path.dirname(ruta_bundle))
                                                                if f.startswith("cobalt_ca_bundle.pem.") and f.endswith(".tmp")])
    _reemplazar_original = os.replace

    def _reemplazo_que_falla(origen, destino):
        raise PermissionError("el bundle está en uso por otro proceso")

    _sin_vars_ssl()
    os.replace = _reemplazo_que_falla
    try:
        resultado_en_uso = ns["_confiar_en_certificados_de_windows"]()
    finally:
        os.replace = _reemplazar_original
    r.check("si no se puede reemplazar el bundle devuelve False y no toca las variables SSL", resultado_en_uso is False and not os.environ.get("SSL_CERT_FILE"))
    r.check("y en ese caso tampoco deja el .tmp en la carpeta temporal", not [f for f in os.listdir(os.path.dirname(ruta_bundle))
                                                                            if f.startswith("cobalt_ca_bundle.pem.") and f.endswith(".tmp")])
    _sin_vars_ssl()
    ns["_confiar_en_certificados_de_windows"]()  # deja el estado como estaba para el resto de comprobaciones
    os.environ["SSL_CERT_FILE"] = "C:/mi/propio/bundle.pem"
    r.check("respeta un SSL_CERT_FILE que el usuario ya haya definido (no lo pisa)",
            ns["_confiar_en_certificados_de_windows"]() is False and os.environ["SSL_CERT_FILE"] == "C:/mi/propio/bundle.pem")
    _sin_vars_ssl()

requests_mod = ns["requests"]
get_original, popen_original, which_original = requests_mod.get, subprocess.Popen, ns["shutil"].which


class _Resp:
    def __init__(self, codigo=200, datos=None):
        self.status_code, self._datos = codigo, datos or {}

    def json(self):
        return self._datos


try:
    # ollama_responde
    requests_mod.get = lambda *a, **k: _Resp(200)
    r.check("ollama_responde: True si /api/version contesta 200", ns["ollama_responde"]() is True)

    def _rechaza(*a, **k):
        raise requests_mod.exceptions.ConnectionError("rechazada")
    requests_mod.get = _rechaza
    r.check("ollama_responde: False (sin excepción) si rechaza la conexión", ns["ollama_responde"]() is False)

    # modelos_ollama_faltantes
    requests_mod.get = lambda *a, **k: _Resp(200, {"models": [{"name": "llama3.1:latest"}, {"name": "qwen2.5:7b-instruct"},
                                                              {"name": "llava:latest"}, {"name": "llama3:latest"}]})
    import json as _json
    import tempfile as _tempfile
    _cfg_original = ns["CONFIG_FILE"]
    ns["CONFIG_FILE"] = os.path.join(_tempfile.mkdtemp(), "cobalt_config.json")
    with open(ns["CONFIG_FILE"], "w", encoding="utf-8") as _f:
        _json.dump({"modelo_local_unico": False}, _f)
    ns["_CONFIG_CACHE"]["t"] = 0.0
    r.check("modelos_ollama_faltantes: detecta solo el que falta (qwen2.5-coder:7b)",
            ns["modelos_ollama_faltantes"]() == ["qwen2.5-coder:7b"])
    with open(ns["CONFIG_FILE"], "w", encoding="utf-8") as _f:
        _json.dump({"modelo_local_unico": True}, _f)
    ns["_CONFIG_CACHE"]["t"] = 0.0
    r.check("modelos_ollama_faltantes con modelo_local_unico: solo exige el modelo único (qwen3.5:9b) y lo detecta si falta", ns["modelos_ollama_faltantes"]() == ["qwen3.5:9b"])
    ns["CONFIG_FILE"] = _cfg_original
    ns["_CONFIG_CACHE"]["t"] = 0.0
    requests_mod.get = _rechaza
    r.check("modelos_ollama_faltantes: None si no puede consultar", ns["modelos_ollama_faltantes"]() is None)

    # localizar_ollama
    ns["shutil"].which = lambda n: "C:/en/el/PATH/ollama.exe"
    r.check("localizar_ollama: usa el PATH primero", ns["localizar_ollama"]() == "C:/en/el/PATH/ollama.exe")
    ns["shutil"].which = lambda n: None
    falso_local = tempfile.mkdtemp()
    os.makedirs(os.path.join(falso_local, "Programs", "Ollama"))
    exe_falso = os.path.join(falso_local, "Programs", "Ollama", "ollama.exe")
    open(exe_falso, "w").close()
    local_original = os.environ.get("LOCALAPPDATA")
    os.environ["LOCALAPPDATA"] = falso_local
    encontrado = ns["localizar_ollama"]()
    r.check("localizar_ollama: sin PATH, busca en LOCALAPPDATA/Programs/Ollama",
            encontrado is not None and os.path.normpath(encontrado) == os.path.normpath(exe_falso))
    if local_original is None:
        del os.environ["LOCALAPPDATA"]
    else:
        os.environ["LOCALAPPDATA"] = local_original

    # asegurar_ollama: ya está corriendo -> no lanza nada
    lanzados = []
    subprocess.Popen = lambda *a, **k: lanzados.append((a, k))
    ns["ollama_responde"] = lambda timeout=1.5: True
    ns["modelos_ollama_faltantes"] = lambda: []
    r.check("asegurar_ollama: si ya responde NO lanza otro proceso", ns["asegurar_ollama"]() is True and lanzados == [])

    # asegurar_ollama: apagado y sin ollama.exe
    ns["ollama_responde"] = lambda timeout=1.5: False
    ns["localizar_ollama"] = lambda: None
    r.check("asegurar_ollama: sin ollama.exe -> False y no lanza nada", ns["asegurar_ollama"]() is False and lanzados == [])

    # asegurar_ollama: apagado, lo inicia y responde tras unos intentos
    llamadas = {"n": 0}

    def _responde_al_tercero(timeout=1.5):
        llamadas["n"] += 1
        return llamadas["n"] >= 3
    ns["ollama_responde"] = _responde_al_tercero
    ns["localizar_ollama"] = lambda: "C:/x/ollama.exe"
    time_original = ns["time"].sleep
    ns["time"].sleep = lambda s: None  # no esperar de verdad
    ok = ns["asegurar_ollama"](esperar_s=5)
    ns["time"].sleep = time_original
    r.check("asegurar_ollama: apagado -> ejecuta 'ollama serve' y espera a que responda", ok is True and len(lanzados) == 1)
    args, kwargs = lanzados[0]
    r.check("lo lanza como ['<exe>', 'serve'] sin ventana ni stdin/stdout ligados",
            args[0] == ["C:/x/ollama.exe", "serve"] and kwargs.get("stdout") == subprocess.DEVNULL
            and (os.name != "nt" or kwargs.get("creationflags", 0) & subprocess.CREATE_NO_WINDOW))

    # asegurar_ollama: lo inicia pero nunca responde
    lanzados.clear()
    ns["ollama_responde"] = lambda timeout=1.5: False
    r.check("asegurar_ollama: si no responde en el plazo -> False (no se cuelga)", ns["asegurar_ollama"](esperar_s=0.3) is False and len(lanzados) == 1)

    # asegurar_ollama: no se puede ejecutar
    def _falla(*a, **k):
        raise OSError("acceso denegado")
    subprocess.Popen = _falla
    r.check("asegurar_ollama: si el sistema impide lanzarlo -> False sin excepción", ns["asegurar_ollama"](esperar_s=0.3) is False)
finally:
    requests_mod.get, subprocess.Popen, ns["shutil"].which = get_original, popen_original, which_original

import contextlib
import io as _io

genai_mod = ns["genai"]
cliente_original = genai_mod.Client
modo = {"tipo": "ok"}
plazos = []


class _Respuesta:
    text = "  OK  "


class _Modelos:
    def generate_content(self, model, contents, config):
        if modo["tipo"] == "error":
            raise RuntimeError("404 NOT_FOUND: modelo retirado")
        if modo["tipo"] == "lento":
            time.sleep(2.0)
        return _Respuesta()


class _ClienteFalso:
    def __init__(self, api_key=None, http_options=None):
        plazos.append((http_options or {}).get("timeout"))
        self.models = _Modelos()


try:
    genai_mod.Client = _ClienteFalso
    ns["API_KEYS_POOL"][:] = ["k1aaaa", "k2bbbb"]
    ns["consultar_ollama"] = lambda modelo, prompt: "LOCAL"

    modo["tipo"] = "ok"
    salida = _io.StringIO()
    with contextlib.redirect_stdout(salida):
        resp = ns["consultar_gemini_o_fallback"]("hola", timeout_s=8.0)
    r.check("nube: devuelve la respuesta recortada del ganador", resp == "OK" and "Ganador en la Nube" in salida.getvalue())
    r.check("plazo del cliente >= 10 s aunque la carrera sea de 8 s (la API rechaza menos)", plazos and all(p >= 10000 for p in plazos))
    plazos.clear()
    with contextlib.redirect_stdout(_io.StringIO()):
        ns["consultar_gemini_o_fallback"]("hola", timeout_s=30.0)
    r.check("con timeout_s=30 el plazo del cliente sube a 30000 ms", plazos and all(p == 30000 for p in plazos))

    modo["tipo"] = "error"
    ns["_ERRORES_NUBE_VISTOS"].clear()
    salida = _io.StringIO()
    with contextlib.redirect_stdout(salida):
        a = ns["consultar_gemini_o_fallback"]("hola", timeout_s=3.0)
        b = ns["consultar_gemini_o_fallback"]("hola", timeout_s=3.0)
    texto = salida.getvalue()
    r.check("nube caída: cae a Ollama en ambas consultas", a == "LOCAL" and b == "LOCAL")
    r.check("el error de la nube YA NO es silencioso (se muestra el motivo)", "modelo retirado" in texto and "[Nube]" in texto)
    r.check("cada error distinto se muestra una sola vez por (modelo, error), no en cada consulta",
            texto.count("[Nube]") <= 2 and texto.count("[Nube]") == len(ns["_ERRORES_NUBE_VISTOS"]))

    modo["tipo"] = "lento"
    t0 = time.time()
    with contextlib.redirect_stdout(_io.StringIO()):
        resp = ns["consultar_gemini_o_fallback"]("hola", timeout_s=0.5)
    r.check("workers lentos: el plazo de la carrera es REAL (cae a Ollama en ~0.5 s, no espera a los 2 s del worker)",
            resp == "LOCAL" and (time.time() - t0) < 1.5)
finally:
    genai_mod.Client = cliente_original

r.check("el pool de modelos ya no incluye el retirado 'gemini-2.5-flash'", "gemini-2.5-flash" not in cerebro_real["GEM_MODELS_POOL"])

r.terminar()
