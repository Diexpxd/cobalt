"""Pruebas del Bloque Q1 (enrutador de la nube). Sin red: proveedores falsos y reloj falso."""
import json
import os
import sys
import tempfile
import time

from _cargar import Resultados

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cerebro"))
import nox_nube as nn  # noqa: E402

r = Resultados()
tmp = tempfile.mkdtemp()


class Reloj:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def prov(nombre, respuesta=None, error=None, de_pago=False, propio_plazo=False, dormir=0.0, llamadas=None):
    def f(prompt, plazo, rol):
        if llamadas is not None:
            llamadas.append((nombre, prompt, plazo, rol))
        if dormir:
            time.sleep(dormir)
        if error:
            raise error if isinstance(error, Exception) else nn.ErrorProveedor(error)
        return respuesta
    return nn.Proveedor(nombre, f, de_pago=de_pago, propio_plazo=propio_plazo)


def enrutador(provs, **kw):
    kw.setdefault("reloj", Reloj())
    return nn.Enrutador(provs, **kw)


ll = []
e = enrutador([prov("gemini", "hola desde gemini", llamadas=ll), prov("claude", "hola desde claude", llamadas=ll), prov("local", "local", propio_plazo=True)])
res = e.preguntar("chat", "hola")
r.check("chat: el primero del orden (gemini) contesta y nadie más es llamado", res.proveedor == "gemini" and res.texto == "hola desde gemini" and len(ll) == 1)
res = e.preguntar("datos", "cuánta vida tiene el wither")
r.check("datos: Claude va primero", res.proveedor == "claude" and res.texto == "hola desde claude")

e = enrutador([prov("gemini", error="sobrecarga"), prov("claude", "respuesta de claude"), prov("local", "local", propio_plazo=True)])
res = e.preguntar("chat", "hola")
usados = [i for i in res.intentos if i["estado"] != "no_configurado"]
r.check("si el primero falla pasa al siguiente y lo anota en 'intentos'", res.proveedor == "claude" and [i["estado"] for i in usados] == ["error", "ok"] and usados[0]["tipo"] == "sobrecarga")

e = enrutador([prov("gemini", error="red"), prov("claude", error="cuota"), prov("local", "respuesta local", propio_plazo=True)])
res = e.preguntar("estudio", "x")
r.check("estudio: si fallan las dos nubes contesta el modelo local", res.proveedor == "local" and res.texto == "respuesta local")
res = e.preguntar("datos", "cuántos corazones tiene el warden")
r.check("datos: la respuesta del modelo local se marca DEGRADADA (no debe darse como dato seguro)", res.proveedor == "local" and res.degradado is True)
res = e.preguntar("estudio", "x")
r.check("estudio con el local no se marca degradado", res.degradado is False)

e = enrutador([prov("gemini", error="red"), prov("claude", error="red")])
res = e.preguntar("planos", "diseña una casa")
r.check("planos: sin 'local' en la cadena, si todo falla queda AGOTADO (el adaptador usará la plantilla) y sin texto",
        res.agotado and res.proveedor is None and sum(1 for i in res.intentos if i["estado"] == "error") == 2 and "local" not in nn.ORDEN_DEFECTO["planos"])

e = enrutador([prov("claude", "solo claude")])
res = e.preguntar("chat", "hola")
r.check("proveedores que no existen se saltan sin romper la cadena", res.proveedor == "claude" and res.intentos[0]["estado"] == "no_configurado")

try:
    e.preguntar("inventado", "x")
    r.check("rol desconocido lanza ValueError", False)
except ValueError:
    r.check("rol desconocido lanza ValueError", True)

res = enrutador([prov("gemini", "  \n "), prov("claude", "vale")]).preguntar("chat", "x")
r.check("una respuesta vacía cuenta como fallo y se pasa al siguiente", res.proveedor == "claude" and res.intentos[0]["tipo"] == "vacio")

