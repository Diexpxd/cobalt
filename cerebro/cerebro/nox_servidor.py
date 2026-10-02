"""BLOQUE O (servidor y mantenimiento): decisiones PURAS (sin Minecraft, sin disco, sin red)."""
import datetime
import math
import re

from nox_pro import _normalizar_frase, _numero, orden

EDAD_OBJETO_VIEJO_TICKS = 2400   # 2 min y medio (los objetos desaparecen solos a los 5 min = 6000 ticks)
RADIO_LIMPIEZA = 16


def _entero_seguro(valor, defecto=0):
    return int(valor) if _numero(valor) else defecto


class MonitorServidor:
    """Estados 'ok' -> 'lag' -> 'critico' con histéresis: hay que estar mal (o bien) un rato SOSTENIDO para cambiar, así un tirón puntual no dispara nada."""

    def __init__(self, tps_lag=16.0, tps_critico=8.0, tps_ok=18.0, lag_s=10.0, critico_s=20.0, ok_s=20.0, limpieza_tras_s=60.0,
                 limpieza_cada_s=300.0, min_objetos_viejos=30):
        self.tps_lag, self.tps_critico, self.tps_ok = tps_lag, tps_critico, tps_ok
        self.lag_s, self.critico_s, self.ok_s = lag_s, critico_s, ok_s
        self.limpieza_tras_s, self.limpieza_cada_s, self.min_objetos_viejos = limpieza_tras_s, limpieza_cada_s, min_objetos_viejos
        self.estado = "ok"
        self._bajo_desde = None
        self._critico_desde = None
        self._bueno_desde = None
        self._lag_desde = None
        self._t_limpieza = -1e9

    @property
    def en_lag(self):
        return self.estado != "ok"

    def actualizar(self, estado_java, ahora, limpieza=True):
        tps = estado_java.get("server_tps")
        if not _numero(tps):
            return []  # sin datos (monitor apagado en Java o Java antiguo): ni alarmas ni cambios
        ordenes = []
        self._bajo_desde = (self._bajo_desde if self._bajo_desde is not None else ahora) if tps < self.tps_lag else None
        self._critico_desde = (self._critico_desde if self._critico_desde is not None else ahora) if tps < self.tps_critico else None
        self._bueno_desde = (self._bueno_desde if self._bueno_desde is not None else ahora) if tps >= self.tps_ok else None
        desplegado = bool(estado_java.get("is_deployed"))

        if self.estado == "ok":
            if self._bajo_desde is not None and ahora - self._bajo_desde >= self.lag_s:
                self.estado = "lag"
                self._lag_desde = ahora
                ordenes += self._retirar_drones(estado_java, f"El servidor va a {tps:.1f} TPS: retiro los drones y no los despliego hasta que se recupere.", desplegado)
        elif self.estado == "lag":
            if self._critico_desde is not None and ahora - self._critico_desde >= self.critico_s:
                self.estado = "critico"
                ordenes.append(orden("flush", chat=f"El servidor va MUY lento ({tps:.1f} TPS): vacío mi cola de tareas para no empeorarlo.", urgente=True))
            elif self._bueno_desde is not None and ahora - self._bueno_desde >= self.ok_s:
                ordenes += self._recuperado(tps)
        else:  # crítico
            if self._bueno_desde is not None and ahora - self._bueno_desde >= self.ok_s:
                ordenes += self._recuperado(tps)
            elif self._critico_desde is None:
                self.estado = "lag"  # ya no es tan grave, pero sigue el lag

        if limpieza and self.estado != "ok" and desplegado:
            ordenes += self._limpiar_objetos(estado_java, ahora)
        return ordenes

    def _retirar_drones(self, estado_java, texto, desplegado):
        if desplegado and estado_java.get("drones_active"):
            return [orden("recall_drones", chat=texto, urgente=True)]
        return [orden("ninguna", chat=texto)]

    def _recuperado(self, tps):
        self.estado = "ok"
        self._lag_desde = None
        self._bajo_desde = self._critico_desde = None
        return [orden("ninguna", chat=f"El servidor se ha recuperado ({tps:.1f} TPS): vuelvo a la normalidad.")]

    def _limpiar_objetos(self, estado_java, ahora):
        if self._lag_desde is None or ahora - self._lag_desde < self.limpieza_tras_s or ahora - self._t_limpieza < self.limpieza_cada_s:
            return []
        viejos = _entero_seguro(estado_java.get("items_old_near"))
        if viejos < self.min_objetos_viejos:
            return []
        if estado_java.get("in_combat") or estado_java.get("frozen") or estado_java.get("critical_hp") or _entero_seguro(estado_java.get("queue")) > 0:
            return []  # jamás en mitad de un combate ni pisando otra tarea
        self._t_limpieza = ahora
        return [orden("pickup", chat=f"Con el lag, recojo los {viejos} objetos viejos del suelo (llevan más de 2 min y medio) para aligerar el servidor.",
                      radius=RADIO_LIMPIEZA, min_age_ticks=EDAD_OBJETO_VIEJO_TICKS)]


