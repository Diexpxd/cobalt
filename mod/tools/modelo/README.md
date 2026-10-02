# Modelos 3D de Cobalt (guardián arcano y efectos de habilidades)

Todo se genera con código, para poder corregir proporciones, colores y animaciones sin abrir un editor.

```
python generar.py --instalar     # genera en salida/ y copia al mod (assets/cobaltbot/...); guarda el modelo anterior en original/ (una vez)
python publicar.py               # salida/visor_guardian.html: visor 3D con todo incrustado (para publicarlo)
python vistas.py <png>           # hoja de 4 vistas del guardián (Edge sin ventana)
python poses.py <png> anim=walk cam=lado tiempos=0,0.25,0.5,0.75
python capturar.py <png> modelo=plasma cam=tres_cuartos anim=spin t=0.3 dist=1.5 y=0.25
```

| Archivo | Qué hace |
|---|---|
| `geo.py` | Núcleo: cubos, huesos, atlas de textura (UV por cara), exportación a geo 1.12.0 y a animation.json |
| `guardian.py` | Diseño del guardián (huesos y cubos) |
| `animaciones.py` | idle, walk, fly, fly_move, fly_start, fly_end, swim, attack, cast_spell, emp, death + la capa `runico` |
| `pintura.py` | Pintor de la textura y de la capa de brillo (`*_glowmask.png`), runas con alfabeto propio |
| `efectos.py` | Orbe de plasma, onda de runas del pulso EMP y dron |
| `visor.html`, `capturar.py` | Visor three.js de trabajo y capturas con Edge sin ventana |
| `visor_publicar.tpl.html`, `publicar.py` | Visor publicable (varios modelos, ficha, cámaras) |

## Reglas que salen del código de GeckoLib 4.4.9 (comprobadas leyendo sus fuentes)
- Frente del modelo = -z; +x es el lado **izquierdo** del personaje (GeckoLib espeja x al cargar).
- Rotaciones de cubo, de hueso y de animación: X e Y se **niegan** al cargar, Z no. Orden de aplicación: Z, luego Y, luego X. Por eso un cubo largo que debe seguir un ángulo A en el plano xy lleva `rot z = -A`.
- En animaciones: rotación X positiva lleva hacia **atrás** lo que cuelga (piernas, brazos, capa) y hacia **adelante** lo que está de pie (torso, cabeza). `animaciones.py` lo encapsula en `colgante(a)` y `erguido(a)` (a > 0 = adelante).
- UV por cara: si una cara no se lista, no se dibuja. Las caras de arriba/abajo salen giradas 180° respecto a un dibujo "de frente".
- Dos controladores: `controller` (estado) y `runico` (halo y flotar de las placas). El estado mueve `runa_X` y `runico` mueve `runa_X_f` (hijo): así no se pisan.
- Brillo: `AutoGlowingGeoLayer` dibuja `<textura>_glowmask.png` (mismo tamaño que la base).

## Comprobaciones
- `CobaltModeloTests` (GameTests): carga cada modelo con el cargador de GeckoLib y comprueba huesos, cubos, UV dentro de la textura, animaciones que el código pide, huesos que las animaciones mueven y tamaño de las texturas.

## Lo que NO se puede comprobar sin abrir Minecraft
Cómo se ve con la luz del juego, el brillo real, el tamaño respecto al mundo y el rendimiento. El visor replica la geometría y el giro de las piezas, no la iluminación de Minecraft.
