"""Retomar la tarea anterior: «ven, atiende los hornos y continúa con tu antigua tarea»."""
import copy
import re
import unicodedata

# acción larga -> archivo de feedback donde Java deja cómo acabó
LARGAS = {
    "mine": "mine_feedback.json",
    "flatten_area": "terraform_feedback.json",
    "clear_area": "clear_feedback.json",
    "harvest": "harvest_feedback.json",
    "chop_wood": "chop_feedback.json",
    "fish": "fish_feedback.json",
}

_CONTADORES = {"mine": ("wanted", "mined"), "chop_wood": ("wanted", "chopped"), "fish": ("wanted", "caught")}

ESPERA_MIN_S = 2.0
CICLOS_LIBRE = 2
TIMEOUT_S = 900.0         # si no queda libre en 15 min, se olvida la petición

_PETICION = re.compile(
    r"(?:,\s*)?(?:\by\s+)?(?:\b(?:luego|despues|despues\s+de\s+eso|al\s+terminar|cuando\s+termines|y\s+luego)\s+)?"
    r"\b(?:continua|continues|continuar|sigue|siguele|seguir|retoma|retomar|reanuda|reanudar|vuelve\s+a|regresa\s+a|termina|terminar)\s+"
    r"(?:con\s+|a\s+)?(?:tu\s+|la\s+|esa\s+|esta\s+|lo\s+)?(?:antigua\s+|anterior\s+|ultima\s+|vieja\s+|de\s+antes\s+)?"
    r"(?:tarea|trabajo|mision|labor|lo\s+que\s+(?:hacias|estabas\s+haciendo|estabas|tenias)|lo\s+tuyo|lo\s+anterior|lo\s+de\s+antes)\b(?:\s+(?:de\s+antes|anterior|antigua|pasada|previa|ultima))?")


def _sin_acentos_con_indices(texto):
    salida, indices = [], []
    for i, c in enumerate(texto):
        for ch in unicodedata.normalize("NFKD", c.lower()):
            if not unicodedata.combining(ch):
                salida.append(ch)
                indices.append(i)
    return "".join(salida), indices


def separar_peticion(mensaje):
    """Quita del mensaje la petición de retomar. -> (mensaje limpio, True si la había)."""
    mensaje = str(mensaje or "")
    plano, indices = _sin_acentos_con_indices(mensaje)
    m = _PETICION.search(plano)
    if not m or not indices:
        return mensaje, False
    if re.search(r"(?:^|\s)no\s+(?:me\s+)?$", plano[:m.start()]):   # 'no continúes con tu tarea': lo contrario
        return mensaje, False
    ini = indices[m.start()]
    fin = indices[m.end() - 1] + 1
    limpio = (mensaje[:ini] + " " + mensaje[fin:]).strip()
    limpio = re.sub(r"\s+", " ", limpio)
    limpio = re.sub(r"(?:^|\s)(?:y|luego|despues|,)\s*$", "", limpio).strip(" ,.;")
    return limpio, True


_DESCRIPCIONES = {
    "mine": lambda o: "minar " + (str(o.get("material")) if o.get("material") not in (None, "", "cualquiera") else "lo que había"),
    "flatten_area": lambda o: "aplanar el terreno",
    "clear_area": lambda o: "despejar la zona",
    "harvest": lambda o: "cosechar",
    "chop_wood": lambda o: "talar árboles",
    "fish": lambda o: "pescar",
}


def describir(orden):
    f = _DESCRIPCIONES.get(orden.get("action"))
    return f(orden) if f else str(orden.get("action"))


class Reanudador:
    def __init__(self, leer_feedback=None):
        self.leer_feedback = leer_feedback or (lambda nombre: None)   # nombre de archivo -> dict (con '_mtime') o None
        self.anterior = None          # {"orden", "t", "archivo"}
        self.pendiente_desde = None
        self.libre = 0

    def registrar(self, orden, ahora):
        if not isinstance(orden, dict):
            return
        accion = orden.get("action")
        if accion in LARGAS:
            self.anterior = {"orden": copy.deepcopy(orden), "t": float(ahora), "archivo": LARGAS[accion]}

    def pedir(self, ahora):
        self.pendiente_desde = float(ahora)
        self.libre = 0

    def cancelar(self):
        self.pendiente_desde = None
        self.libre = 0

    def actualizar(self, estado, ahora):
        if self.pendiente_desde is None:
            return []
        if ahora - self.pendiente_desde > TIMEOUT_S:
            self.cancelar()
            return []
        if ahora - self.pendiente_desde < ESPERA_MIN_S:
            return []
        if not isinstance(estado, dict) or not estado.get("is_deployed", False):
            return []
        if estado.get("task") or int(estado.get("queue") or 0) > 0:
            self.libre = 0
            return []
        self.libre += 1
        if self.libre < CICLOS_LIBRE:
            return []
        self.cancelar()
        return self._retomar()

    def _mensaje(self, texto):
        return {"action": "ninguna", "target": "SISTEMA", "chat_message": texto, "amount": 1, "material": "cualquiera", "movement_mode": "walk"}

    def _retomar(self):
        if not self.anterior:
            return [self._mensaje("No tenía ninguna tarea anterior que retomar.")]
        ant = self.anterior
        orden = copy.deepcopy(ant["orden"])
        que = describir(orden)
        fb = self.leer_feedback(ant["archivo"])
        nuevo = isinstance(fb, dict) and float(fb.get("_mtime", 0.0)) >= ant["t"] - 1.0        # el feedback es de ESA tarea, no de una anterior
        if nuevo and fb.get("status") == "success":
            return [self._mensaje(f"Mi tarea anterior ({que}) ya la terminé.")]
        cuenta = _CONTADORES.get(orden.get("action"))
        if nuevo and cuenta:   # solo lo que falta (lo pedido menos lo ya hecho)
            try:
                falta = int(fb.get(cuenta[0], 0)) - int(fb.get(cuenta[1], 0))
                if falta > 0:
                    orden["amount"] = falta
            except (TypeError, ValueError):
                pass
        orden["chat_message"] = f"Retomo lo que estaba haciendo: {que}."
        orden["reanudada"] = True
        return [orden]
