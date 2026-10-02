"""Bloque Q1: enrutador de la nube. PURO: sin red ni Minecraft, se prueba con proveedores falsos."""
import datetime
import json
import os
import queue
import re
import threading
import time

ROLES = ("chat", "datos", "internet", "planos", "estudio", "jefes", "tactica")
ORDEN_DEFECTO = {
    "chat": ("gemini", "claude", "local"),
    "datos": ("claude", "gemini", "local"),
    "internet": ("claude", "gemini", "local"),
    "planos": ("claude", "gemini"),  # sin 'local': si todo falla, el adaptador usa la plantilla de código
    "estudio": ("gemini", "claude", "local"),
    "jefes": ("gemini", "claude", "local"),
    "tactica": ("gemini", "claude", "local"),
}
PLAZO_DEFECTO_S = {"chat": 12, "datos": 12, "internet": 45, "planos": 180, "estudio": 60, "jefes": 60, "tactica": 20}
TECHO_TOTAL_S = {"chat": 30, "datos": 30, "internet": 90, "planos": 400, "estudio": 130, "jefes": 130, "tactica": 45}
MAX_TOKENS = {"chat": 300, "datos": 300, "internet": 500, "planos": 12000, "estudio": 300, "jefes": 500, "tactica": 300}
ROLES_FACTUALES = ("datos", "internet")
PROVEEDORES_CONOCIDOS = ("gemini", "claude", "local")

PRECIOS_CLAUDE = {"claude-sonnet-5": (2.0, 10.0), "claude-haiku-4-5-20251001": (1.0, 5.0), "claude-opus-5": (5.0, 25.0)}  # USD por millón de tokens (entrada, salida)
PRECIO_BUSQUEDA_CLAUDE_USD = 0.01
PRECIOS_GEMINI = {"gemini-3.6-flash": (0.75, 3.75), "gemini-3.7-flash": (0.75, 3.75), "gemini-3.8-flash": (0.75, 3.75),
                  "gemini-3.5-flash": (1.5, 9.0), "gemini-3.1-pro-preview": (2.0, 12.0), "gemini-3.1-flash-lite": (0.25, 1.5)}

TIPOS_ERROR = ("cuota", "sobrecarga", "timeout", "red", "auth", "config", "vacio")
PAUSA_LARGA_S = 600.0  # 'auth' y 'config' no se arreglan solos: mejor no insistir cada llamada


class ErrorProveedor(Exception):
    """Un proveedor falló."""

    def __init__(self, tipo, mensaje="", espera_s=None):
        super().__init__(mensaje or tipo)
        self.tipo = tipo if tipo in TIPOS_ERROR else "red"
        self.espera_s = espera_s


def parse_orden(texto, defecto):
    """'gemini, claude ,local' -> ('gemini','claude','local')."""
    if not isinstance(texto, str):
        return tuple(defecto)
    visto = []
    for parte in re.split(r"[,;\s]+", texto.strip().lower()):
        if parte in PROVEEDORES_CONOCIDOS and parte not in visto:
            visto.append(parte)
    return tuple(visto) if visto else tuple(defecto)


def coste_claude(modelo, uso):
    """USD de una respuesta de Claude a partir del bloque 'usage' de la API (tokens, caché y búsquedas web)."""
    p_in, p_out = PRECIOS_CLAUDE.get(modelo, PRECIOS_CLAUDE["claude-sonnet-5"])
    entrada = (uso.get("input_tokens") or 0) * p_in
    entrada += (uso.get("cache_read_input_tokens") or 0) * p_in * 0.1
    entrada += (uso.get("cache_creation_input_tokens") or 0) * p_in * 1.25
    salida = (uso.get("output_tokens") or 0) * p_out
    busquedas = ((uso.get("server_tool_use") or {}).get("web_search_requests") or 0) * PRECIO_BUSQUEDA_CLAUDE_USD
    return (entrada + salida) / 1e6 + busquedas


def coste_gemini(modelo, tokens_in, tokens_out_total):
    """USD de una respuesta de Gemini de pago. Los tokens de 'pensar' se cobran como salida: pásalos ya sumados."""
    p_in, p_out = PRECIOS_GEMINI.get(modelo, (1.5, 9.0))
    return ((tokens_in or 0) * p_in + (tokens_out_total or 0) * p_out) / 1e6


