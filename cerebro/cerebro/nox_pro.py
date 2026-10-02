"""nox_pro.py: reflejos y decisiones "pro-player" de Cobalt."""
import math
import re
import threading
import time
import unicodedata

BOT_ID = "Cobalt_1"


def orden(accion, chat=None, modo="walk", **campos):
    """Una orden lista para command.json."""
    urgente = campos.pop("urgente", False)
    o = {"action": accion, "target": "SISTEMA", "amount": 1, "material": "cualquiera", "movement_mode": modo}
    o.update(campos)
    if chat:
        o["chat_message"] = chat
    if urgente:
        o["_urgente"] = True
    return o


def _numero(valor):
    return isinstance(valor, (int, float)) and not isinstance(valor, bool) and math.isfinite(valor)


def posicion(d):
    """(x, y, z) de un dict con esas claves, o None."""
    if isinstance(d, dict) and all(_numero(d.get(k)) for k in ("x", "y", "z")):
        return (float(d["x"]), float(d["y"]), float(d["z"]))
    return None


def distancia(a, b):
    return math.dist(a, b)


def distancia_xz(a, b):
    return math.hypot(a[0] - b[0], a[2] - b[2])


def entidades_de(datos):
    """Lista de entidades de entities.json (vacía si no hay o el formato es raro)."""
    lista = datos.get("entities") if isinstance(datos, dict) else None
    return [e for e in lista if isinstance(e, dict)] if isinstance(lista, list) else []


def hostiles(datos):
    return [e for e in entidades_de(datos) if e.get("kind") == "hostile"]


def dueno(datos):
    """El jugador dueño de Cobalt según entities.json (o None)."""
    for e in entidades_de(datos):
        if e.get("kind") == "player" and e.get("owner"):
            return e
    return None


_PALABRAS_OMEGA = {"halt_all", "halt all", "haltall", "omega", "protocolo omega", "congelate", "congélate", "congela todo", "detente todo", "alto total"}
_PALABRAS_REANUDAR = {"resume", "reanuda", "reanudar", "reanudar todo", "protocolo omega off", "omega off"}


