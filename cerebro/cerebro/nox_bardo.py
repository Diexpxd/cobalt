"""BLOQUE O: escribe una crónica en un libro firmado con lo que Cobalt ya tiene registrado."""
import datetime
import re

from nox_pro import _normalizar_frase, _numero

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
MAX_CHARS_PAGINA = 240   # Java corta a 250
MAX_PAGINAS = 40


def fecha_larga(dt):
    return f"{dt.day} de {MESES[dt.month - 1]} de {dt.year}"


def _fecha_ts(ts):
    try:
        return fecha_larga(datetime.datetime.fromtimestamp(float(ts)))
    except (ValueError, OSError, OverflowError, TypeError):
        return "fecha desconocida"


def paginar(lineas, maximo=MAX_CHARS_PAGINA):
    """Reparte líneas en páginas de <= 'maximo' caracteres SIN partir una línea (salvo que sola pase del máximo: entonces se corta por palabras)."""
    trozos = []
    for linea in lineas:
        texto = str(linea)
        while len(texto) > maximo:
            corte = texto.rfind(" ", 0, maximo)
            corte = corte if corte > 0 else maximo
            trozos.append(texto[:corte].rstrip())
            texto = texto[corte:].lstrip()
        trozos.append(texto)
    paginas, actual = [], ""
    for t in trozos:
        candidata = t if not actual else actual + "\n" + t
        if len(candidata) <= maximo:
            actual = candidata
        else:
            if actual.strip():
                paginas.append(actual)
            actual = t
    if actual.strip():
        paginas.append(actual)
    return [p.strip("\n") for p in paginas if p.strip()][:MAX_PAGINAS]


def _resumen_combates(registros):
    registros = [r for r in registros if isinstance(r, dict)]
    if not registros:
        return ["Aún no he librado ningún combate registrado."]
    victorias = sum(1 for r in registros if r.get("resultado") == "victoria")
    muertes = sum(1 for r in registros if r.get("resultado") == "muerte")
    danio = sum(float(r["danio"]) for r in registros if _numero(r.get("danio")))
    lineas = [f"Combates: {len(registros)} ({victorias} victorias, {muertes} caídas)."]
    lineas.append(f"Daño recibido en total: {round(danio)}.")
    rivales = {}
    for r in registros:
        if r.get("rival"):
            rivales[r["rival"]] = rivales.get(r["rival"], 0) + 1
    if rivales:
        nombre, n = max(sorted(rivales.items()), key=lambda kv: kv[1])
        lineas.append(f"Mi rival más común: {nombre} ({n} veces).")
    jefes = sorted({r.get("boss_name") or r.get("rival") for r in registros if r.get("jefe") and r.get("resultado") == "victoria" and (r.get("boss_name") or r.get("rival"))})
    if jefes:
        lineas.append("Jefes vencidos: " + ", ".join(jefes[:6]) + ".")
    largos = [r for r in registros if _numero(r.get("duracion_s"))]
    if largos:
        mas = max(largos, key=lambda r: r["duracion_s"])
        lineas.append(f"Mi combate más largo duró {round(mas['duracion_s'])} s contra {mas.get('rival') or 'algo desconocido'}.")
    dims = sorted({str(r["dimension"]).split(":")[-1] for r in registros if r.get("dimension")})
    if len(dims) > 1:
        lineas.append("He peleado en: " + ", ".join(dims) + ".")
    return lineas


def _resumen_obras(obras):
    if not isinstance(obras, dict) or not obras:
        return ["Todavía no he levantado ninguna obra."]
    def reciente(kv):
        t = kv[1].get("t") if isinstance(kv[1], dict) else None
        return -(t if _numero(t) else 0)

    ordenadas = sorted(obras.items(), key=reciente)
    lineas = [f"Obras construidas: {len(obras)}."]
    for nombre, d in ordenadas[:6]:
        if isinstance(d, dict):
            lineas.append(f"- {nombre}, en X={d.get('x')} Z={d.get('z')} ({_fecha_ts(d.get('t'))}).")
    return lineas


def _muertes(waypoints):
    fechas = []
    for clave in (waypoints or {}):
        m = re.fullmatch(r"muerte_nox_(\d{10,})", str(clave))
        if m:
            fechas.append(int(m.group(1)) / 1000.0)
    return sorted(fechas)


def crear_cronica(registros, obras, waypoints, ahora):
    """(titulo, paginas). 'ahora' es un datetime."""
    lineas_portada = ["Crónica de Cobalt", "", f"Escrita el {fecha_larga(ahora)}.", "", "Lo que sigue son hechos anotados en mi registro, no leyendas."]
    secciones = [lineas_portada, [""] + _resumen_combates(registros)]
    muertes = _muertes(waypoints)
    if muertes:
        ultima = _fecha_ts(muertes[-1])
        secciones.append(["", f"He caído {len(muertes)} vez/veces según mis marcas de muerte; la última, el {ultima}."])
    secciones.append([""] + _resumen_obras(obras))
    lugares = sorted(k for k, v in (waypoints or {}).items() if isinstance(v, dict) and not str(k).startswith(("muerte_nox_", "inventario_nox_")))
    if lugares:
        secciones.append(["", f"Lugares que recuerdo ({len(lugares)}): " + ", ".join(lugares[:12]) + ("…" if len(lugares) > 12 else ".")])
    secciones.append(["", "Firmado: Cobalt."])
    lineas = [l for s in secciones for l in s]
    return "Crónica de Cobalt", paginar(lineas)


_RE_CRONICA = re.compile(r"^(?:cobalt\s+)?(?:por favor\s+)?(?:escribe|escribeme|redacta|anota|registra|haz|hazme)\s+(?:un\s+|una\s+|el\s+|la\s+|tu\s+)?(?:libro|cronica|diario|bitacora|historia|memorias)\b"
                         r"|^(?:cobalt\s+)?cronica$")


def interpretar_bardo(mensaje):
    """'cronica' o None."""
    f = _normalizar_frase(mensaje)
    return "cronica" if f and _RE_CRONICA.search(f) else None
