"""H6: diagnóstico."""
import json
import re
import threading
import time
import unicodedata
from collections import Counter, deque

MAX_LINEA = 300

_PATRONES = (
    (re.compile(r"AIza[0-9A-Za-z_\-]{20,}"), "«clave»"),
    (re.compile(r"\bsk-[A-Za-z0-9_\-]{16,}"), "«clave»"),
    (re.compile(r"(?i)\b(bearer)\s+[A-Za-z0-9._\-]{16,}"), r"\1 «oculto»"),
    (re.compile(r"(?i)([A-Za-z0-9_\-]*(?:api[_-]?key|key|token|secret|password|passwd|authorization))(\s*[=:]\s*[\"']?)[^\s,;&\"']{6,}"), r"\1\2«oculto»"),
    (re.compile(r"[\w.+\-]+@[\w\-]+\.[\w.\-]+"), "«correo»"),
    (re.compile(r"\b[A-Fa-f0-9]{40,}\b"), "«hash»"),
)


def redactar(texto, max_len=MAX_LINEA):
    """Quita claves, tokens y correos de un texto y lo acota. Nunca lanza; siempre devuelve str."""
    try:
        t = str(texto)
        for patron, sustituto in _PATRONES:
            t = patron.sub(sustituto, t)
        t = t.replace("\x00", "")
        return t if len(t) <= max_len else t[:max_len - 1] + "…"
    except Exception:  # noqa: BLE001
        return "«ilegible»"


class Anillo:
    """Las últimas N líneas (con su hora), seguro entre hilos y con redacción al entrar."""

    def __init__(self, capacidad=400, max_linea=MAX_LINEA, reloj=time.time):
        self._d = deque(maxlen=max(1, int(capacidad)))
        self._cerrojo = threading.Lock()
        self.max_linea, self.reloj = max_linea, reloj

    def anotar(self, texto):
        for linea in str(texto).splitlines():
            limpia = redactar(linea.strip(), self.max_linea)
            if limpia:
                with self._cerrojo:
                    self._d.append((self.reloj(), limpia))

    def ultimas(self, n=None):
        with self._cerrojo:
            lista = list(self._d)
        return lista if n is None else lista[-max(0, int(n)):] if n else []


class Tee:
    """Sustituye a sys.stdout: escribe donde escribía antes y además guarda las líneas completas en un Anillo."""

    MAX_PENDIENTE = 4000

    def __init__(self, destino, anillo):
        self._destino, self._anillo, self._pendiente = destino, anillo, ""

    def write(self, s):
        n = self._destino.write(s)
        try:
            self._pendiente += str(s)
            if "\n" in self._pendiente:
                *completas, self._pendiente = self._pendiente.split("\n")
                for linea in completas:
                    self._anillo.anotar(linea)
            if len(self._pendiente) > self.MAX_PENDIENTE:
                self._anillo.anotar(self._pendiente)
                self._pendiente = ""
        except Exception:  # noqa: BLE001
            self._pendiente = ""
        return n

    def flush(self):
        return self._destino.flush()

    def __getattr__(self, nombre):  # encoding, isatty, fileno... como el flujo original
        return getattr(self._destino, nombre)


def describir_orden(o):
    """Una línea corta de una orden enviada a Java (sin datos sensibles): acción, objetivo y el chat recortado."""
    if not isinstance(o, dict):
        return "orden no válida"
    partes = [f"action={str(o.get('action', '?'))[:24]}"]
    for k in ("material", "block", "target"):
        if o.get(k) not in (None, "", "cualquiera"):
            partes.append(f"{k}={str(o[k])[:30]}")
    if o.get("chat_message"):
        partes.append("chat=" + repr(str(o["chat_message"])[:60]))
    return redactar(" ".join(partes))


def edad_s(ahora, mtime):
    """Segundos desde que se modificó un archivo, o None si no existe / dato raro."""
    if isinstance(mtime, bool) or not isinstance(mtime, (int, float)):
        return None
    return max(0.0, ahora - mtime)


def texto_edad(seg):
    if seg is None:
        return "no existe"
    if seg < 90:
        return f"hace {int(seg)} s"
    if seg < 5400:
        return f"hace {int(seg // 60)} min"
    return f"hace {int(seg // 3600)} h"


