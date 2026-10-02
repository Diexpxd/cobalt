"""Bloque F (Python): OMEGA, watchdog de hilos, recuperación de muerte, registro de combates, vigilante de tareas y sigilo."""
import os
import sys
import threading
import time

from _cargar import RAIZ, Resultados

sys.path.insert(0, os.path.join(RAIZ, "cerebro"))
import nox_pro as np  # noqa: E402

r = Resultados()

r.check("omega: 'HALT_ALL', 'halt all', 'Protocolo Omega!' y 'congélate' -> halt_all",
        all(np.interpretar_omega(m) == "halt_all" for m in ("HALT_ALL", "halt all", "Protocolo Omega!", "congélate", "  OMEGA ", "halt_all ya")))
r.check("omega: 'resume' y 'reanudar' -> resume", np.interpretar_omega("resume") == "resume" and np.interpretar_omega("Reanudar!") == "resume")
r.check("omega: frases normales NO congelan (el omega 3, halt sin all, mensaje vacío)",
        all(np.interpretar_omega(m) is None for m in ("el omega 3 es bueno", "cobalt sígueme", "halt", "", None, "para", "stop")))

class HiloFalso:
    def __init__(self, vivo=True):
        self.vivo, self.daemon, self.iniciado = vivo, False, False

    def start(self):
        self.iniciado = True

    def is_alive(self):
        return self.vivo


creados = []
avisos = []


def fabrica():
    h = HiloFalso()
    creados.append(h)
    return h


sup = np.Supervisor(max_reinicios=3, ventana_s=60, avisar=avisos.append)
sup.registrar("radar", fabrica)
sup.iniciar("radar")
r.check("watchdog: el hilo se inicia como daemon", len(creados) == 1 and creados[0].iniciado and creados[0].daemon)
r.check("watchdog: un hilo vivo no se toca", sup.revisar(100.0) == [] and len(creados) == 1)
creados[-1].vivo = False
r.check("watchdog: un hilo muerto se reinicia con uno NUEVO", sup.revisar(101.0) == ["radar"] and len(creados) == 2 and creados[1].iniciado)
creados[-1].vivo = False
sup.revisar(102.0)
creados[-1].vivo = False
sup.revisar(103.0)
creados[-1].vivo = False
r.check("watchdog: tras 3 reinicios en la ventana se RINDE (no hay bucle infinito) y avisa una sola vez",
        sup.revisar(104.0) == [] and len(creados) == 4 and sum("no se reinicia más" in a for a in avisos) == 1 and sup.revisar(105.0) == [])
sup2 = np.Supervisor(max_reinicios=1, ventana_s=10, avisar=lambda m: None)
c2 = []
sup2.registrar("x", lambda: c2.append(HiloFalso()) or c2[-1])
sup2.iniciar("x")
c2[-1].vivo = False
sup2.revisar(0.0)
c2[-1].vivo = False
r.check("watchdog: los reinicios viejos (fuera de la ventana) no cuentan", sup2.revisar(50.0) == ["x"])
hilo_real = threading.Thread(target=lambda: None)
sup3 = np.Supervisor(avisar=lambda m: None)
sup3.registrar("real", lambda: threading.Thread(target=lambda: None))
sup3.iniciar("real")
time.sleep(0.2)
r.check("watchdog: con hilos de verdad (terminan solos) los reinicia", sup3.revisar(time.time()) == ["real"])

rec = np.RecuperacionMuerte()
vivo = {"is_deployed": True, "is_dead": False}
muerto = {"is_deployed": False, "is_dead": True}
gps1 = {"x": 100.2, "y": 64, "z": -50.7, "dimension": "minecraft:overworld"}
r.check("muerte: vivo, sin nada que hacer", rec.actualizar(vivo, gps1, 0.0) == [])
r.check("muerte: al morir guarda la última posición y no ordena nada", rec.actualizar(muerto, {}, 1.0) == [] and rec.fase == "esperando" and rec.pos_muerte[:3] == (100.2, 64.0, -50.7))
gps_resp = {"x": 0, "y": 70, "z": 0, "dimension": "minecraft:overworld"}
o = rec.actualizar(vivo, gps_resp, 2.0)
r.check("muerte: al reaparecer va (fly) a donde cayó, con sus coordenadas enteras y un aviso",
        len(o) == 1 and o[0]["action"] == "go_to" and (o[0]["x"], o[0]["y"], o[0]["z"]) == (100, 64, -50) and o[0]["movement_mode"] == "fly" and "recuperar" in o[0]["chat_message"])