class Gasto:
    """Dólares gastados HOY en proveedores de pago, persistidos en un JSON (se reinicia solo al cambiar de día)."""

    def __init__(self, archivo=None, hoy=None):
        self.archivo = archivo
        self.hoy = hoy or (lambda: datetime.date.today().isoformat())
        self._lock = threading.Lock()
        self._dia, self._usd = self.hoy(), 0.0
        if archivo and os.path.exists(archivo):
            try:
                with open(archivo, encoding="utf-8") as f:
                    d = json.load(f)
                if d.get("dia") == self._dia:
                    self._usd = float(d.get("usd", 0.0))
            except (OSError, ValueError, TypeError):
                pass

    def usd_hoy(self):
        with self._lock:
            self._rodar()
            return self._usd

    def sumar(self, usd):
        with self._lock:
            self._rodar()
            self._usd += max(0.0, float(usd or 0.0))
            self._guardar()

    def _rodar(self):
        if self.hoy() != self._dia:
            self._dia, self._usd = self.hoy(), 0.0

    def _guardar(self):
        if not self.archivo:
            return
        try:
            tmp = self.archivo + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"dia": self._dia, "usd": round(self._usd, 6)}, f)
            os.replace(tmp, self.archivo)
        except OSError:
            pass  # el gasto en memoria sigue valiendo aunque el disco falle


class Registro:
    """Una línea JSON por llamada (rol, proveedor, éxito, tiempo, tokens, coste)."""

    def __init__(self, archivo=None, max_bytes=2_000_000):
        self.archivo, self.max_bytes = archivo, max_bytes
        self._lock = threading.Lock()

    def anotar(self, **campos):
        if not self.archivo:
            return
        campos["t"] = datetime.datetime.now().isoformat(timespec="seconds")
        with self._lock:
            try:
                if os.path.exists(self.archivo) and os.path.getsize(self.archivo) > self.max_bytes:
                    os.replace(self.archivo, self.archivo + ".1")
                with open(self.archivo, "a", encoding="utf-8") as f:
                    f.write(json.dumps(campos, ensure_ascii=False) + "\n")
            except OSError:
                pass


class RotorClaves:
    def __init__(self, cuantas, reloj=time.monotonic):
        self.cuantas, self.reloj = cuantas, reloj
        self._i, self._enfriando = 0, {}
        self._lock = threading.Lock()

    def siguiente(self):
        with self._lock:
            ahora = self.reloj()
            for paso in range(self.cuantas):
                i = (self._i + paso) % self.cuantas
                if self._enfriando.get(i, 0) <= ahora:
                    self._i = (i + 1) % self.cuantas
                    return i
            return None

    def enfriar(self, indice, segundos):
        with self._lock:
            self._enfriando[indice] = self.reloj() + max(0.0, segundos)


class Proveedor:
    """funcion(prompt, plazo_s, rol) -> str | dict(texto, tokens_in, tokens_out, coste_usd)."""

    def __init__(self, nombre, funcion, de_pago=False, propio_plazo=False):
        self.nombre, self.funcion, self.de_pago, self.propio_plazo = nombre, funcion, de_pago, propio_plazo


def _es_de_pago(prov):
    return bool(prov.de_pago() if callable(prov.de_pago) else prov.de_pago)


class Resultado:
    def __init__(self, texto="", proveedor=None, degradado=False, intentos=None, seg=0.0, coste_usd=0.0):
        self.texto, self.proveedor, self.degradado = texto, proveedor, degradado
        self.intentos, self.seg, self.coste_usd = intentos or [], seg, coste_usd

    @property
    def agotado(self):
        return not self.texto

    def __repr__(self):
        return f"Resultado({self.proveedor!r}, degradado={self.degradado}, texto={self.texto[:30]!r}, intentos={len(self.intentos)})"