def resumen_nube(lineas, max_lineas=500):
    """Líneas JSON del registro de la nube -> {(rol, proveedor): {'ok': n, 'fallo': n, 'errores': {tipo: n}, 'seg_medio': x}}. Ignora lo que no se entienda."""
    tabla = {}
    for linea in _lista(lineas)[-max_lineas:]:
        try:
            d = json.loads(linea)
        except (ValueError, TypeError):
            continue
        if not isinstance(d, dict):
            continue
        clave = (str(d.get("rol", "?"))[:20], str(d.get("proveedor", "?"))[:20])
        e = tabla.setdefault(clave, {"ok": 0, "fallo": 0, "errores": Counter(), "_seg": []})
        if d.get("ok") is True:
            e["ok"] += 1
        else:
            e["fallo"] += 1
            e["errores"][str(d.get("error") or "desconocido")[:30]] += 1
        if isinstance(d.get("seg"), (int, float)) and not isinstance(d.get("seg"), bool) and d["seg"] >= 0:
            e["_seg"].append(d["seg"])
    for e in tabla.values():
        s = e.pop("_seg")
        e["seg_medio"] = round(sum(s) / len(s), 1) if s else None
        e["errores"] = dict(e["errores"])
    return tabla


def _tiempo_valido(t):
    return isinstance(t, (int, float)) and not isinstance(t, bool) and t == t and 1e9 <= t <= 4.2e9


def _hora(t, formato="%H:%M:%S"):
    try:
        return time.strftime(formato, time.localtime(t)) if _tiempo_valido(t) else "??:??:??"
    except (ValueError, OverflowError, OSError, TypeError):
        return "??:??:??"


def _lista(x):
    return list(x) if isinstance(x, (list, tuple)) else []


def es_linea_de_error(linea):
    t = str(linea)
    if "[Reflejo" in t:
        return False
    return t.startswith("[-]") or "Traceback" in t or "Error" in t or "❌" in t or "🚨" in t


def resumen_mods(mods_json, max_ids=60):
    """mods.json (de Java) -> {'total': n, 'minecraft': str, 'ids': [...]}, o None si no hay datos válidos."""
    if not isinstance(mods_json, dict) or not isinstance(mods_json.get("mods"), list):
        return None
    ids = []
    for m in mods_json["mods"]:
        if isinstance(m, dict) and isinstance(m.get("id"), str) and re.fullmatch(r"[a-z0-9_\-.]{1,64}", m["id"]):
            ids.append(m["id"] + (("@" + m["version"][:20]) if isinstance(m.get("version"), str) and re.fullmatch(r"[\w.+\-]{1,20}", m["version"][:20]) else ""))
    mc = mods_json.get("minecraft")
    return {"total": len(mods_json["mods"]), "minecraft": redactar(mc, 20) if isinstance(mc, str) else "?", "ids": sorted(ids)[:max_ids]}


