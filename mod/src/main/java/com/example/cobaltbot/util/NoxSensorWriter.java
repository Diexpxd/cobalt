package com.example.cobaltbot.util;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.mojang.logging.LogUtils;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.monster.Enemy;
import net.minecraft.world.entity.monster.Monster;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.Container;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.item.BlockItem;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.phys.AABB;
import net.minecraftforge.common.Tags;
import org.slf4j.Logger;

import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** ÚNICO escritor de los sensores que lee cerebro.py (vision.json, terreno_sensor.json, nox_status.json). */
public class NoxSensorWriter {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final File DIR = com.example.cobaltbot.util.NoxRutas.dir();

    public static final double RADIO_RADAR = 32.0D;
    private static final int MAX_NOMBRES_RADAR = 8;
    private static final float VIDA_JEFE = 100.0F;

    static {
        if (!DIR.exists()) {
            DIR.mkdirs();
        }
    }

    public static void escribirAtomico(String nombreArchivo, String contenido) {
        File destino = new File(DIR, nombreArchivo);
        File tmp = new File(DIR, nombreArchivo + ".tmp");
        try {
            Files.writeString(tmp.toPath(), contenido, StandardCharsets.UTF_8);
            try {
                Files.move(tmp.toPath(), destino.toPath(),
                        StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
            } catch (IOException moveFail) {
                Files.writeString(destino.toPath(), contenido, StandardCharsets.UTF_8);
                Files.deleteIfExists(tmp.toPath());
            }
        } catch (Exception e) {
            LOGGER.warn("[NoxSensorWriter] No se pudo escribir {}: {}", nombreArchivo, e.toString());
        }
    }

    public static final int TERRENO_SEGURO = 0;
    public static final int TERRENO_AGUA = 1;
    public static final int TERRENO_PELIGRO = 2;

    public static int clasificarTerreno(BlockGetter level, BlockPos base) {
        int resultado = TERRENO_SEGURO;
        for (int dx = -1; dx <= 1; dx++) {
            for (int dz = -1; dz <= 1; dz++) {
                for (int dy = -2; dy <= 0; dy++) {
                    Block b = level.getBlockState(base.offset(dx, dy, dz)).getBlock();
                    if (b == Blocks.LAVA || b == Blocks.FIRE || b == Blocks.SOUL_FIRE) {
                        return TERRENO_PELIGRO;
                    }
                    if (b == Blocks.WATER) {
                        resultado = TERRENO_AGUA;
                    }
                }
            }
        }
        return resultado;
    }

    private static final int MAX_ESCANEO_CAIDA = 32;
    private static final int CAIDA_MINIMA_AVISO = 4;   // por debajo no es una caída relevante

    public static int distanciaAlSuelo(BlockGetter level, BlockPos desde, int max) {
        for (int i = 1; i <= max; i++) {
            BlockState estado = level.getBlockState(desde.below(i));
            if (estado.blocksMotion() || !estado.getFluidState().isEmpty()) {
                return i - 1;
            }
        }
        return -1;
    }

    public static void actualizarSensorTerreno(Level level, Entity bot, boolean volando) {
        try {
            List<String> avisos = new ArrayList<>();

            int terreno = clasificarTerreno(level, bot.blockPosition());
            boolean peligro = bot.isInLava() || bot.isOnFire() || terreno == TERRENO_PELIGRO;
            if (peligro) {
                avisos.add("PELIGRO: ¡Lava o fuego detectado bajo los pies o adyacente! Se requiere vuelo urgente (fly).");
            }

            if (bot.isInWall()) {
                avisos.add("ALERTA: sofocación (Cobalt está dentro de un bloque sólido).");
            }

            if (!volando && !bot.onGround() && !bot.isInWater() && !bot.isInLava() && bot.getDeltaMovement().y < -0.1D) {
                int suelo = distanciaAlSuelo(level, bot.blockPosition(), MAX_ESCANEO_CAIDA);
                if (suelo < 0) {
                    avisos.add("ALERTA: caída al vacío (sin suelo en " + MAX_ESCANEO_CAIDA + " bloques bajo Cobalt).");
                } else if (suelo >= CAIDA_MINIMA_AVISO) {
                    avisos.add("ALERTA: caída inminente, suelo a " + suelo + " bloques bajo Cobalt.");
                }
            }

            if (!peligro) {
                if (bot.isInWater()) {
                    avisos.add("ESTADO: Sumergido en agua. Se requiere movement_mode 'swim'.");
                } else if (terreno == TERRENO_AGUA) {
                    avisos.add("TERRENO: Agua detectada cerca. Usa movement_mode 'swim' para cruzar.");
                }
            }

            escribirAtomico("terreno_sensor.json", avisos.isEmpty() ? "Terreno seguro." : String.join(" | ", avisos));
        } catch (Exception e) {
            LOGGER.warn("[NoxSensorWriter] Fallo en sensor de terreno", e);
        }
    }

    public static final double VEL_CAIDA_LIBRE = -0.35D;

    public static boolean debeVolarPorCaida(double velocidadVertical, int caidaBloques, boolean sueloNoSeguro) {
        if (velocidadVertical > VEL_CAIDA_LIBRE) return false;
        return caidaBloques < 0 || caidaBloques >= CAIDA_MINIMA_AVISO || sueloNoSeguro;
    }

    public static void limpiarSensores() {
        escribirAtomico("terreno_sensor.json", "Sin datos: Cobalt no está desplegado.");
        escribirAtomico("vision.json", "Radar de Hostiles (" + (int) RADIO_RADAR + "m): Despejado (Cobalt no está desplegado).");
        escribirAtomico("entities.json", "{\"bot_id\":\"" + com.example.cobaltbot.util.NoxCuerpo.BOT_ID + "\",\"deployed\":false,\"entities\":[],\"hazards\":[],\"blacklist\":[]}");
    }

    public static final double RADIO_COMBATE = 24.0D;
    public static final double DIST_AMENAZA_CERCANA = 8.0D;

    public static List<LivingEntity> hostilesEnRadio(Level level, LivingEntity bot, double radio) {
        double radio2 = radio * radio;
        List<LivingEntity> lista = new ArrayList<>(level.getEntitiesOfClass(LivingEntity.class,
                bot.getBoundingBox().inflate(radio), e -> {
                    // Cero fuego amigo: nunca el propio bot ni ningún jugador
                    if (e == bot || e instanceof Player || !e.isAlive()) return false;
                    if (e.distanceToSqr(bot) > radio2) return false;
                    return e instanceof Enemy || e instanceof Monster || e.getType().is(Tags.EntityTypes.BOSSES);
                }));
        lista.sort(Comparator.comparingDouble(e -> e.distanceToSqr(bot)));
        return lista;
    }

    public static boolean esJefe(LivingEntity e) {
        return e.getType().is(Tags.EntityTypes.BOSSES) || e.getMaxHealth() >= VIDA_JEFE;
    }

    public static boolean esAmenaza(LivingEntity bot, LivingEntity hostil) {
        return bot.distanceToSqr(hostil) <= DIST_AMENAZA_CERCANA * DIST_AMENAZA_CERCANA || bot.hasLineOfSight(hostil);
    }

    public static void actualizarRadarHostiles(Level level, LivingEntity bot) {
        try {
            List<LivingEntity> hostiles = hostilesEnRadio(level, bot, RADIO_RADAR);

            String reporte;
            if (hostiles.isEmpty()) {
                reporte = "Radar de Hostiles (" + (int) RADIO_RADAR + "m): Despejado.";
            } else {
                StringBuilder sb = new StringBuilder("Radar de Hostiles (")
                        .append((int) RADIO_RADAR).append("m): ")
                        .append(hostiles.size()).append(" detectados - ");

                int mostrados = Math.min(hostiles.size(), MAX_NOMBRES_RADAR);
                for (int i = 0; i < mostrados; i++) {
                    LivingEntity e = hostiles.get(i);
                    boolean jefe = esJefe(e);
                    if (i > 0) sb.append(", ");
                    if (jefe) sb.append("[JEFE] ");
                    sb.append(e.getName().getString())
                            .append(" (").append(String.format(java.util.Locale.ROOT, "%.1f", e.distanceTo(bot)))
                            .append(esAmenaza(bot, e) ? "m)" : "m*)");
                }
                if (hostiles.size() > mostrados) {
                    sb.append(", +").append(hostiles.size() - mostrados).append(" más");
                }
                reporte = sb.toString();
            }

            escribirAtomico("vision.json", reporte);
        } catch (Exception e) {
            LOGGER.warn("[NoxSensorWriter] Fallo en radar de hostiles", e);
        }
    }

    public static final int MAX_ENTIDADES = 24;
    private static final int RADIO_TRAMPAS = 5;
    private static final int MAX_TRAMPAS = 16;
    private static final java.util.Set<String> LISTA_NEGRA = java.util.concurrent.ConcurrentHashMap.newKeySet();

    public static java.util.Set<String> listaNegra() {
        return java.util.Collections.unmodifiableSet(LISTA_NEGRA);
    }

    private static String idDe(ItemStack pila) {
        var clave = BuiltInRegistries.ITEM.getKey(pila.getItem());
        return clave == null ? "desconocido" : clave.toString();
    }

    private static String idDe(Entity e) {
        var clave = BuiltInRegistries.ENTITY_TYPE.getKey(e.getType());
        return clave == null ? "desconocido" : clave.toString();
    }

    private static double redondear(double v) {
        return Math.round(v * 10.0D) / 10.0D;
    }

    public static boolean esAliado(LivingEntity e) {
        if (e instanceof com.example.cobaltbot.entity.CobaltDroneEntity) return true; // los drones del enjambre nunca son objetivo
        if (e instanceof net.minecraft.world.entity.TamableAnimal t && t.isTame()) return true;
        if (e instanceof net.minecraft.world.entity.animal.horse.AbstractHorse h && h.isTamed()) return true;
        return e instanceof net.minecraft.world.entity.animal.IronGolem g && g.isPlayerCreated();
    }

    private static boolean ataCaDistancia(LivingEntity e) {
        return e instanceof net.minecraft.world.entity.monster.RangedAttackMob || e instanceof net.minecraft.world.entity.monster.CrossbowAttackMob
                || e instanceof net.minecraft.world.entity.monster.Ghast || e instanceof net.minecraft.world.entity.monster.Blaze
                || e instanceof net.minecraft.world.entity.monster.Shulker;
    }

    private static JsonObject describirEntidad(LivingEntity bot, LivingEntity e, Player owner) {
        if (e instanceof com.example.cobaltbot.entity.CobaltDroneEntity) return null; // su estado va en nox_status (drones_*)
        String tipo;
        boolean porComportamiento = false;
        net.minecraft.world.entity.LivingEntity objetivo = e instanceof net.minecraft.world.entity.Mob m ? m.getTarget() : null;
        if (e instanceof Player) {
            tipo = "player";
        } else if (esAliado(e)) {
            tipo = "ally";
        } else if (e instanceof Enemy || e instanceof Monster || e.getType().is(Tags.EntityTypes.BOSSES)) {
            tipo = "hostile";
        } else if (objetivo != null && (objetivo == bot || objetivo instanceof Player)) {
            tipo = "hostile";
            porComportamiento = true;
        } else {
            return null;
        }

        JsonObject o = new JsonObject();
        o.addProperty("id", e.getId());
        o.addProperty("type", idDe(e));
        o.addProperty("name", e.getName().getString());
        o.addProperty("kind", tipo);
        if (porComportamiento) o.addProperty("by_behavior", true);
        boolean jefe = !(e instanceof Player) && esJefe(e);
        o.addProperty("boss", jefe);
        o.addProperty("mega", jefe && com.example.cobaltbot.util.NoxCuerpo.esMegaJefe(e.getMaxHealth()));
        o.addProperty("dist", redondear(e.distanceTo(bot)));
        o.addProperty("x", redondear(e.getX()));
        o.addProperty("y", redondear(e.getY()));
        o.addProperty("z", redondear(e.getZ()));
        double vx = (e.getX() - e.xOld) * 20.0D; // bloques por segundo
        double vz = (e.getZ() - e.zOld) * 20.0D;
        o.addProperty("vx", redondear(vx));
        o.addProperty("vz", redondear(vz));
        double hx = bot.getX() - e.getX(), hz = bot.getZ() - e.getZ();
        double hl = Math.max(1.0E-3D, Math.sqrt(hx * hx + hz * hz));
        o.addProperty("approaching", (vx * hx + vz * hz) / hl > 0.3D);
        o.addProperty("hp", redondear(e.getHealth()));
        o.addProperty("max_hp", redondear(e.getMaxHealth()));
        o.addProperty("los", bot.hasLineOfSight(e));
        o.addProperty("ranged", ataCaDistancia(e));
        o.addProperty("blocking", e.isBlocking());
        o.addProperty("targets_bot", objetivo == bot);
        o.addProperty("targets_player", objetivo instanceof Player);
        if (e instanceof net.minecraft.world.entity.monster.Creeper c) {
            o.addProperty("swelling", c.getSwellDir() > 0 || c.isIgnited()); // "Creeper Hisses"
        }
        if (e instanceof Player p) {
            o.addProperty("owner", owner != null && p == owner);
            o.addProperty("sneaking", p.isShiftKeyDown());
            o.addProperty("yaw", redondear(p.getYRot())); // hacia dónde mira (para avisarle de lo que tiene a la espalda)
            ItemStack mano = p.getMainHandItem();
            if (!mano.isEmpty()) {
                o.addProperty("held", idDe(mano)); // y qué herramienta lleva ("tu pico está a punto de romperse")
                if (mano.isDamageableItem()) o.addProperty("held_dur_pct", redondear(NoxTools.durabilidadRestantePct(mano)));
            }
        }
        return o;
    }

    private static JsonArray escanearTrampas(Level level, LivingEntity bot) {
        JsonArray lista = new JsonArray();
        BlockPos centro = bot.blockPosition();
        for (int dx = -RADIO_TRAMPAS; dx <= RADIO_TRAMPAS && lista.size() < MAX_TRAMPAS; dx++) {
            for (int dy = -RADIO_TRAMPAS; dy <= RADIO_TRAMPAS && lista.size() < MAX_TRAMPAS; dy++) {
                for (int dz = -RADIO_TRAMPAS; dz <= RADIO_TRAMPAS && lista.size() < MAX_TRAMPAS; dz++) {
                    BlockPos pos = centro.offset(dx, dy, dz);
                    String tipo = com.example.cobaltbot.util.NoxCuerpo.tipoDeTrampa(level.getBlockState(pos));
                    if (tipo == null) continue;
                    JsonObject t = new JsonObject();
                    t.addProperty("type", tipo);
                    t.addProperty("x", pos.getX());
                    t.addProperty("y", pos.getY());
                    t.addProperty("z", pos.getZ());
                    t.addProperty("dist", redondear(Math.sqrt(pos.distSqr(centro))));
                    lista.add(t);
                }
            }
        }
        return lista;
    }

    private static final double RADIO_OBJETOS = 12.0D;
    private static final int MAX_OBJETOS = 16;

    private static JsonArray escanearObjetosSuelo(Level level, LivingEntity bot) {
        List<net.minecraft.world.entity.item.ItemEntity> cerca = new ArrayList<>(level.getEntitiesOfClass(net.minecraft.world.entity.item.ItemEntity.class,
                bot.getBoundingBox().inflate(RADIO_OBJETOS), e -> e.isAlive() && e.distanceToSqr(bot) <= RADIO_OBJETOS * RADIO_OBJETOS));
        cerca.sort(Comparator.comparingDouble(e -> e.distanceToSqr(bot)));
        JsonArray lista = new JsonArray();
        for (net.minecraft.world.entity.item.ItemEntity e : cerca) {
            if (lista.size() >= MAX_OBJETOS) break;
            ItemStack pila = e.getItem();
            if (pila.isEmpty()) continue;
            JsonObject o = new JsonObject();
            o.addProperty("id", e.getId());
            o.addProperty("item", BuiltInRegistries.ITEM.getKey(pila.getItem()).toString());
            o.addProperty("count", pila.getCount());
            o.addProperty("enchanted", pila.isEnchanted() || pila.getItem() instanceof net.minecraft.world.item.EnchantedBookItem);
            o.addProperty("x", redondear(e.getX()));
            o.addProperty("y", redondear(e.getY()));
            o.addProperty("z", redondear(e.getZ()));
            o.addProperty("dist", redondear(e.distanceTo(bot)));
            lista.add(o);
        }
        return lista;
    }

    public static JsonObject datosDeDanio(LivingEntity bot) {
        try {
            return datosDeDanioSeguro(bot);
        } catch (Exception e) {
            LOGGER.warn("[NoxSensorWriter] No se pudo describir el último daño: {}", e.toString());
            return null;
        }
    }

    private static JsonObject datosDeDanioSeguro(LivingEntity bot) {
        net.minecraft.world.damagesource.DamageSource fuente = bot.getLastDamageSource();
        if (fuente == null) return null;
        JsonObject d = new JsonObject();
        d.addProperty("type", fuente.type().msgId());
        d.addProperty("projectile", fuente.is(net.minecraft.tags.DamageTypeTags.IS_PROJECTILE));
        Entity causante = fuente.getEntity();
        Entity directo = fuente.getDirectEntity();
        if (causante != null) {
            d.addProperty("source", causante.getName().getString());
            d.addProperty("sx", redondear(causante.getX()));
            d.addProperty("sy", redondear(causante.getY()));
            d.addProperty("sz", redondear(causante.getZ()));
        }
        if (directo != null && directo != causante) {
            d.addProperty("direct", idDe(directo));
            d.addProperty("dx", redondear(directo.getX()));
            d.addProperty("dy", redondear(directo.getY()));
            d.addProperty("dz", redondear(directo.getZ()));
            net.minecraft.world.phys.Vec3 v = directo.getDeltaMovement();
            d.addProperty("dvx", redondear(v.x));
            d.addProperty("dvz", redondear(v.z));
        }
        return d;
    }

    public static void actualizarEntidades(Level level, LivingEntity bot, Player owner) {
        try {
            JsonObject raiz = new JsonObject();
            raiz.addProperty("bot_id", com.example.cobaltbot.util.NoxCuerpo.BOT_ID);
            raiz.addProperty("updated_ms", System.currentTimeMillis());
            raiz.addProperty("deployed", true);
            JsonObject yo = new JsonObject();
            yo.addProperty("x", redondear(bot.getX()));
            yo.addProperty("y", redondear(bot.getY()));
            yo.addProperty("z", redondear(bot.getZ()));
            yo.addProperty("yaw", redondear(bot.getYRot()));
            raiz.add("bot", yo);

            double radio2 = RADIO_RADAR * RADIO_RADAR;
            List<LivingEntity> cerca = new ArrayList<>(level.getEntitiesOfClass(LivingEntity.class, bot.getBoundingBox().inflate(RADIO_RADAR),
                    e -> e != bot && e.isAlive() && e.distanceToSqr(bot) <= radio2));
            cerca.sort(Comparator.comparingDouble(e -> e.distanceToSqr(bot)));

            JsonArray lista = new JsonArray();
            for (LivingEntity e : cerca) {
                if (lista.size() >= MAX_ENTIDADES) break;
                String id = idDe(e);
                if (LISTA_NEGRA.contains(id)) continue;
                try {
                    JsonObject o = describirEntidad(bot, e, owner);
                    if (o != null) lista.add(o);
                } catch (Exception ex) {
                    if (LISTA_NEGRA.add(id)) LOGGER.warn("[NoxSensorWriter] '{}' lanzó {} al describirla: a la lista negra.", id, ex.toString());
                }
            }
            raiz.add("entities", lista);
            raiz.add("hazards", escanearTrampas(level, bot));
            raiz.add("items", escanearObjetosSuelo(level, bot));
            JsonArray negra = new JsonArray();
            for (String id : LISTA_NEGRA) negra.add(id);
            raiz.add("blacklist", negra);
            escribirAtomico("entities.json", raiz.toString());
        } catch (Exception e) {
            LOGGER.warn("[NoxSensorWriter] Fallo escribiendo entities.json", e);
        }
    }

    public static void escribirEstado(boolean desplegado, boolean muerto, int minutosRegen,
                                      LivingEntity bot, String modoMovimiento) {
        escribirEstado(desplegado, muerto, minutosRegen, bot, modoMovimiento, null);
    }

    public static void escribirEstado(boolean desplegado, boolean muerto, int minutosRegen,
                                      LivingEntity bot, String modoMovimiento, JsonObject extras) {
        try {
            JsonObject json = new JsonObject();
            json.addProperty("bot_id", com.example.cobaltbot.util.NoxCuerpo.BOT_ID);
            json.addProperty("is_deployed", desplegado);
            json.addProperty("is_dead", muerto);
            json.addProperty("regen_minutes", minutosRegen);
            json.addProperty("updated_ms", System.currentTimeMillis());

            if (bot != null) {
                float vida = bot.getHealth();
                float vidaMax = bot.getMaxHealth();
                json.addProperty("hp", Math.round(vida * 10.0F) / 10.0F);
                json.addProperty("max_hp", vidaMax);
                json.addProperty("hp_pct", vidaMax > 0 ? Math.round(100.0F * vida / vidaMax) : 0);
                json.addProperty("armor", bot.getArmorValue());
                json.addProperty("movement_mode", modoMovimiento);
                json.addProperty("dimension", bot.level().dimension().location().toString());

                JsonArray efectos = new JsonArray();
                JsonArray efectosMalos = new JsonArray();
                for (MobEffectInstance efecto : bot.getActiveEffects()) {
                    var id = BuiltInRegistries.MOB_EFFECT.getKey(efecto.getEffect());
                    if (id != null) {
                        efectos.add(id.toString());
                        if (efecto.getEffect().getCategory() == net.minecraft.world.effect.MobEffectCategory.HARMFUL) efectosMalos.add(id.toString());
                    }
                }
                json.add("effects", efectos);
                json.add("effects_bad", efectosMalos);
            }

            if (extras != null) {
                for (Map.Entry<String, com.google.gson.JsonElement> campo : extras.entrySet()) {
                    json.add(campo.getKey(), campo.getValue());
                }
            }

            escribirAtomico("nox_status.json", json.toString());
        } catch (Exception e) {
            LOGGER.warn("[NoxSensorWriter] Fallo escribiendo nox_status.json", e);
        }
    }

    public static void escribirEstadoChip(boolean muerto, int minutosRegen) {
        escribirEstado(false, muerto, minutosRegen, null, "walk");
    }

    private static final int MAX_TIPOS_INVENTARIO = 30;

    public static JsonObject resumirInventario(Container inventario) {
        JsonObject resumen = new JsonObject();
        int total = inventario.getContainerSize();
        int usados = 0, curacion = 0, bloques = 0;
        boolean pico = false, hacha = false, espada = false, pala = false, azada = false;
        Map<String, Integer> cantidades = new LinkedHashMap<>();
        Map<String, Integer> pociones = new LinkedHashMap<>();
        Map<String, Integer> ripio = new LinkedHashMap<>();
        List<String> fragiles = new ArrayList<>();
        int leche = 0;

        for (int i = 0; i < total; i++) {
            ItemStack pila = inventario.getItem(i);
            if (pila.isEmpty()) continue;
            usados++;

            var clave = BuiltInRegistries.ITEM.getKey(pila.getItem());
            String id = clave.toString();
            cantidades.merge(id, pila.getCount(), Integer::sum);
            if (pila.getItem() instanceof net.minecraft.world.item.PotionItem && !(pila.getItem() instanceof net.minecraft.world.item.ThrowablePotionItem)) {
                for (MobEffectInstance efecto : net.minecraft.world.item.alchemy.PotionUtils.getMobEffects(pila)) {
                    var idEfecto = BuiltInRegistries.MOB_EFFECT.getKey(efecto.getEffect());
                    if (idEfecto != null) pociones.merge(idEfecto.getPath(), pila.getCount(), Integer::sum);
                }
            }
            if (pila.is(net.minecraft.world.item.Items.MILK_BUCKET)) leche += pila.getCount();
            if (NoxMinado.esBasura(pila)) ripio.merge(clave.getPath(), pila.getCount(), Integer::sum);
            if (NoxTools.esFragil(pila) && !fragiles.contains(clave.getPath())) fragiles.add(clave.getPath());

            if (pila.getItem().isEdible()) curacion += pila.getCount();
            if (pila.getItem() instanceof BlockItem) bloques += pila.getCount();
            String tipo = NoxTools.tipoDeHerramienta(pila); // clasificación única (ver NoxTools)
            if ("pickaxe".equals(tipo)) pico = true;
            else if ("axe".equals(tipo)) hacha = true;
            else if ("sword".equals(tipo)) espada = true;
            else if ("shovel".equals(tipo)) pala = true;
            else if ("hoe".equals(tipo)) azada = true;
        }

        resumen.addProperty("slots", total);
        resumen.addProperty("used", usados);
        resumen.addProperty("free", total - usados);
        resumen.addProperty("full", usados >= total);
        resumen.addProperty("empty", usados == 0);
        resumen.addProperty("healing", curacion);
        resumen.addProperty("blocks", bloques);

        JsonArray herramientas = new JsonArray();
        if (pico) herramientas.add("pickaxe");
        if (hacha) herramientas.add("axe");
        if (espada) herramientas.add("sword");
        if (pala) herramientas.add("shovel");
        if (azada) herramientas.add("hoe");
        resumen.add("tools", herramientas);

        JsonObject items = new JsonObject();
        cantidades.entrySet().stream()
                .sorted((a, b) -> Integer.compare(b.getValue(), a.getValue()))
                .limit(MAX_TIPOS_INVENTARIO)
                .forEach(e -> items.addProperty(e.getKey(), e.getValue()));
        resumen.add("items", items);
        resumen.addProperty("other_types", Math.max(0, cantidades.size() - MAX_TIPOS_INVENTARIO));
        JsonObject jsonPociones = new JsonObject();
        pociones.forEach(jsonPociones::addProperty);
        resumen.add("potions", jsonPociones);
        resumen.addProperty("milk", leche);
        JsonObject jsonRipio = new JsonObject();
        ripio.forEach(jsonRipio::addProperty);
        resumen.add("junk", jsonRipio);
        JsonArray jsonFragiles = new JsonArray();
        fragiles.forEach(jsonFragiles::add);
        resumen.add("fragile", jsonFragiles);
        return resumen;
    }
}