class Enrutador:
    def __init__(self, proveedores, *, reloj=time.monotonic, gasto=None, tope_diario_usd=lambda: 1.0, registro=None,
                 fallos_para_abrir=3, pausa_s=60.0):
        self.proveedores = {p.nombre: p for p in proveedores}
        self.reloj, self.gasto, self.tope, self.registro = reloj, gasto or Gasto(), tope_diario_usd, registro or Registro()
        self.fallos_para_abrir, self.pausa_s = fallos_para_abrir, pausa_s
        self._fallos, self._abierto_hasta = {}, {}
        self._lock = threading.Lock()

    def _motivo_bloqueo(self, prov):
        with self._lock:
            hasta = self._abierto_hasta.get(prov.nombre, 0.0)
        if hasta > self.reloj():
            return "apartado_temporalmente"
        if _es_de_pago(prov) and self.gasto.usd_hoy() >= self.tope():
            return "tope_diario"
        return None

    def _exito(self, nombre):
        with self._lock:
            self._fallos[nombre] = 0
            self._abierto_hasta.pop(nombre, None)

    def _fallo(self, nombre, err):
        with self._lock:
            self._fallos[nombre] = self._fallos.get(nombre, 0) + 1
            if err.tipo in ("auth", "config"):
                pausa = PAUSA_LARGA_S
            elif err.tipo == "cuota":
                pausa = min(PAUSA_LARGA_S, err.espera_s or 120.0)
            elif self._fallos[nombre] >= self.fallos_para_abrir:
                pausa = self.pausa_s
            else:
                pausa = 0.0
            if pausa:
                self._abierto_hasta[nombre] = self.reloj() + pausa

    def estado(self):
        ahora = self.reloj()
        with self._lock:
            return {n: round(h - ahora, 1) for n, h in self._abierto_hasta.items() if h > ahora}

    def _llamar(self, prov, prompt, plazo_s, rol):
        if prov.propio_plazo:
            return prov.funcion(prompt, plazo_s, rol)
        salida = queue.Queue()

        def trabajo():
            try:
                salida.put(("ok", prov.funcion(prompt, plazo_s, rol)))
            except BaseException as e:  # noqa: BLE001 - se devuelve al hilo que espera
                salida.put(("error", e))

        threading.Thread(target=trabajo, daemon=True).start()
        try:
            tipo, valor = salida.get(timeout=max(0.05, plazo_s))
        except queue.Empty:
            raise ErrorProveedor("timeout", f"{prov.nombre}: sin respuesta en {plazo_s:g} s")
        if tipo == "error":
            raise valor if isinstance(valor, ErrorProveedor) else ErrorProveedor("red", f"{type(valor).__name__}: {str(valor)[:120]}")
        return valor

    def preguntar(self, rol, prompt, *, orden=None, plazo_s=None, techo_s=None):
        if rol not in ROLES:
            raise ValueError(f"rol desconocido: {rol!r}")
        orden = tuple(ORDEN_DEFECTO[rol] if orden is None else orden)  # un orden VACÍO (sin claves configuradas) = agotado, no "el de siempre"
        plazo = float(plazo_s if plazo_s is not None else PLAZO_DEFECTO_S[rol])
        techo = float(techo_s if techo_s is not None else max(TECHO_TOTAL_S[rol], plazo))
        t0 = self.reloj()
        intentos = []
        for nombre in orden:
            prov = self.proveedores.get(nombre)
            if prov is None:
                intentos.append({"proveedor": nombre, "estado": "no_configurado"})
                continue
            motivo = self._motivo_bloqueo(prov)
            if motivo:
                intentos.append({"proveedor": nombre, "estado": motivo})
                continue
            restante = techo - (self.reloj() - t0)
            if restante <= 0 and not prov.propio_plazo:
                intentos.append({"proveedor": nombre, "estado": "sin_tiempo"})
                continue
            try:
                texto_prompt = prompt(nombre) if callable(prompt) else prompt
            except Exception as e:  # noqa: BLE001 - preparar el prompt no debe tumbar la cadena
                intentos.append({"proveedor": nombre, "estado": "prompt_fallido", "detalle": type(e).__name__})
                continue
            if not texto_prompt:
                intentos.append({"proveedor": nombre, "estado": "sin_prompt"})
                continue
            t1 = self.reloj()
            try:
                bruto = self._llamar(prov, texto_prompt, min(plazo, max(1.0, restante)) if not prov.propio_plazo else plazo, rol)
                datos = bruto if isinstance(bruto, dict) else {"texto": bruto}
                texto = str(datos.get("texto") or "").strip()
                if not texto:
                    raise ErrorProveedor("vacio", f"{nombre}: respuesta vacía")
            except ErrorProveedor as err:
                seg = round(self.reloj() - t1, 2)
                self._fallo(nombre, err)
                intentos.append({"proveedor": nombre, "estado": "error", "tipo": err.tipo, "seg": seg})
                self.registro.anotar(rol=rol, proveedor=nombre, ok=False, error=err.tipo, seg=seg)
                continue
            seg = round(self.reloj() - t1, 2)
            coste = float(datos.get("coste_usd") or 0.0)
            if _es_de_pago(prov) and coste:
                self.gasto.sumar(coste)
            self._exito(nombre)
            intentos.append({"proveedor": nombre, "estado": "ok", "seg": seg})
            self.registro.anotar(rol=rol, proveedor=nombre, ok=True, seg=seg, tokens_in=datos.get("tokens_in"),
                                 tokens_out=datos.get("tokens_out"), coste_usd=round(coste, 6), busquedas=datos.get("busquedas"),
                                 coste_lista_usd=datos.get("coste_lista_usd"))
            return Resultado(texto, nombre, degradado=(nombre == "local" and rol in ROLES_FACTUALES), intentos=intentos,
                             seg=round(self.reloj() - t0, 2), coste_usd=coste)
        return Resultado("", None, intentos=intentos, seg=round(self.reloj() - t0, 2))