def _normalizar_frase(texto):
    t = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode("ascii").lower()
    t = re.sub(r"[^a-z0-9_ ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def interpretar_omega(mensaje):
    """'halt_all' / 'resume' / None."""
    frase = _normalizar_frase(mensaje)
    if not frase:
        return None
    if frase in {_normalizar_frase(p) for p in _PALABRAS_REANUDAR}:
        return "resume"
    if frase in {_normalizar_frase(p) for p in _PALABRAS_OMEGA} or frase.startswith("halt_all"):
        return "halt_all"
    return None


class Supervisor:
    """Vigila hilos con nombre y los reinicia si mueren (p."""

    def __init__(self, max_reinicios=5, ventana_s=60.0, avisar=print):
        self.max_reinicios = max_reinicios
        self.ventana_s = ventana_s
        self.avisar = avisar
        self.hilos = {}

    def registrar(self, nombre, fabrica):
        self.hilos[nombre] = {"fabrica": fabrica, "hilo": None, "reinicios": [], "rendido": False}

    def iniciar(self, nombre):
        info = self.hilos[nombre]
        hilo = info["fabrica"]()
        hilo.daemon = True
        hilo.start()
        info["hilo"] = hilo
        return hilo

    def revisar(self, ahora=None):
        ahora = time.time() if ahora is None else ahora
        reiniciados = []
        for nombre, info in self.hilos.items():
            hilo = info["hilo"]
            if hilo is None or hilo.is_alive() or info["rendido"]:
                continue
            info["reinicios"] = [t for t in info["reinicios"] if ahora - t < self.ventana_s]
            if len(info["reinicios"]) >= self.max_reinicios:
                info["rendido"] = True
                self.avisar(f"[Watchdog] El hilo '{nombre}' murió {self.max_reinicios} veces en {self.ventana_s:g} s: no se reinicia más.")
                continue
            info["reinicios"].append(ahora)
            self.avisar(f"[Watchdog] El hilo '{nombre}' había muerto: se reinicia.")
            self.iniciar(nombre)
            reiniciados.append(nombre)
        return reiniciados


class RecuperacionMuerte:
    """Al morir guarda dónde; al reaparecer, su prioridad es volver a ese punto (y avisa)."""

    RADIO_LLEGADA = 4.0
    REEMISION_S = 8.0
    MAX_S = 300.0

    def __init__(self):
        self.ultima = None       # (x, y, z, dimension) mientras vive
        self.pos_muerte = None
        self.estaba_muerto = False
        self.fase = "idle"       # idle | esperando | en_camino
        self.t_inicio = 0.0
        self.t_ultimo = 0.0

    def _ir(self, chat=None):
        x, y, z, _ = self.pos_muerte
        return orden("go_to", chat, modo="fly", x=int(x), y=int(y), z=int(z))

    def actualizar(self, estado, gps, ahora):
        muerto = bool(estado.get("is_dead"))
        desplegado = bool(estado.get("is_deployed"))
        p = posicion(gps)
        dimension = gps.get("dimension") if isinstance(gps, dict) else None
        if desplegado and not muerto and p:
            self.ultima = (p[0], p[1], p[2], dimension)
        if muerto and not self.estaba_muerto:
            self.pos_muerte = self.ultima
            self.fase = "esperando" if self.pos_muerte else "idle"
        self.estaba_muerto = muerto

        salida = []
        if self.fase == "esperando" and desplegado and not muerto:
            mx, my, mz, mdim = self.pos_muerte
            if mdim and dimension and mdim != dimension:
                salida.append(orden("ninguna", f"Morí en {mdim.split(':')[-1]} ({int(mx)}, {int(my)}, {int(mz)}); no puedo ir hasta allí desde aquí."))
                self.fase = "idle"
            else:
                self.fase = "en_camino"
                self.t_inicio = self.t_ultimo = ahora
                salida.append(self._ir(f"Voy a recuperar mis cosas donde caí ({int(mx)}, {int(my)}, {int(mz)})."))
        elif self.fase == "en_camino":
            mx, my, mz, _ = self.pos_muerte
            if p and distancia(p, (mx, my, mz)) <= self.RADIO_LLEGADA:
                self.fase = "idle"
                salida.append(orden("ninguna", "Llegué al lugar donde caí."))
                salida.append(orden("pickup", radius=16))  # recoge sus cosas del suelo
            elif ahora - self.t_inicio > self.MAX_S:
                self.fase = "idle"
                salida.append(orden("ninguna", "No logré llegar al lugar donde caí; lo dejo aquí."))
            elif ahora - self.t_ultimo >= self.REEMISION_S:
                self.t_ultimo = ahora
                salida.append(self._ir())
        return salida


class RegistroCombates:
    """Convierte la telemetría continua en UN registro por combate (duración, daño recibido, rivales, EMP, resultado)."""

    MIN_DURACION_S = 2.0   # menos que esto es parpadeo del radar, no un combate

    def __init__(self, escribir, silencio_s=6.0):
        self.escribir = escribir
        self.silencio_s = silencio_s
        self.actual = None

    def _nuevo(self, estado, ahora):
        hp = estado.get("hp") if _numero(estado.get("hp")) else 0.0
        return {"inicio": ahora, "ultimo": ahora, "hp_inicio": hp, "hp_prev": hp, "hp_min": hp, "danio": 0.0, "rivales": {},
                "jefe": False, "boss_name": None, "emp_usos": 0, "emp_prev": estado.get("emp_ready", True),
                "dimension": estado.get("dimension")}

    def _cerrar(self, estado, ahora, resultado):
        c, self.actual = self.actual, None
        duracion = round(c["ultimo"] - c["inicio"], 1)
        if duracion < self.MIN_DURACION_S and resultado != "muerte":
            return None
        rivales = sorted(c["rivales"].items(), key=lambda kv: -kv[1])
        registro = {
            "ts": int(ahora), "duracion_s": duracion, "hp_inicio": c["hp_inicio"], "hp_fin": c["hp_prev"], "hp_min": c["hp_min"],
            "danio": round(c["danio"], 1), "rival": rivales[0][0] if rivales else None, "rivales": [n for n, _ in rivales[:5]],
            "jefe": c["jefe"], "boss_name": c["boss_name"], "emp_usos": c["emp_usos"], "resultado": resultado, "dimension": c["dimension"],
        }
        self.escribir(registro)
        return registro

    def actualizar(self, estado, entidades, ahora):
        if estado.get("is_dead") and self.actual:
            return self._cerrar(estado, ahora, "muerte")
        if estado.get("in_combat"):
            if self.actual is None:
                self.actual = self._nuevo(estado, ahora)
            c = self.actual
            c["ultimo"] = ahora
            hp = estado.get("hp")
            if _numero(hp):
                if hp < c["hp_prev"]:
                    c["danio"] += c["hp_prev"] - hp
                c["hp_prev"] = hp
                c["hp_min"] = min(c["hp_min"], hp)
            if estado.get("target"):
                c["rivales"][estado["target"]] = c["rivales"].get(estado["target"], 0) + 1
            for e in hostiles(entidades):
                if _numero(e.get("dist")) and e["dist"] <= 24:
                    c["rivales"][e.get("name", "?")] = c["rivales"].get(e.get("name", "?"), 0) + 1
            if estado.get("boss_mode"):
                c["jefe"] = True
                c["boss_name"] = estado.get("boss_name") or c["boss_name"]
            emp = estado.get("emp_ready", True)
            if c["emp_prev"] and not emp:
                c["emp_usos"] += 1
            c["emp_prev"] = emp
        elif self.actual and ahora - self.actual["ultimo"] >= self.silencio_s:
            return self._cerrar(estado, ahora, "victoria" if estado.get("hp", 1) > 0 else "muerte")
        return None


def estadisticas_combate(registros, rival=None):
    """Resumen por rival: combates, victorias, muertes, daño medio y duración media."""
    grupos = {}
    for r in registros:
        if not isinstance(r, dict) or not r.get("rival"):
            continue
        if rival and str(r["rival"]).lower() != str(rival).lower():
            continue
        g = grupos.setdefault(r["rival"], {"combates": 0, "victorias": 0, "muertes": 0, "danio": 0.0, "duracion": 0.0})
        g["combates"] += 1
        g["victorias"] += 1 if r.get("resultado") == "victoria" else 0
        g["muertes"] += 1 if r.get("resultado") == "muerte" else 0
        g["danio"] += float(r.get("danio") or 0)
        g["duracion"] += float(r.get("duracion_s") or 0)
    return {n: {"combates": g["combates"], "victorias": g["victorias"], "muertes": g["muertes"],
                "danio_medio": round(g["danio"] / g["combates"], 1), "duracion_media_s": round(g["duracion"] / g["combates"], 1)}
            for n, g in grupos.items()}


def resumen_para_prompt(registros, rival):
    """Frase con la experiencia previa contra 'rival' para el RAG táctico ('' si no hay historial)."""
    est = estadisticas_combate(registros, rival)
    if not est:
        return ""
    nombre, s = next(iter(est.items()))
    return (f"Historial contra {nombre}: {s['combates']} combate(s), {s['victorias']} victoria(s), {s['muertes']} muerte(s); "
            f"daño medio recibido {s['danio_medio']}, duración media {s['duracion_media_s']} s.")


class VigilanteTareas:
    """Vigila la cola de Java: si se acumula, la vacía (FLUSH); si una tarea lleva demasiado sin acabar, se detiene y avisa con las"""

    def __init__(self, limite_s=15 * 60.0, cola_max=8, cola_s=20.0):
        self.limite_s = limite_s
        self.cola_max = cola_max
        self.cola_s = cola_s
        self.clave = None
        self.t_tarea = 0.0
        self.t_cola = None

    @staticmethod
    def _clave(tarea):
        return str(tarea).split(" ", 1)[0] if tarea else None

    def actualizar(self, estado, gps, ahora):
        salida = []
        clave = self._clave(estado.get("task"))
        if clave != self.clave:
            self.clave, self.t_tarea = clave, ahora
        elif clave and ahora - self.t_tarea > self.limite_s:
            p = posicion(gps)
            donde = f" en ({int(p[0])}, {int(p[1])}, {int(p[2])})" if p else ""
            salida.append(orden("flush"))
            salida.append(orden("stop", f"Llevo más de {int(self.limite_s // 60)} minutos con '{clave}' sin terminar. Me detengo{donde}; ven a por mí si me perdí."))
            self.clave, self.t_tarea = None, ahora

        cola = estado.get("queue", 0)
        if _numero(cola) and cola >= self.cola_max:
            if self.t_cola is None:
                self.t_cola = ahora
            elif ahora - self.t_cola >= self.cola_s:
                salida.append(orden("flush", f"Tenía {int(cola)} tareas acumuladas: vacío la cola."))
                self.t_cola = None
        else:
            self.t_cola = None
        return salida


def debe_sigilo(entidades, sneaking_actual, radio=30.0):
    """True/False si hay que cambiar el sigilo; None si ya está bien."""
    hay_warden = any("warden" in str(e.get("type", "")) and _numero(e.get("dist")) and e["dist"] <= radio for e in entidades_de(entidades))
    trampas = entidades.get("hazards") if isinstance(entidades, dict) else None
    hay_shrieker = any(t.get("type") == "sculk_shrieker" and _numero(t.get("dist")) and t["dist"] <= 8.0
                       for t in (trampas or []) if isinstance(t, dict))
    quiere = hay_warden or hay_shrieker
    if quiere and not sneaking_actual:
        return True
    if not quiere and sneaking_actual:
        return False
    return None