res = enrutador([prov("gemini", error=RuntimeError("boom")), prov("claude", "vale")]).preguntar("chat", "x")
r.check("una excepción cualquiera del proveedor se convierte en fallo, no tumba al enrutador", res.proveedor == "claude" and res.intentos[0]["tipo"] == "red")

r.check("orden explícito manda sobre el de defecto", enrutador([prov("gemini", "g"), prov("claude", "c")]).preguntar("chat", "x", orden=("claude", "gemini")).proveedor == "claude")

ll = []
t0 = time.time()
e = enrutador([prov("gemini", "tarde", dormir=2.0), prov("claude", "a tiempo")], reloj=time.monotonic)
res = e.preguntar("chat", "x", plazo_s=0.3, techo_s=5)
r.check("un proveedor que no responde en su plazo se corta (~0,3 s, no espera a los 2 s) y pasa al siguiente",
        res.proveedor == "claude" and time.time() - t0 < 1.5 and res.intentos[0]["tipo"] == "timeout")
ll = []
e = enrutador([prov("gemini", "g", llamadas=ll)])
e.preguntar("planos", "x")
r.check("el plazo por defecto de planos se le pasa al proveedor (180 s)", ll[0][2] == 180.0)
ll = []
e = enrutador([prov("claude", "c", llamadas=ll)])
e.preguntar("internet", "x")
r.check("el plazo por defecto de internet es 45 s", ll[0][2] == 45.0)
r.check("plazos por defecto: chat 12, estudio 60, jefes 60, táctica 20",
        (nn.PLAZO_DEFECTO_S["chat"], nn.PLAZO_DEFECTO_S["estudio"], nn.PLAZO_DEFECTO_S["jefes"], nn.PLAZO_DEFECTO_S["tactica"]) == (12, 60, 60, 20))

class RelojAvance:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


ra = RelojAvance()
def lento(prompt, plazo, rol):
    ra.t += 40.0
    raise nn.ErrorProveedor("timeout")
e = nn.Enrutador([nn.Proveedor("gemini", lento), nn.Proveedor("claude", lento), nn.Proveedor("local", lambda p, pl, ro: "local ok", propio_plazo=True)], reloj=ra)
res = e.preguntar("tactica", "x", techo_s=30, orden=("gemini", "claude", "local"))  # techo 30 s: gemini gasta 40, claude ya no tiene tiempo
r.check("con el techo total agotado se salta a Claude ('sin_tiempo') pero el local sí contesta",
        [i["estado"] for i in res.intentos][:2] == ["error", "sin_tiempo"] and res.proveedor == "local")

rel = Reloj()
ll = []
e = nn.Enrutador([nn.Proveedor("gemini", prov("gemini", error="sobrecarga", llamadas=ll).funcion), nn.Proveedor("claude", lambda p, pl, ro: "claude")], reloj=rel, fallos_para_abrir=3, pausa_s=60)
for _ in range(3):
    e.preguntar("chat", "x")
r.check("tras 3 fallos seguidos, gemini se aparta", len(ll) == 3 and "gemini" in e.estado())
e.preguntar("chat", "x")
r.check("apartado: ya no se le llama (sigue en 3 llamadas)", len(ll) == 3)
rel.t += 61
e.preguntar("chat", "x")
r.check("pasada la pausa vuelve a intentarse", len(ll) == 4)

ok_tras = {"n": 0}
def intermitente(prompt, plazo, rol):
    ok_tras["n"] += 1
    if ok_tras["n"] < 3:
        raise nn.ErrorProveedor("sobrecarga")
    return "ya"
e = nn.Enrutador([nn.Proveedor("gemini", intermitente), nn.Proveedor("claude", lambda p, pl, ro: "claude")], reloj=Reloj(), fallos_para_abrir=3)
for _ in range(4):
    e.preguntar("chat", "x")
r.check("un éxito reinicia la cuenta de fallos (2 fallos + éxito no aparta a nadie)", "gemini" not in e.estado())