r.check("muerte: no repite la orden antes de 8 s", rec.actualizar(vivo, gps_resp, 5.0) == [])
r.check("muerte: pasados 8 s la repite (sin chat, para no spamear)", (lambda x: len(x) == 1 and x[0]["action"] == "go_to" and "chat_message" not in x[0])(rec.actualizar(vivo, gps_resp, 11.0)))
o = rec.actualizar(vivo, {"x": 101, "y": 64, "z": -50, "dimension": "minecraft:overworld"}, 12.0)
r.check("muerte: al llegar (<= 4 bloques) termina, avisa y recoge lo del suelo", len(o) == 2 and "Llegué" in o[0]["chat_message"] and o[1]["action"] == "pickup" and rec.fase == "idle")
rec2 = np.RecuperacionMuerte()
rec2.actualizar(vivo, gps1, 0.0)
rec2.actualizar(muerto, {}, 1.0)
o = rec2.actualizar(vivo, {"x": 0, "y": 70, "z": 0, "dimension": "minecraft:the_nether"}, 2.0)
r.check("muerte: si murió en OTRA dimensión no intenta ir; avisa", len(o) == 1 and o[0]["action"] == "ninguna" and "Morí en" in o[0]["chat_message"] and rec2.fase == "idle")
rec3 = np.RecuperacionMuerte()
rec3.actualizar(vivo, gps1, 0.0)
rec3.actualizar(muerto, {}, 1.0)
rec3.actualizar(vivo, gps_resp, 2.0)
o = rec3.actualizar(vivo, gps_resp, 400.0)
r.check("muerte: si no llega en 5 minutos se rinde y lo dice", len(o) == 1 and "No logré llegar" in o[0]["chat_message"] and rec3.fase == "idle")
rec4 = np.RecuperacionMuerte()
r.check("muerte: muerte sin posición previa (nunca vivo) -> no hace nada", rec4.actualizar(muerto, {}, 0.0) == [] and rec4.actualizar(vivo, gps_resp, 1.0) == [])

escritos = []
reg = np.RegistroCombates(escritos.append, silencio_s=6.0)
ent = {"entities": [{"kind": "hostile", "name": "Zombie", "dist": 5.0}, {"kind": "hostile", "name": "Zombie", "dist": 30.0}]}
base = {"in_combat": True, "hp": 20.0, "emp_ready": True, "target": "Zombie", "dimension": "minecraft:overworld"}
t = 100.0
reg.actualizar(base, ent, t)
reg.actualizar(dict(base, hp=16.0), ent, t + 1)
reg.actualizar(dict(base, hp=16.0, emp_ready=False), ent, t + 2)
reg.actualizar(dict(base, hp=18.0, emp_ready=False, boss_mode=True, boss_name="Wither"), ent, t + 3)
r.check("combate: mientras dura no escribe nada", escritos == [])
reg.actualizar({"in_combat": False, "hp": 18.0}, ent, t + 5)
r.check("combate: con menos de 6 s de silencio sigue abierto", escritos == [])
cerrado = reg.actualizar({"in_combat": False, "hp": 18.0}, ent, t + 10)
r.check("combate: tras 6 s de silencio escribe UN registro", len(escritos) == 1 and cerrado is escritos[0])
c = escritos[0]
r.check("combate: duración 3 s, daño recibido 4 (20->16; la curación no resta), 1 uso de EMP, resultado victoria",
        c["duracion_s"] == 3.0 and c["danio"] == 4.0 and c["emp_usos"] == 1 and c["resultado"] == "victoria" and c["hp_min"] == 16.0)
r.check("combate: rival principal, jefe y nombre del jefe; solo cuenta hostiles a <= 24 m",
        c["rival"] == "Zombie" and c["jefe"] is True and c["boss_name"] == "Wither" and c["rivales"] == ["Zombie"])
escritos.clear()
reg.actualizar(base, ent, 200.0)
reg.actualizar({"in_combat": False, "hp": 20.0}, ent, 200.5)
reg.actualizar({"in_combat": False, "hp": 20.0}, ent, 210.0)
r.check("combate: un parpadeo de 0.5 s del radar NO se registra", escritos == [])
reg.actualizar(base, ent, 300.0)
reg.actualizar(dict(base, hp=5.0), ent, 302.0)
res = reg.actualizar({"is_dead": True, "in_combat": True, "hp": 0}, ent, 303.0)
r.check("combate: si muere en combate se registra con resultado 'muerte'", res is not None and res["resultado"] == "muerte" and res["danio"] == 15.0)

historial = [
    {"rival": "Zombie", "resultado": "victoria", "danio": 2.0, "duracion_s": 10.0},
    {"rival": "zombie", "resultado": "victoria", "danio": 4.0, "duracion_s": 20.0},
    {"rival": "Wither", "resultado": "muerte", "danio": 100.0, "duracion_s": 60.0},
    {"rival": None}, "basura",
]
est = np.estadisticas_combate(historial)
r.check("estadísticas: agrupa por rival (sin mayúsculas... cada nombre tal como llegó), ignora basura",
        set(est) == {"Zombie", "zombie", "Wither"} and est["Wither"]["muertes"] == 1 and est["Wither"]["danio_medio"] == 100.0)