CLAUDE_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_VERSION_API = "2023-06-01"
HERRAMIENTA_BUSQUEDA = "web_search_20250305"


def claude_peticion(modelo, prompt, *, sistema=None, max_tokens=400, busqueda=False, max_busquedas=3, ubicacion=None, mensajes=None):
    cuerpo = {"model": modelo, "max_tokens": int(max_tokens), "messages": mensajes or [{"role": "user", "content": prompt}]}
    if sistema:
        cuerpo["system"] = sistema
    if busqueda:
        herramienta = {"type": HERRAMIENTA_BUSQUEDA, "name": "web_search", "max_uses": int(max_busquedas)}
        if ubicacion:
            herramienta["user_location"] = dict(ubicacion, type="approximate")
        cuerpo["tools"] = [herramienta]
    return cuerpo


def claude_error_http(status, cuerpo, retry_after=None):
    """Convierte un error HTTP de la API en ErrorProveedor (los códigos vienen de la documentación oficial de la Messages API)."""
    tipo_api = ((cuerpo or {}).get("error") or {}).get("type", "") if isinstance(cuerpo, dict) else ""
    espera = None
    try:
        espera = float(retry_after) if retry_after is not None else None
    except (TypeError, ValueError):
        pass
    if status in (401, 403):
        return ErrorProveedor("auth", f"claude {status} {tipo_api}")
    if status == 429:
        return ErrorProveedor("cuota", "claude 429 rate_limit", espera)
    if status in (529, 503, 500, 502, 504):
        return ErrorProveedor("sobrecarga", f"claude {status} {tipo_api}")
    if status in (400, 404, 413, 422):
        return ErrorProveedor("config", f"claude {status} {tipo_api}: {str(((cuerpo or {}).get('error') or {}).get('message', ''))[:160]}")
    return ErrorProveedor("red", f"claude {status}")


def claude_interpretar(cuerpo):
    """Respuesta 200 -> {'texto', 'uso', 'busquedas', 'fuentes', 'parada', 'contenido'}."""
    contenido = cuerpo.get("content") or []
    texto = "".join(b.get("text", "") for b in contenido if isinstance(b, dict) and b.get("type") == "text").strip()
    fuentes, errores_busqueda = [], []
    for b in contenido:
        if not isinstance(b, dict):
            continue
        if b.get("type") == "web_search_tool_result":
            c = b.get("content")
            if isinstance(c, dict) and c.get("type") == "web_search_tool_result_error":
                errores_busqueda.append(c.get("error_code", "?"))
            elif isinstance(c, list):
                fuentes += [r.get("url") for r in c if isinstance(r, dict) and r.get("url")]
    uso = cuerpo.get("usage") or {}
    return {"texto": texto, "uso": uso, "busquedas": (uso.get("server_tool_use") or {}).get("web_search_requests", 0),
            "fuentes": fuentes[:8], "errores_busqueda": errores_busqueda, "parada": cuerpo.get("stop_reason"), "contenido": contenido}


def _sumar_uso(a, b):
    total = dict(a)
    for k in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
        total[k] = (a.get(k) or 0) + (b.get(k) or 0)
    total["server_tool_use"] = {"web_search_requests": ((a.get("server_tool_use") or {}).get("web_search_requests", 0)
                                                        + (b.get("server_tool_use") or {}).get("web_search_requests", 0))}
    return total