e = enrutador([prov("claude", error="auth"), prov("gemini", "g")])
e.preguntar("datos", "x")
r.check("error de autenticación: se aparta 10 min de golpe (una clave mala no se reintenta a cada pregunta)", 500 < e.estado().get("claude", 0) <= 600)
e = enrutador([prov("claude", error="config"), prov("gemini", "g")])
e.preguntar("datos", "x")
r.check("error de configuración (petición inválida): apartado 10 min", 500 < e.estado().get("claude", 0) <= 600)
e = enrutador([prov("gemini", error=nn.ErrorProveedor("cuota", espera_s=30)), prov("claude", "c")])
e.preguntar("chat", "x")
r.check("cuota con Retry-After de 30 s: apartado 30 s", 25 < e.estado().get("gemini", 0) <= 30)
e = enrutador([prov("gemini", error="cuota"), prov("claude", "c")])
e.preguntar("chat", "x")
r.check("cuota sin Retry-After: apartado 2 min por defecto", 100 < e.estado().get("gemini", 0) <= 120)

dia = {"d": "2026-09-20"}
g = nn.Gasto(os.path.join(tmp, "gasto.json"), hoy=lambda: dia["d"])
ll = []
e = enrutador([nn.Proveedor("claude", lambda p, pl, ro: (ll.append(1), {"texto": "c", "coste_usd": 0.6})[1], de_pago=True), prov("gemini", "g gratis")], gasto=g, tope_diario_usd=lambda: 1.0)
e.preguntar("datos", "x")
e.preguntar("datos", "x")
r.check("el coste de las respuestas de pago se acumula (0,6 + 0,6)", abs(g.usd_hoy() - 1.2) < 1e-9)
res = e.preguntar("datos", "x")
r.check("superado el tope diario Claude se salta ('tope_diario') y contesta el siguiente",
        res.proveedor == "gemini" and next(i for i in res.intentos if i["proveedor"] == "claude")["estado"] == "tope_diario" and len(ll) == 2)
g2 = nn.Gasto(os.path.join(tmp, "gasto.json"), hoy=lambda: dia["d"])
r.check("el gasto de hoy sobrevive a un reinicio (se lee del JSON)", abs(g2.usd_hoy() - 1.2) < 1e-9)
dia["d"] = "2026-09-21"
r.check("al cambiar de día el gasto vuelve a 0", g.usd_hoy() == 0.0 and nn.Gasto(os.path.join(tmp, "gasto.json"), hoy=lambda: dia["d"]).usd_hoy() == 0.0)
open(os.path.join(tmp, "roto.json"), "w").write("{no es json")
r.check("un JSON de gasto corrupto no rompe: empieza en 0", nn.Gasto(os.path.join(tmp, "roto.json")).usd_hoy() == 0.0)
res = enrutador([nn.Proveedor("gemini", lambda p, pl, ro: {"texto": "g", "coste_usd": 5.0}, de_pago=False)], gasto=nn.Gasto(), tope_diario_usd=lambda: 0.01).preguntar("chat", "x")
r.check("un proveedor NO de pago no cuenta contra el tope (Gemini gratis sigue respondiendo)", res.proveedor == "gemini")

pago = {"si": False}
e = enrutador([nn.Proveedor("gemini", lambda p, pl, ro: {"texto": "g", "coste_usd": 0.7}, de_pago=lambda: pago["si"]), prov("claude", "c")], gasto=nn.Gasto(), tope_diario_usd=lambda: 1.0)
e.preguntar("chat", "x")
r.check("de_pago como función: con Gemini 'gratis' su coste no se suma", e.gasto.usd_hoy() == 0.0)
pago["si"] = True
e.preguntar("chat", "x")
e.preguntar("chat", "x")
r.check("de_pago como función: al pasar a 'de pago' (configuración en vivo) el coste ya cuenta y Gemini se aparta al pasar el tope",
        abs(e.gasto.usd_hoy() - 1.4) < 1e-9 and e.preguntar("chat", "x").proveedor == "claude")
