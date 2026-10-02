# Cobalt

Compañero autónomo para Minecraft Java 1.20.1 (Forge). Cobalt es una entidad que sigue al jugador, mina, tala, pesca, craftea, construye a partir de planos, combate y avisa de peligros. El proyecto tiene dos partes que se comunican por archivos JSON:

- **`mod/`**: el mod de Forge, en Java. Controla el cuerpo de Cobalt dentro del juego, ejecuta las órdenes y escribe los sensores (posición, entidades cercanas, inventario, terreno).
- **`cerebro/`**: el cerebro, en Python. Lee los sensores, decide y escribe las órdenes. Combina reglas deterministas para los reflejos (huir de la lava, curarse, esquivar creepers) con un modelo de lenguaje para entender el chat y planificar tareas largas.

```
Minecraft (mod Java) --gps.json, entities.json, nox_status.json...--> cerebro (Python)
Minecraft (mod Java) <-----------------command.json------------------ cerebro (Python)
```

El mod solo obedece las órdenes dirigidas a su propio cuerpo, y cada función se puede apagar en caliente con un interruptor en `cerebro/cobalt_config.json`, que ambos lados releen cada pocos segundos.

## Qué hace el cerebro

- **Reflejos y supervivencia**: huida con poca vida, curación, evitar lava, aterrizaje seguro, anti-atasco, recuperación tras morir.
- **Combate**: priorización de objetivos, disparo con predicción, pulso EMP, enjambre de drones, protocolo de jefes con memoria de derrotas.
- **Oficios**: minería (incluida de túnel y profunda), tala, pesca, crafteo con la mesa virtual de su inventario, cosecha y logística de cofres.
- **Obra**: construcción por planos y por lotes de hasta 64 bloques por orden, aplanado de terreno, caminos y puentes, réplica y reparación de estructuras.
- **Chat**: órdenes cortas en español e inglés ("quédate", "recoge hierro", "continúa con lo que hacías"), informe de situación, memoria de lo estudiado y preferencias del jugador.
- **Enrutador de modelos**: cada tarea tiene su cadena de proveedores (Gemini, API de Claude o un modelo local con Ollama), con plazos, cortacircuitos tras fallos y tope de gasto diario.
- **Servidor**: vigila el TPS, limpia entidades cuando hay lag y protege las tareas ante reinicios programados.

## Instalación

Requisitos: JDK 17, Python 3.12 (con el que se probó), Forge 1.20.1 y [Ollama](https://ollama.com) (opcional, para el modelo local).

```
cd mod
gradlew build                       # el jar queda en mod/build/libs; copiarlo a la carpeta mods junto con GeckoLib 4.4.9

cd ../cerebro
pip install -r requirements.txt
```

Variables de entorno:

| Variable | Para qué |
|---|---|
| `COBALT_DIR` | Carpeta de intercambio entre el mod y el cerebro. Tiene que ser la misma para los dos; lo más simple es apuntarla a `cerebro/` |
| `GEMINI_API_KEY_1`, `_2`... | Claves de Gemini (opcional; se rotan una a una) |
| `COBALT_CLAUDE_KEY` | Clave de la API de Claude (opcional) |

Sin claves, el cerebro usa solo el modelo local de Ollama (`qwen3.5:9b` por defecto, configurable en `cobalt_config.json`).

```
python cerebro/cerebro.py
```

## Pruebas

```
python cerebro/tests/run_all.py              # 2054 comprobaciones de Python
mod/tools/pruebas/ejecutar.ps1               # 514 comprobaciones de lógica en Java, con bloques e ítems reales
cd mod && gradlew runGameTestServer          # 89 GameTests en un servidor real de Minecraft sin ventana
```

`cerebro/validar_todo.ps1` ejecuta las tres. Las pruebas de la nube usan proveedores y relojes simulados, así que no gastan cuota de ninguna API.

## Modelos 3D

El guardián, la esfera de plasma, el pulso EMP y el dron se generan con código para poder ajustar proporciones, colores y animaciones sin un editor. Está en `mod/tools/modelo/` y su README explica las reglas de GeckoLib que se comprobaron.

## Estado

Proyecto personal en desarrollo. Limitaciones conocidas:

- Pensado para Windows y para un solo jugador como dueño de Cobalt.
- Las rutas de los proveedores en la nube se probaron con clientes simulados, no con una sesión larga de uso real.
- Hay funciones marcadas como experimentales y apagadas por defecto, como la importación de schematics.
- Sin licencia de uso: todos los derechos reservados. El código se publica para consulta.