r.check("estadísticas: filtrando por rival sin distinguir mayúsculas suma ambos",
        np.estadisticas_combate(historial, "ZOMBIE") == {"Zombie": {"combates": 1, "victorias": 1, "muertes": 0, "danio_medio": 2.0, "duracion_media_s": 10.0},
                                                          "zombie": {"combates": 1, "victorias": 1, "muertes": 0, "danio_medio": 4.0, "duracion_media_s": 20.0}})
txt = np.resumen_para_prompt(historial, "Wither")
r.check("resumen RAG: frase con el historial; vacío si no hay", "Wither" in txt and "1 muerte" in txt and np.resumen_para_prompt(historial, "Ghast") == "")

vt = np.VigilanteTareas(limite_s=900, cola_max=8, cola_s=20)
gps_v = {"x": 10.4, "y": 30, "z": -5.9}
r.check("tareas: sin tarea no hace nada", vt.actualizar({"task": None, "queue": 0}, gps_v, 0.0) == [])
vt.actualizar({"task": "mine:iron_ore 0/8"}, gps_v, 10.0)
r.check("tareas: el progreso cambia pero la tarea es la misma (clave 'mine:iron_ore')", vt.actualizar({"task": "mine:iron_ore 3/8 (explorando y=-30)"}, gps_v, 500.0) == [])
o = vt.actualizar({"task": "mine:iron_ore 5/8 (volviendo)"}, gps_v, 10.0 + 901.0)
r.check("tareas: pasados 15 min con la misma tarea -> flush + stop con las coordenadas y aviso",
        [x["action"] for x in o] == ["flush", "stop"] and "(10, 30, -5)" in o[1]["chat_message"] and "mine:iron_ore" in o[1]["chat_message"])
r.check("tareas: tras avisar no repite de inmediato", vt.actualizar({"task": "mine:iron_ore 5/8"}, gps_v, 10.0 + 905.0) == [])
vt.actualizar({"task": "restock:cobblestone 0/32"}, gps_v, 2000.0)
r.check("tareas: cambiar de tarea reinicia el reloj", vt.actualizar({"task": "restock:cobblestone 8/32"}, gps_v, 2500.0) == [])
vc = np.VigilanteTareas(cola_max=8, cola_s=20)
r.check("cola: 7 tareas no es un problema", vc.actualizar({"queue": 7}, {}, 0.0) == [] and vc.actualizar({"queue": 7}, {}, 100.0) == [])
vc.actualizar({"queue": 9}, {}, 200.0)
r.check("cola: 9 tareas solo 10 s -> aún no", vc.actualizar({"queue": 9}, {}, 210.0) == [])
o = vc.actualizar({"queue": 9}, {}, 221.0)
r.check("cola: 9 tareas durante 20 s -> flush y aviso", len(o) == 1 and o[0]["action"] == "flush" and "9 tareas" in o[0]["chat_message"])
vc.actualizar({"queue": 9}, {}, 300.0)
vc.actualizar({"queue": 0}, {}, 310.0)
r.check("cola: si baja antes de tiempo se reinicia el contador", vc.actualizar({"queue": 9}, {}, 315.0) == [] and vc.actualizar({"queue": 9}, {}, 330.0) == [])

warden = {"entities": [{"type": "minecraft:warden", "dist": 20.0}], "hazards": []}
r.check("sigilo: Warden a 20 m y de pie -> agacharse", np.debe_sigilo(warden, False) is True)
r.check("sigilo: Warden a 20 m y ya agachado -> nada", np.debe_sigilo(warden, True) is None)
r.check("sigilo: sin Warden y agachado -> levantarse; de pie -> nada", np.debe_sigilo({"entities": [], "hazards": []}, True) is False and np.debe_sigilo({"entities": [], "hazards": []}, False) is None)
r.check("sigilo: Warden a 50 m no cuenta", np.debe_sigilo({"entities": [{"type": "minecraft:warden", "dist": 50.0}]}, False) is None)
r.check("sigilo: un sculk shrieker a 5 m cuenta", np.debe_sigilo({"entities": [], "hazards": [{"type": "sculk_shrieker", "dist": 5.0}]}, False) is True)
r.check("sigilo: datos raros no revientan", np.debe_sigilo({}, False) is None and np.debe_sigilo(None, False) is None)

r.check("orden(): campos por defecto y chat opcional", np.orden("flush") == {"action": "flush", "target": "SISTEMA", "amount": 1, "material": "cualquiera", "movement_mode": "walk"}
        and np.orden("x", "hola")["chat_message"] == "hola")
r.check("posicion(): acepta números, rechaza texto/bool/NaN", np.posicion({"x": 1, "y": 2.5, "z": -3}) == (1.0, 2.5, -3.0) and np.posicion({"x": "1", "y": 2, "z": 3}) is None
        and np.posicion({"x": True, "y": 2, "z": 3}) is None and np.posicion({"x": float("nan"), "y": 0, "z": 0}) is None and np.posicion(None) is None)

r.terminar()