res = enrutador([prov("gemini", "g"), prov("claude", "c")]).preguntar("chat", "x", orden=())
r.check("un orden vacío (sin ningún proveedor configurado) da AGOTADO, no vuelve al orden por defecto", res.agotado and res.intentos == [])

visto = []
def prompt_fn(nombre):
    visto.append(nombre)
    return f"prompt para {nombre}"
ll = []
e = enrutador([prov("claude", "c", llamadas=ll), prov("gemini", "g", llamadas=ll)])
e.preguntar("internet", prompt_fn)
r.check("el prompt se prepara solo para el proveedor al que se llama (no se busca en internet si Claude ya contesta)", visto == ["claude"] and ll[0][1] == "prompt para claude")
e = enrutador([prov("claude", error="red", llamadas=ll), prov("gemini", "g", llamadas=ll)])
visto.clear()
e.preguntar("internet", prompt_fn)
r.check("si Claude falla, el prompt de Gemini se prepara después", visto == ["claude", "gemini"])
def prompt_roto(nombre):
    if nombre == "claude":
        raise RuntimeError("sin red para buscar")
    return "ok"
res = enrutador([prov("claude", "c"), prov("gemini", "g")]).preguntar("internet", prompt_roto)
r.check("si preparar el prompt de un proveedor falla, se sigue con el siguiente",
        res.proveedor == "gemini" and next(i for i in res.intentos if i["proveedor"] == "claude")["estado"] == "prompt_fallido")
res = enrutador([prov("claude", "c"), prov("gemini", "g")]).preguntar("internet", lambda n: "" if n == "claude" else "pregunta")
r.check("un prompt vacío para un proveedor lo salta", res.proveedor == "gemini")

reg_archivo = os.path.join(tmp, "registro.jsonl")
e = enrutador([nn.Proveedor("claude", lambda p, pl, ro: {"texto": "RESPUESTA SECRETA", "tokens_in": 10, "tokens_out": 5, "coste_usd": 0.001}, de_pago=True)],
              registro=nn.Registro(reg_archivo), gasto=nn.Gasto())
e.preguntar("datos", "PREGUNTA CONFIDENCIAL con clave AIzaSy" + "X" * 34)
crudo = open(reg_archivo, encoding="utf-8").read()
linea = json.loads(crudo.strip().splitlines()[-1])
r.check("el registro anota rol, proveedor, ok, tiempo, tokens y coste", linea["rol"] == "datos" and linea["proveedor"] == "claude" and linea["ok"] is True and linea["tokens_out"] == 5 and linea["coste_usd"] == 0.001)
r.check("el registro NO contiene el prompt, ni la respuesta, ni claves", "CONFIDENCIAL" not in crudo and "SECRETA" not in crudo and "AIza" not in crudo)
e = enrutador([prov("claude", error="cuota")], registro=nn.Registro(reg_archivo))
e.preguntar("datos", "x")
r.check("los fallos también se anotan (ok=false y el tipo de error)", json.loads(open(reg_archivo, encoding="utf-8").read().strip().splitlines()[-1])["error"] == "cuota")
pequeno = os.path.join(tmp, "rot.jsonl")
rg = nn.Registro(pequeno, max_bytes=200)
for i in range(30):
    rg.anotar(rol="chat", proveedor="gemini", ok=True, i=i)
r.check("el registro rota al pasar del tamaño máximo (no crece sin límite)", os.path.exists(pequeno + ".1") and os.path.getsize(pequeno) < 1000)

r.check("parse_orden acepta comas y espacios y respeta el orden", nn.parse_orden("claude, gemini ,local", ("gemini",)) == ("claude", "gemini", "local"))
r.check("parse_orden descarta desconocidos y repetidos", nn.parse_orden("gpt,claude,claude,local", ("gemini",)) == ("claude", "local"))
r.check("parse_orden con basura -> orden por defecto", nn.parse_orden("???", ("gemini", "local")) == ("gemini", "local") and nn.parse_orden(None, ("gemini",)) == ("gemini",))