def claude_consultar(post, clave, modelo, prompt, *, sistema=None, max_tokens=400, busqueda=False, max_busquedas=3, ubicacion=None,
                     plazo_s=30.0, max_pausas=2):
    """Llama a Claude."""
    cabeceras = {"x-api-key": clave, "anthropic-version": CLAUDE_VERSION_API, "content-type": "application/json"}
    mensajes = [{"role": "user", "content": prompt}]
    uso_total, fuentes, busquedas = {}, [], 0
    for _ in range(max_pausas + 1):
        cuerpo = claude_peticion(modelo, prompt, sistema=sistema, max_tokens=max_tokens, busqueda=busqueda,
                                 max_busquedas=max_busquedas, ubicacion=ubicacion, mensajes=mensajes)
        status, resp, h = post(CLAUDE_URL, cabeceras, cuerpo, plazo_s)
        if status != 200:
            raise claude_error_http(status, resp, (h or {}).get("retry-after"))
        r = claude_interpretar(resp)
        uso_total = _sumar_uso(uso_total, r["uso"])
        fuentes += r["fuentes"]
        busquedas += r["busquedas"] or 0
        if r["parada"] == "pause_turn":
            mensajes = mensajes + [{"role": "assistant", "content": r["contenido"]}]  # la API exige devolverlo tal cual
            continue
        if not r["texto"]:
            detalle = ",".join(r["errores_busqueda"]) or "sin texto"
            raise ErrorProveedor("vacio", f"claude: {detalle}")
        return {"texto": r["texto"], "tokens_in": (uso_total.get("input_tokens") or 0) + (uso_total.get("cache_read_input_tokens") or 0),
                "tokens_out": uso_total.get("output_tokens"), "coste_usd": coste_claude(modelo, uso_total), "busquedas": busquedas,
                "fuentes": fuentes[:8]}
    raise ErrorProveedor("vacio", "claude: el turno siguió pausado tras varias continuaciones")


def sistema_cobalt(hoy):
    return (f"Eres Cobalt, un compañero de aventuras en Minecraft Java 1.20.1: aliado inteligente, directo y natural, ni servil ni exagerado. "
            f"Hoy es {hoy}. Responde en español, en 1-2 frases, sin emojis, sin listas, sin enlaces ni fuentes.")


def prompt_datos(mensaje):
    return (f'El jugador pregunta sobre Minecraft: "{mensaje}"\nResponde con el dato exacto en 1-2 frases, sin añadidos, sin emojis. '
            "Si no estás seguro de una cifra o receta, dilo claramente en lugar de inventarla.")


def prompt_internet_claude(mensaje):
    return (f'El jugador pregunta: "{mensaje}"\nUsa la búsqueda web si hace falta y contesta en máximo 2 frases con el dato actual, '
            "sin enlaces ni lista de fuentes y sin emojis. Si no encuentras el dato, dilo; no inventes.")


_EMOJIS = re.compile("[" + chr(0x1F000) + "-" + chr(0x1FAFF) + chr(0x2600) + "-" + chr(0x27BF) + chr(0xFE0F) + chr(0x200D) + "]")


def limpiar_para_chat(texto, maximo=240):
    """Deja una respuesta lista para el chat de Minecraft: sin lista de fuentes ni enlaces, sin markdown ni emojis, en una línea y con un máximo de"""
    if not texto:
        return ""
    t = re.split(r"\n\s*\**\s*(?:sources?|fuentes?)\s*\**\s*:", str(texto), maxsplit=1, flags=re.IGNORECASE)[0]
    t = re.sub(r"\[([^\]]+)\]\(https?://[^)]*\)", r"\1", t)  # [texto](url) -> texto
    t = re.sub(r"https?://\S+", "", t)
    t = t.replace("**", "").replace("__", "").replace("`", "")
    t = _EMOJIS.sub("", t)
    t = re.sub(r"^\s*[-*]\s+", "", t, flags=re.MULTILINE)  # viñetas
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) > maximo:
        corte = t.rfind(". ", 60, maximo)
        t = t[:corte + 1] if corte != -1 else t[:maximo].rsplit(" ", 1)[0].rstrip(",;:") + "..."
    return t


def prompt_internet_fragmentos(mensaje, fragmentos):
    return (f'Eres Cobalt, un asistente experto. El jugador preguntó: "{mensaje}"\nDatos de internet (pueden estar desactualizados o ser '
            f'incoherentes entre sí): "{fragmentos}"\nREGLAS: responde breve (1-2 oraciones) usando SOLO estos datos. Si los datos se contradicen, '
            "no parecen fiables o no contienen la respuesta, di que no pudiste comprobarlo. No inventes.")


MENSAJE_NO_VERIFICADO = "Ahora mismo no puedo comprobar ese dato con seguridad. Pregúntame en un momento."

