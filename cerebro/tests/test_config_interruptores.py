"""Pruebas de los interruptores de seguridad (cobalt_config.json) del lado Python."""
import io
import json
import os
import tempfile
import time

from _cargar import Resultados, cargar_cerebro

ns = cargar_cerebro()
r = Resultados()
ruta = os.path.join(tempfile.mkdtemp(), "cobalt_config.json")
ns["CONFIG_FILE"] = ruta


def escribir(texto):
    io.open(ruta, "w", encoding="utf-8").write(texto)


def recargar():
    ns["_CONFIG_CACHE"]["t"] = 0.0  # fuerza la relectura sin esperar los 5 s


# archivo ausente -> todo encendido, umbrales por defecto
recargar()
r.check("sin archivo: la función está ENCENDIDA por defecto", ns["config_activa"]("autocuracion") is True)
r.check("sin archivo: umbral por defecto", ns["config_numero"]("vida_critica_pct", 30) == 30)

escribir(json.dumps({"autocuracion": False, "modo_jefe": True, "vida_critica_pct": 25, "mineria_real": "no", "raro": 3}))
recargar()
r.check("false apaga la función", ns["config_activa"]("autocuracion") is False)
r.check("true la mantiene", ns["config_activa"]("modo_jefe") is True)
r.check("clave ausente -> encendida", ns["config_activa"]("prediccion_disparo") is True)
r.check("valor no booleano ('no') se ignora -> encendida", ns["config_activa"]("mineria_real") is True)
r.check("umbral numérico leído", ns["config_numero"]("vida_critica_pct", 30) == 25)
r.check("un número no cuenta como booleano y un booleano no cuenta como número",
        ns["config_activa"]("raro") is True and ns["config_numero"]("autocuracion", 7) == 7)

escribir('{"autocuracion": fal')
recargar()
r.check("archivo roto: se conserva el último valor bueno (autocuracion sigue apagada)", ns["config_activa"]("autocuracion") is False)

# caché: dentro de los 5 s no relee
escribir(json.dumps({"autocuracion": True}))
r.check("dentro de la ventana de 5 s NO relee el archivo (caché)", ns["config_activa"]("autocuracion") is False)
recargar()
r.check("pasada la ventana relee y aplica el cambio", ns["config_activa"]("autocuracion") is True)

# borrar el archivo vuelve a los valores por defecto
os.remove(ruta)
recargar()
r.check("archivo borrado -> vuelve a todo encendido", ns["config_activa"]("modo_jefe") is True and ns["config_numero"]("vida_critica_pct", 30) == 30)

real = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cobalt_config.json")
datos = json.load(io.open(real, encoding="utf-8"))
r.check("cobalt_config.json entregado: JSON válido", isinstance(datos, dict))
bools = [k for k, v in datos.items() if isinstance(v, bool)]
OPT_IN = {"nube_router", "modelo_local_unico", "biblioteca_planos", "nube_gemini_de_pago", "schematics_import", "schematics_estados", "construccion_por_lotes", "vision_continua"}
r.check("cobalt_config.json entregado: todos los interruptores vienen ENCENDIDOS salvo los opt-in documentados",
        bools and all(datos[k] for k in bools if k not in OPT_IN))
r.check("el TP cuántico tarda 120 s en volver a estar disponible (lo pidió el usuario: 60 s se le hacía rápido)", datos.get("tp_cuantico_enfriamiento_s") == 120)
ELEGIDOS_POR_EL_USUARIO = OPT_IN - {"nube_gemini_de_pago"}
r.check("cobalt_config.json entregado: nube_gemini_de_pago sigue APAGADO (cuesta dinero) y los demás opt-in existen como booleanos (el usuario los encendió)",
        datos.get("nube_gemini_de_pago") is False and all(isinstance(datos.get(k), bool) for k in ELEGIDOS_POR_EL_USUARIO))
r.check("cobalt_config.json entregado: define los umbrales de vida", 0 < datos["vida_critica_pct"] < datos["vida_recuperada_pct"] <= 100)

r.terminar()