rel = Reloj()
ro = nn.RotorClaves(3, reloj=rel)
r.check("rota las claves de una en una (no la carrera de todas a la vez)", [ro.siguiente() for _ in range(4)] == [0, 1, 2, 0])
ro.enfriar(1, 60)
r.check("una clave enfriada (429) se salta", [ro.siguiente() for _ in range(3)] == [2, 0, 2])
rel.t += 61
r.check("pasado el enfriamiento la clave vuelve", 1 in [ro.siguiente() for _ in range(3)])
ro2 = nn.RotorClaves(2, reloj=rel)
ro2.enfriar(0, 60), ro2.enfriar(1, 60)
r.check("si todas descansan devuelve None", ro2.siguiente() is None and nn.RotorClaves(0).siguiente() is None)

uso = {"input_tokens": 1000, "output_tokens": 200, "cache_read_input_tokens": 0, "server_tool_use": {"web_search_requests": 2}}
r.check("coste de Claude Sonnet 5 = 1000·$2 + 200·$10 por millón + 2 búsquedas a $0,01", abs(nn.coste_claude("claude-sonnet-5", uso) - (0.002 + 0.002 + 0.02)) < 1e-9)
r.check("coste con caché: la lectura cuesta el 10 % y la escritura el 125 %",
        abs(nn.coste_claude("claude-sonnet-5", {"cache_read_input_tokens": 1_000_000}) - 0.2) < 1e-9 and abs(nn.coste_claude("claude-sonnet-5", {"cache_creation_input_tokens": 1_000_000}) - 2.5) < 1e-9)
r.check("modelo desconocido: se estima con el precio de Sonnet (nunca a 0)", nn.coste_claude("claude-inventado", {"output_tokens": 1_000_000}) == 10.0)
r.check("coste de Gemini 3.6 flash con los tokens de pensar sumados a la salida", abs(nn.coste_gemini("gemini-3.6-flash", 2000, 500) - (2000 * 0.75 + 500 * 3.75) / 1e6) < 1e-12)

p = nn.claude_peticion("claude-sonnet-5", "hola", sistema="Eres Cobalt", max_tokens=300)
r.check("petición básica: modelo, max_tokens, system, un mensaje de usuario y SIN herramientas ni temperature",
        p == {"model": "claude-sonnet-5", "max_tokens": 300, "messages": [{"role": "user", "content": "hola"}], "system": "Eres Cobalt"})
p = nn.claude_peticion("claude-sonnet-5", "clima", busqueda=True, max_busquedas=2, ubicacion={"city": "Springfield", "region": "Illinois", "country": "US", "timezone": "America/Chicago"})
h = p["tools"][0]
r.check("con búsqueda: herramienta web_search_20250305, max_uses y ubicación aproximada",
        h["type"] == "web_search_20250305" and h["name"] == "web_search" and h["max_uses"] == 2 and h["user_location"]["type"] == "approximate" and h["user_location"]["country"] == "US")

respuesta_ok = {"content": [{"type": "text", "text": "Hola "}, {"type": "text", "text": "mundo"}], "stop_reason": "end_turn", "usage": {"input_tokens": 50, "output_tokens": 10}}
respuesta_busqueda = {"content": [{"type": "text", "text": "Voy a buscar."}, {"type": "server_tool_use", "id": "s1", "name": "web_search", "input": {"query": "x"}},
                                  {"type": "web_search_tool_result", "tool_use_id": "s1", "content": [{"type": "web_search_result", "url": "https://minecraft.wiki/w/Java_Edition_26.3", "title": "t"}]},
                                  {"type": "text", "text": "La versión es la 26.3.", "citations": []}],
                      "stop_reason": "end_turn", "usage": {"input_tokens": 6000, "output_tokens": 300, "server_tool_use": {"web_search_requests": 1}}}