def generar_informe(d):
    """Markdown del diagnóstico a partir de un dict que arma el adaptador."""
    d = d if isinstance(d, dict) else {}
    ahora = d.get("ahora") if _tiempo_valido(d.get("ahora")) else time.time()
    L = []
    L.append("# Diagnóstico de Cobalt")
    L.append(f"_Generado: {_hora(ahora, '%Y-%m-%d %H:%M:%S')}. Las claves de API, tokens y correos se ocultan automáticamente._")
    L.append("")
    cfg = d.get("config") if isinstance(d.get("config"), dict) else {}
    booleanos = {k: v for k, v in cfg.items() if isinstance(v, bool) and not str(k).startswith("_")}
    apagados = sorted(k for k, v in booleanos.items() if not v)
    L.append("## Resumen")
    sens = d.get("sensores") if isinstance(d.get("sensores"), dict) else {}
    edades = {k: v for k, v in sens.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
    java_vivo = bool(edades) and min(edades.values()) < 30
    L.append(f"- Java (mod): {'ESCRIBIENDO sus sensores' if java_vivo else 'SIN ACTIVIDAD reciente (¿el juego está cerrado, Cobalt sin desplegar o el mod sin recompilar?)'}")
    consola = [x for x in _lista(d.get("consola")) if isinstance(x, (list, tuple)) and len(x) == 2]
    errores = [x for x in consola if es_linea_de_error(x[1])]
    L.append(f"- Errores/avisos en la consola reciente: {len(errores)} de {len(consola)} líneas")
    L.append(f"- Interruptores: {len(booleanos) - len(apagados)} encendidos, {len(apagados)} apagados")
    ollama = d.get("ollama") if isinstance(d.get("ollama"), dict) else {}
    if ollama:
        L.append(f"- Ollama: {'responde' if ollama.get('responde') else 'NO responde'}; modelo local: {redactar(ollama.get('modelo', '?'), 40)}"
                 + (" (modelo único)" if ollama.get("unico") else ""))
    L.append("")
    L.append("## Sensores (cuánto hace que Java los escribió)")
    if sens:
        for nombre in sorted(sens):
            L.append(f"- {redactar(nombre, 40)}: {texto_edad(sens[nombre] if isinstance(sens[nombre], (int, float)) and not isinstance(sens[nombre], bool) else None)}")
    else:
        L.append("- (sin datos)")
    hechos = [h for h in _lista(d.get("hechos")) if isinstance(h, str)]
    if hechos:
        L.append("")
        L.append("## Lo que ve Cobalt ahora")
        L += [f"- {redactar(h)}" for h in hechos[:8]]
    mods = resumen_mods(d.get("mods"))
    L.append("")
    L.append("## Mods (los exporta Java al cargar el mundo)")
    if mods:
        L.append(f"- Minecraft {mods['minecraft']}; {mods['total']} mods cargados. Primeros {len(mods['ids'])}: " + ", ".join(mods["ids"]))
    else:
        L.append("- Java no ha exportado `mods.json` (mod sin recompilar o mundo sin cargar).")
    L.append("")
    L.append("## Interruptores apagados")
    L.append("- " + (", ".join(redactar(a, 60) for a in apagados) if apagados else "(ninguno)"))
    ordenes = [x for x in _lista(d.get("ordenes")) if isinstance(x, (list, tuple)) and len(x) == 2]
    L.append("")
    L.append(f"## Últimas órdenes enviadas a Java ({len(ordenes)})")
    L += [f"- {_hora(t)} {redactar(x)}" for t, x in ordenes[-25:]] or ["- (ninguna desde que arrancó el cerebro)"]
    nube = d.get("nube") if isinstance(d.get("nube"), dict) else {}
    L.append("")
    L.append("## Nube (últimas llamadas del registro)")
    filas = sorted(((k, e) for k, e in nube.items() if isinstance(k, tuple) and len(k) == 2 and isinstance(e, dict)), key=lambda ke: (str(ke[0][0]), str(ke[0][1])))
    if filas:
        for (rol, prov), e in filas:
            L.append(f"- {redactar(rol, 30)} → {redactar(prov, 30)}: {redactar(e.get('ok', 0), 12)} ok, {redactar(e.get('fallo', 0), 12)} fallos"
                     + (f", {redactar(e['seg_medio'], 12)} s de media" if e.get("seg_medio") is not None else "")
                     + (f", errores: {redactar(e['errores'], 120)}" if e.get("errores") else ""))
    else:
        L.append("- (sin llamadas registradas)")
    L.append("")
    L.append("## Consola de Python (últimas líneas; primero los errores)")
    if errores:
        L.append("### Errores y avisos")
        L += [f"- {_hora(t)} {redactar(x)}" for t, x in errores[-15:]]
    L.append("### Cola completa")
    L += [f"    {_hora(t)} {redactar(x)}" for t, x in consola[-60:]] or ["    (vacía)"]
    meta = {"apagados": len(apagados), "java_vivo": java_vivo, "errores": len(errores), "mods": mods["total"] if mods else None}
    return "\n".join(L) + "\n", meta


def resumen_chat(meta, nombre_archivo):
    """Una frase para el chat. Solo se afirma lo que el informe midió."""
    m = meta if isinstance(meta, dict) else {}
    java = "Java responde" if m.get("java_vivo") else "Java sin actividad reciente"
    errores = m.get("errores", 0)
    return (f"Diagnóstico guardado en {nombre_archivo}: {java}, "
            + (f"{errores} error(es) recientes en la consola" if errores else "sin errores recientes en la consola")
            + f", {m.get('apagados', 0)} interruptores apagados.")


def _normalizar(t):
    t = unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode("ascii").lower()
    t = re.sub(r"\b(?:cobalt|nox)\b", " ", t)
    t = re.sub(r"[¿?¡!.,;:]+", " ", t)
    t = re.sub(r"\b(?:por favor|porfa|please|ahora)\b", " ", t)
    return re.sub(r"\s+", " ", t).strip()


_DIAGNOSTICO = re.compile(r"^(?:(?:haz|hazme|dame|pasame|genera|generame|quiero|necesito|corre|ejecuta|lanza)\s+)?(?:un\s+|el\s+)?(?:diagnostico|autodiagnostico)(?:\s+completo)?$")


def pide_diagnostico(mensaje):
    """Estricto: solo «diagnóstico» y sus formas cortas. «Diagnóstico de mi granja de Create» va al modelo."""
    if len(str(mensaje or "")) > 80:
        return False
    t = _normalizar(mensaje)
    return bool(t) and bool(_DIAGNOSTICO.match(t))