_ORDEN_FISICA = re.compile(r"^\s*(ven|ve|sigue|sigueme|mina|minar|construye|edifica|ataca|defiende|guarda|recoge|vuela|camina|corre|huye|equipa|"
                           r"planta|cosecha|pesca|pon|cambia|quita|abre|cierra|detente|deten|para|dame)\b", re.IGNORECASE)
_PIDE_INFORMACION = re.compile(r"^\s*dame\s+(el|la|los|las)?\s*(precio|cotizacion|clima|informacion|noticias|version|resultado)", re.IGNORECASE)
_NECESITA_INTERNET = re.compile("|".join([
    r"\b(precio|precios|cuesta|cuestan|cotizacion|dolar|dolares|euro|euros|bitcoin|tipo de cambio|peso mexicano)\b",
    r"\b(clima|llover|llueve|lluvia|temperatura|pronostico)\b",
    r"\b(noticia|noticias|novedades)\b",
    r"\b(ultima|ultimo|reciente|nueva|nuevo|proxima|proximo|siguiente)\b[^.?!]{0,30}\b(version|actualizacion|update|snapshot|parche|drop)\b",
    r"\b(version|actualizacion|update|snapshot|parche|drop)\b[^.?!]{0,30}\b(ultima|ultimo|reciente|nueva|nuevo|proxima|proximo|siguiente)\b",
    r"\bque (paso|ha pasado|esta pasando|hay de nuevo)\b",
    r"\bquien (gano|va ganando|es el campeon)\b|\bresultado de(l)? (partido|juego)\b",
    r"\b(tutorial|guia)\b",
    r"\b(busca|buscame|investiga|averigua)\b[^.?!]{0,40}\b(como|tutorial|guia|informacion|internet|red|google|wiki)\b",
    r"\ben (internet|la red|google|youtube)\b|\bwiki\b",
    r"\bcuando (sale|salio|sera|llega)\b|\bfecha de (lanzamiento|salida)\b",
]), re.IGNORECASE)


def _sin_tildes(texto):
    import unicodedata
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii").lower()


def necesita_internet(mensaje):
    """True si la frase pide claramente algo que solo internet sabe (precio, clima, noticias, última versión, tutoriales...)."""
    if not isinstance(mensaje, str) or not 4 <= len(mensaje.strip()) <= 240:
        return False
    t = _sin_tildes(mensaje)
    if _ORDEN_FISICA.match(t) and not _PIDE_INFORMACION.match(t):
        return False
    return bool(_NECESITA_INTERNET.search(t))
_VERBOS_ORDEN = re.compile(r"^\s*(ven|ve|sigue|sigueme|sígueme|mina|minar|construye|edifica|ataca|defiende|guarda|para|deten|detente|recoge|"
                           r"tr[aá]eme|dame|abre|cierra|vuela|camina|corre|huye|cura|equipa|planta|cosecha|pesca|diseña|planifica|estudia|aprende|investiga)\b",
                           re.IGNORECASE)
_INTERROGATIVO = re.compile(r"\b(cu[aá]nt[oa]s?|qu[eé]|c[oó]mo|d[oó]nde|cu[aá]l(es)?|para qu[eé]|por qu[eé]|de qu[eé])\b", re.IGNORECASE)
_TEMA_MINECRAFT = re.compile(
    r"\b(receta|craftea|crafteo|fabrica|fabricar|vida|da[nñ]o|durabilidad|nivel|bioma|mob|bloque|encantamiento|poci[oó]n|jefe|wither|drag[oó]n|"
    r"ender|g[oó]lem|aldeano|nether|netherita|diamante|hierro|redstone|piglin|warden|creeper|esqueleto|zombi|villager|colmena|abeja|"
    r"experiencia|xp|portal|baliza|elitro|[eé]litro|yunque|pico|espada|armadura|comida|hambre|spawn|genera)\b", re.IGNORECASE)


def es_pregunta_de_datos(mensaje):
    """¿El jugador pregunta un DATO de Minecraft (cifra, receta, dónde/cómo se consigue) y no da una orden ni charla? Conservador: ante la duda, no."""
    if not isinstance(mensaje, str):
        return False
    m = mensaje.strip()
    if not 8 <= len(m) <= 220 or _VERBOS_ORDEN.match(m):
        return False
    return bool(_INTERROGATIVO.search(m) and _TEMA_MINECRAFT.search(m))