class Falso:
    def __init__(self, respuestas):
        self.respuestas, self.peticiones = list(respuestas), []

    def __call__(self, url, cabeceras, cuerpo, timeout):
        self.peticiones.append((url, cabeceras, json.loads(json.dumps(cuerpo)), timeout))
        return self.respuestas.pop(0)


f = Falso([(200, respuesta_ok, {})])
d = nn.claude_consultar(f, "CLAVE-FALSA", "claude-sonnet-5", "hola", plazo_s=12)
url, cab, cuerpo, to = f.peticiones[0]
r.check("va a la URL de la Messages API con x-api-key, anthropic-version y content-type", url == "https://api.anthropic.com/v1/messages" and cab["x-api-key"] == "CLAVE-FALSA" and cab["anthropic-version"] == "2023-06-01" and cab["content-type"] == "application/json")
r.check("une los bloques de texto y calcula tokens y coste", d["texto"] == "Hola mundo" and d["tokens_in"] == 50 and d["tokens_out"] == 10 and abs(d["coste_usd"] - (50 * 2 + 10 * 10) / 1e6) < 1e-12)
r.check("el plazo se pasa al POST", to == 12)
f = Falso([(200, respuesta_busqueda, {})])
d = nn.claude_consultar(f, "K", "claude-sonnet-5", "versión?", busqueda=True)
r.check("con búsqueda: devuelve solo el texto final, cuenta 1 búsqueda ($0,01 en el coste) y guarda las fuentes",
        d["texto"] == "Voy a buscar.La versión es la 26.3." and d["busquedas"] == 1 and d["fuentes"] == ["https://minecraft.wiki/w/Java_Edition_26.3"] and d["coste_usd"] > 0.01)

pausa = {"content": [{"type": "server_tool_use", "id": "s2", "name": "web_search", "input": {"query": "q"}}], "stop_reason": "pause_turn", "usage": {"input_tokens": 100, "output_tokens": 5, "server_tool_use": {"web_search_requests": 1}}}
final = {"content": [{"type": "text", "text": "Listo."}], "stop_reason": "end_turn", "usage": {"input_tokens": 200, "output_tokens": 7}}
f = Falso([(200, pausa, {}), (200, final, {})])
d = nn.claude_consultar(f, "K", "claude-sonnet-5", "q", busqueda=True)
r.check("pause_turn: se continúa devolviendo el turno del asistente tal cual y se SUMAN los usos", d["texto"] == "Listo." and len(f.peticiones) == 2 and d["tokens_in"] == 300 and d["busquedas"] == 1
        and f.peticiones[1][2]["messages"][1] == {"role": "assistant", "content": pausa["content"]})
f = Falso([(200, pausa, {})] * 5)
try:
    nn.claude_consultar(f, "K", "claude-sonnet-5", "q", busqueda=True, max_pausas=2)
    r.check("un turno que sigue pausado tras varias continuaciones acaba en error 'vacio'", False)
except nn.ErrorProveedor as ex:
    r.check("un turno que sigue pausado tras varias continuaciones acaba en error 'vacio' (3 peticiones como máximo)", ex.tipo == "vacio" and len(f.peticiones) == 3)

sin_texto = {"content": [{"type": "web_search_tool_result", "tool_use_id": "s", "content": {"type": "web_search_tool_result_error", "error_code": "max_uses_exceeded"}}], "stop_reason": "end_turn", "usage": {}}
try:
    nn.claude_consultar(Falso([(200, sin_texto, {})]), "K", "claude-sonnet-5", "q", busqueda=True)
    r.check("200 sin texto (búsqueda fallida) -> error 'vacio' con el motivo", False)
except nn.ErrorProveedor as ex:
    r.check("200 sin texto (búsqueda fallida) -> error 'vacio' con el motivo", ex.tipo == "vacio" and "max_uses_exceeded" in str(ex))