def resumen_servidor(estado_java, monitor=None):
    """Frase con el estado del servidor para el chat."""
    tps = estado_java.get("server_tps")
    if not _numero(tps):
        return "No tengo datos del servidor (el monitor está apagado o Java no los envía)."
    modo = {"ok": "normal", "lag": "en lag", "critico": "en estado crítico"}.get(monitor.estado if monitor else "ok", "normal")
    partes = [f"El servidor va a {tps:.1f} TPS"]
    if _numero(estado_java.get("server_mspt")):
        partes[0] += f" ({estado_java['server_mspt']:.1f} ms por tick)"
    if _numero(estado_java.get("players_online")):
        partes.append(f"{int(estado_java['players_online'])} jugador(es) conectado(s)")
    if _numero(estado_java.get("items_near")):
        viejos = _entero_seguro(estado_java.get("items_old_near"))
        partes.append(f"{int(estado_java['items_near'])} objeto(s) sueltos cerca ({viejos} con más de 2 min y medio)")
    return ", ".join(partes) + f". Modo: {modo}."


def parsear_horas(valor):
    """['04:00', '16:30'] -> [(4, 0), (16, 30)]. Ignora lo que no sea 'H:MM'/'HH:MM' válido (nunca revienta con un config mal escrito)."""
    horas = []
    if not isinstance(valor, (list, tuple)):
        return horas
    for v in valor:
        m = re.fullmatch(r"\s*(\d{1,2}):(\d{2})\s*", v) if isinstance(v, str) else None
        if m and int(m.group(1)) < 24 and int(m.group(2)) < 60:
            horas.append((int(m.group(1)), int(m.group(2))))
    return sorted(set(horas))


def proximo_reinicio(ahora, horas):
    """El primer reinicio de la lista que ocurre DESPUÉS de 'ahora' (datetime), o None si la lista está vacía."""
    candidatos = []
    for h, mi in horas:
        t = ahora.replace(hour=h, minute=mi, second=0, microsecond=0)
        if t <= ahora:
            t += datetime.timedelta(days=1)
        candidatos.append(t)
    return min(candidatos) if candidatos else None


class ProteccionReinicio:
    """Antes de un reinicio programado (cobalt_config.json -> 'servidor_reinicios': ["04:00", "16:00"], hora del ordenador del servidor):"""

    def __init__(self):
        self._hechas = set()

    def actualizar(self, estado_java, ahora, horas_config, aviso_min=5.0):
        horas = parsear_horas(horas_config)
        objetivo = proximo_reinicio(ahora, horas)
        if objetivo is None or not estado_java.get("is_deployed"):
            return []
        restante = (objetivo - ahora).total_seconds()
        clave = objetivo.isoformat()
        self._hechas = {h for h in self._hechas if h[0] >= (ahora - datetime.timedelta(days=1)).isoformat()}  # no crece sin fin
        ordenes = []
        if restante <= 60.0:
            if (clave, "parada") not in self._hechas:
                self._hechas.add((clave, "parada"))
                self._hechas.add((clave, "aviso"))
                ordenes.append(orden("flush", chat="Reinicio del servidor en 1 minuto: vacío mi cola y me detengo.", urgente=True))
                ordenes.append(orden("stop", urgente=True))
        elif restante <= aviso_min * 60.0 and (clave, "aviso") not in self._hechas:
            self._hechas.add((clave, "aviso"))
            minutos = max(1, math.ceil(restante / 60.0))
            ordenes.append(orden("ninguna", chat=f"Reinicio del servidor en unos {minutos} minuto(s) ({objetivo:%H:%M}): retiro los drones y guardo mis cosas en los cofres."))
            if estado_java.get("drones_active"):
                ordenes.append(orden("recall_drones"))
            if not estado_java.get("in_combat"):
                ordenes.append(orden("store"))
        return ordenes


_RE_TPS = re.compile(r"\b(?:tps|lag|laggeo|rendimiento del servidor|como va el servidor|va lento el servidor|estado del servidor|servidor lento|ping del servidor)\b")
_RE_LIMPIAR = re.compile(r"^(?:cobalt\s+)?(?:por favor\s+)?(?:limpia|limpiar|recoge|recoger|aligera|aligerar)\s+(?:los\s+|el\s+)?(?:objetos?|items?|lag|suelo|basura|entidades)\b")
_RE_HORNOS = re.compile(r"\b(?:atiende|atender|revisa|revisar|carga|cargar|vacia|vaciar|alimenta|alimentar|recoge|recoger)\s+(?:de\s+)?(?:los\s+|el\s+|mis\s+|tus\s+)?hornos?\b"
                        r"|^(?:cobalt\s+)?(?:por favor\s+)?(?:funde|fundir|cocina|cocinar)\s+(?:los\s+|las\s+|el\s+|mis\s+|tus\s+)?(?:minerales|menas|lingotes|mena|hierro|oro|cobre|comida|carne|todo)\b")


def interpretar_servidor(mensaje):
    """{'tipo': 'tps'|'limpiar'|'hornos', ...} o None."""
    f = _normalizar_frase(mensaje)
    if not f:
        return None
    if _RE_LIMPIAR.search(f):
        return {"tipo": "limpiar"}
    if _RE_HORNOS.search(f):
        radio = re.search(r"\b(\d{1,2})\s*(?:bloques?|metros?)\b", f)
        return {"tipo": "hornos", "radio": max(3, min(16, int(radio.group(1)))) if radio else 10}
    if _RE_TPS.search(f) and re.search(r"\b(?:como|que|cuantos|cual|va|vas|hay|estado|tps|mira|dime|revisa)\b", f):
        return {"tipo": "tps"}
    return None