for status, tipo in [(401, "auth"), (403, "auth"), (429, "cuota"), (529, "sobrecarga"), (500, "sobrecarga"), (400, "config"), (404, "config"), (418, "red")]:
    try:
        nn.claude_consultar(Falso([(status, {"error": {"type": "x", "message": "m"}}, {})]), "K", "claude-sonnet-5", "q")
        r.check(f"HTTP {status} -> {tipo}", False)
    except nn.ErrorProveedor as ex:
        r.check(f"HTTP {status} -> error '{tipo}'", ex.tipo == tipo)
try:
    nn.claude_consultar(Falso([(429, {"error": {"type": "rate_limit_error"}}, {"retry-after": "17"})]), "K", "claude-sonnet-5", "q")
except nn.ErrorProveedor as ex:
    r.check("429 con Retry-After: la espera pedida por la API se respeta", ex.espera_s == 17.0)
try:
    nn.claude_consultar(Falso([(401, {"error": {"type": "authentication_error", "message": "invalid x-api-key CLAVE-FALSA"}}, {})]), "CLAVE-FALSA", "claude-sonnet-5", "q")
except nn.ErrorProveedor as ex:
    r.check("el mensaje del error de autenticación no incluye el texto devuelto por la API (que podría eco de la clave)", "CLAVE-FALSA" not in str(ex))

si = ["¿Cuántos puntos de vida tiene el Warden?", "cuál es la receta del pico de hierro", "¿Cómo se cura a un aldeano zombi?", "¿Qué necesito para hacer una baliza?",
      "Dónde se encuentra la netherita", "¿Para qué sirve el yunque?"]
no = ["ven aquí", "¿Cómo estás?", "construye una casa de piedra", "mina hierro por favor", "¿Qué tal el día?", "hola cobalt", "sígueme, ¿cuántos zombis ves?",
      "", None, "¿Qué?", "¿Cuál es tu nombre?", "a" * 400, 42]
r.check("reconoce preguntas de datos de Minecraft: " + str([m for m in si if not nn.es_pregunta_de_datos(m)]), all(nn.es_pregunta_de_datos(m) for m in si))
r.check("NO confunde órdenes ni charla con datos: " + str([m for m in no if nn.es_pregunta_de_datos(m)]), not any(nn.es_pregunta_de_datos(m) for m in no))

real_internet = ("La última versión estable de Minecraft Java Edition es la **26.3**, que salió el **15 de septiembre de 2026**. La anterior fue la 26.2.\n\n"
                 "Sources:\n- [Java Edition 26.3 – Minecraft Wiki](https://minecraft.wiki/w/Java_Edition_26.3)\n- [Version history](https://minecraft.wiki/w/Java_Edition_version_history)")
limpio = nn.limpiar_para_chat(real_internet)
r.check("quita la lista de fuentes, los enlaces y el markdown: " + repr(limpio), limpio == "La última versión estable de Minecraft Java Edition es la 26.3, que salió el 15 de septiembre de 2026. La anterior fue la 26.2.")
smoji = nn.limpiar_para_chat("El Warden tiene **500 puntos de vida** (250 corazones). Mejor evitarlo con sigilo. " + chr(0x1F92B))
r.check("quita emojis y deja el resto: " + repr(smoji), smoji == "El Warden tiene 500 puntos de vida (250 corazones). Mejor evitarlo con sigilo.")
r.check("convierte [texto](url) en texto y borra URLs sueltas", nn.limpiar_para_chat("Mira [la wiki](https://x.org/a) o https://y.org/b ahora") == "Mira la wiki o ahora")
r.check("quita viñetas y junta líneas", nn.limpiar_para_chat("- uno\n- dos\n* tres") == "uno dos tres")
r.check("'Fuentes:' en español también corta", nn.limpiar_para_chat("Cuesta 17,2 pesos.\n\nFuentes:\n- x") == "Cuesta 17,2 pesos.")
largo = ("Esta es una frase de prueba bastante larga para comprobar el corte. " * 8).strip()
corte = nn.limpiar_para_chat(largo, maximo=240)
r.check("recorta a 240 caracteres como máximo y termina en un punto (frase completa)", len(corte) <= 240 and corte.endswith("."))
r.check("sin puntos que respeten el mínimo, corta en palabra y añade '...'", nn.limpiar_para_chat("palabra " * 80, maximo=100).endswith("...") and len(nn.limpiar_para_chat("palabra " * 80, maximo=100)) <= 103)
r.check("vacío o None -> vacío", nn.limpiar_para_chat("") == "" and nn.limpiar_para_chat(None) == "")
r.check("un texto corto y limpio no cambia", nn.limpiar_para_chat("Son 500 puntos de vida.") == "Son 500 puntos de vida.")
r.check("los prompts piden no usar emojis, enlaces ni fuentes; el sistema pide un tono natural y directo, ni servil ni exagerado",
        "sin emojis" in nn.prompt_datos("q") and "sin enlaces" in nn.prompt_internet_claude("q") and "sin emojis" in nn.sistema_cobalt("hoy")
        and "ni servil ni exagerado" in nn.sistema_cobalt("hoy"))

internet_si = ["¿cuánto cuesta un dólar hoy?", "qué clima hace hoy en Springfield", "cuál es la última versión de minecraft java", "qué pasó esta semana en el mundo de minecraft",
               "busca cómo hacer una granja de hierro", "dime un tutorial para derrotar al warden", "quién ganó el partido de ayer", "cuál es el precio del bitcoin",
               "qué noticias hay hoy", "¿va a llover mañana?", "cuándo sale la próxima actualización de minecraft", "cuánto está el euro",
               "dame el precio del dólar", "busca información sobre el warden", "mira en internet cómo se hace", "qué actualización nueva salió", "¿hay una versión reciente?"]
internet_no = ["sígueme por favor", "mina hierro", "hola cobalt", "guarda este lugar como base", "construye una casa de piedra", "ven aquí", "defiéndeme de los zombis",
               "¿cómo estás?", "qué ves", "recoge la madera de aquí", "vuela hacia mí", "cuánta vida te queda", "busca diamantes", "busca hierro por aquí", "busca un lugar para dormir",
               "mina carbón y tráemelo", "dame 32 bloques de piedra", "pon una antorcha aquí", "cambia a modo creativo", "pon el clima soleado", "quita el escudo", "abre el cofre",
               "cuántos corazones tienes", "qué hora es en el juego", "¿cuánta vida tiene el warden?", "construye la nueva torre", "la siguiente casa la hacemos de madera",
               "esta semana construimos", "hoy vamos a minar", "la actualización de mi mod está lista", "gracias cobalt", "estoy aburrido", "", None, 42, "ok", "a" * 500]
r.check("necesita_internet: detecta las preguntas de internet " + str([m for m in internet_si if not nn.necesita_internet(m)]), all(nn.necesita_internet(m) for m in internet_si))
r.check("necesita_internet: NO se activa con órdenes ni charla (incluido 'busca diamantes' y 'pon el clima soleado') " + str([m for m in internet_no if nn.necesita_internet(m)]),
        not any(nn.necesita_internet(m) for m in internet_no))

r.check("el prompt de fragmentos exige decir 'no pude comprobarlo' si los datos se contradicen (lo que hizo inventar a Gemini con la 'Caelum Update')",
        "contradicen" in nn.prompt_internet_fragmentos("q", "f") and "no pudiste comprobarlo" in nn.prompt_internet_fragmentos("q", "f"))
r.check("el prompt de Claude para internet pide no inventar", "no inventes" in nn.prompt_internet_claude("q"))
r.check("el sistema de Cobalt incluye la fecha de hoy", "20 de septiembre de 2026" in nn.sistema_cobalt("20 de septiembre de 2026"))

r.terminar()
