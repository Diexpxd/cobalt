package com.example.cobaltbot.entity;

import com.example.cobaltbot.util.NoxAgro;
import com.example.cobaltbot.util.NoxArboles;
import com.example.cobaltbot.util.NoxCrafteo;
import com.example.cobaltbot.util.NoxMinado;
import com.example.cobaltbot.util.NoxPesca;
import com.example.cobaltbot.util.NoxServidor;
import com.example.cobaltbot.util.NoxTerreno;
import com.example.cobaltbot.util.NoxSensorWriter;
import com.example.cobaltbot.util.NoxTools;
import com.google.gson.JsonObject;
import com.mojang.logging.LogUtils;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.Container;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.SimpleContainer;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.BlockItem;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.items.ItemHandlerHelper;
import org.slf4j.Logger;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/** Cola de tareas LARGAS y SECUENCIALES de Cobalt (minar, entregar, guardar, reabastecer, despejar). */
public final class CobaltTareas {

    private static final Logger LOGGER = LogUtils.getLogger();

    public interface Tarea {
        boolean tick(CobaltEntity mob);

        default void cancelar(CobaltEntity mob) {}

        String nombre();
    }

    private final Deque<Tarea> cola = new ArrayDeque<>();
    private Tarea actual = null;

    public void encolar(Tarea tarea) {
        if (cola.size() < 16) cola.add(tarea); // tope: un LLM desbocado no llena la memoria
    }

    public boolean ocupado() {
        return actual != null || !cola.isEmpty();
    }

    public int pendientes() {
        return cola.size() + (actual != null ? 1 : 0);
    }

    public String descripcion() {
        return actual == null ? null : actual.nombre();
    }

    public void limpiar(CobaltEntity mob) {
        if (actual != null) actual.cancelar(mob);
        actual = null;
        cola.clear();
    }

    public void tick(CobaltEntity mob) {
        if (actual == null) {
            actual = cola.poll();
            if (actual == null) return;
        }
        if (mob.tareasPausadas()) return;
        boolean terminada;
        try {
            terminada = actual.tick(mob);
        } catch (Exception e) {
            LOGGER.error("[Cobalt] La tarea '{}' falló y se descarta", actual.nombre(), e);
            terminada = true;
        }
        if (terminada) actual = null;
    }

    static void feedback(String archivo, String estado, String detalle, JsonObject extra) {
        JsonObject json = extra != null ? extra : new JsonObject();
        json.addProperty("status", estado);
        json.addProperty("detalle", detalle == null ? "" : detalle);
        NoxSensorWriter.escribirAtomico(archivo, json.toString());
    }

    static void acercarse(CobaltEntity mob, double x, double y, double z, double velocidad) {
        if (!mob.getNavigation().moveTo(x, y, z, velocidad)) {
            mob.setModoVuelo(true);
            mob.getMoveControl().setWantedPosition(x, y, z, velocidad);
        }
    }

    static boolean inventarioSinHuecos(Container inventario) {
        for (int i = 0; i < inventario.getContainerSize(); i++) {
            if (inventario.getItem(i).isEmpty()) return false;
        }
        return true;
    }

    public static final class TareaMinar implements Tarea {
        private static final int RADIO = 10;
        private static final int MAX_BLOQUES = 64;
        private static final int MAX_TICKS_NORMAL = 4800;    // 4 minutos
        private static final int MAX_TICKS_PROFUNDO = 12000; // 10 minutos si puede explorar en profundidad
        private static final int RADIO_TUNEL = 14;           // hasta dónde se busca una veta enterrada
        private static final int MAX_TUNELES = 40;           // túneles hacia vetas por orden (solo cuentan los planificados)
        private static final int MAX_EXCAVADOS = 600;        // bloques de túnel/escalera por orden
        private static final int NODOS_SEGMENTO = 8;         // pasos de cada tramo de exploración
        private static final int INTERVALO_ANTORCHA = 10;    // una antorcha cada 10 bloques de túnel
        private static final int MAX_TICKS_RETORNO = 1500;   // 75 s para volver a la entrada
        private static final int MAX_TICKS_POR_BLOQUE = 240; // 12 s intentando llegar a uno
        private static final double ALCANCE = 4.5D;

        private final String material;
        private final int cantidad;
        private int minados = 0;
        private int ticks = 0;
        private int ticksBloque = 0;
        private int ticksRomper = -1;
        private BlockPos objetivo = null;
        private BlockPos acceso = null;
        private List<BlockPos> candidatos = new ArrayList<>();
        private final Set<BlockPos> descartados = new HashSet<>();
        private BlockPos base = null;
        private boolean baseLeida = false;
        private String motivoParcial = null;
        // Túnel hacia menas enterradas (interruptor mineria_tunel)
        private final ArrayDeque<BlockPos> ruta = new ArrayDeque<>();
        private boolean objetivoEnRuta = false;
        private BlockPos minaDestino = null;
        private int excavados = 0;
        private int tunelesPlanificados = 0;
        private int sinAntorcha = 0;
        private BlockPos frente = null;            // pies de Cobalt al final del último tramo planificado
        private BlockPos frenteAnterior = null;    // frente antes del tramo en curso (para deshacerlo si se aborta)
        private Direction direccionPrevia = null;
        private final ArrayList<BlockPos> rastro = new ArrayList<>(); // frentes sucesivos: el camino de vuelta
        private boolean volviendo = false;
        private String motivoFinal = null;
        private int ticksRetorno = 0;
        private final int maxTicks;

        public TareaMinar(String material, int cantidad) {
            this(material, cantidad, 0);
        }

        public TareaMinar(String material, int cantidad, int limiteMinutos) {
            this.material = material == null || material.isBlank() ? "cualquiera" : material.trim();
            this.cantidad = Math.max(1, Math.min(MAX_BLOQUES, cantidad));
            int tope = com.example.cobaltbot.util.NoxConfig.activo("mineria_profunda") ? MAX_TICKS_PROFUNDO : MAX_TICKS_NORMAL;
            this.maxTicks = limiteMinutos > 0 ? Math.min(tope, limiteMinutos * 1200) : tope;
        }

        @Override
        public String nombre() {
            String fase = volviendo ? " (volviendo)" : frente != null ? " (explorando y=" + frente.getY() + ")" : "";
            return "mine:" + material + " " + minados + "/" + cantidad + fase;
        }

        @Override
        public void cancelar(CobaltEntity mob) {
            finalizar(mob, "cancelada por una orden de detenerse"); // cancelar es inmediato: no se vuelve a la entrada
        }

        @Override
        public boolean tick(CobaltEntity mob) {
            if (!(mob.level() instanceof ServerLevel nivel)) return true;
            if (!baseLeida) {
                base = NoxMinado.leerBase();
                baseLeida = true;
            }
            if (volviendo) return volver(mob);
            if (++ticks > maxTicks) return terminar(mob, "tiempo agotado (" + (maxTicks / 1200) + " min)");
            if (minados >= cantidad) return terminar(mob, null);
            if (inventarioSinHuecos(mob.getCobaltInventory())) return terminar(mob, "inventario lleno");

            if (objetivo == null) {
                boolean hay = !ruta.isEmpty() ? tomarDeRuta(mob, nivel) : elegirObjetivo(mob, nivel);
                if (!hay && motivoParcial == null && ruta.isEmpty() && planificarTunel(mob, nivel)) hay = tomarDeRuta(mob, nivel);
                if (!hay && motivoParcial == null && ruta.isEmpty() && explorar(mob, nivel)) hay = tomarDeRuta(mob, nivel);
                if (!hay) {
                    String razon = motivoParcial != null ? motivoParcial
                            : (minados > 0 ? "no quedan más bloques accesibles"
                            : "no encontré '" + material + "' a la vista ni al alcance de un túnel seguro"
                            + (excavados > 0 ? " tras abrir " + excavados + " bloques de túnel" : " en " + RADIO_TUNEL + " bloques"));
                    return terminar(mob, razon);
                }
            }
            if (objetivo == null) return false;

            if (++ticksBloque > MAX_TICKS_POR_BLOQUE) { // no se llega a este bloque: se descarta y se sigue con otro
                descartarObjetivo();
                return false;
            }
            BlockState estado = nivel.getBlockState(objetivo);
            if (estado.isAir()) { // alguien lo rompió (o ya lo abrimos): se sigue con el siguiente
                objetivo = null;
                objetivoEnRuta = false;
                return false;
            }
            boolean valido = objetivoEnRuta
                    ? NoxMinado.excavableSeguro(nivel, objetivo, base, NoxMinado.RADIO_BASE_PROTEGIDA) // pudo aparecer agua/lava al lado
                    : NoxMinado.esObjetivo(estado, material) && NoxMinado.esMinable(estado);
            if (!valido) {
                if (objetivoEnRuta) descartarObjetivo(); else objetivo = null;
                return false;
            }

            Vec3 centro = Vec3.atCenterOf(objetivo);
            boolean alAlcance = mob.getEyePosition().distanceTo(centro) <= ALCANCE && hayLineaDeVista(mob, nivel, objetivo);
            if (!alAlcance) {
                BlockPos destino = acceso != null ? acceso : objetivo;
                acercarse(mob, destino.getX() + 0.5D, destino.getY() + 0.5D, destino.getZ() + 0.5D, 1.5D);
                return false;
            }

            mob.getNavigation().stop();
            mob.getLookControl().setLookAt(centro.x, centro.y, centro.z);

            ItemStack herramienta = mejorHerramienta(mob, estado);
            if (ticksRomper < 0) {
                if (estado.requiresCorrectToolForDrops() && (herramienta.isEmpty() || !herramienta.isCorrectToolForDrops(estado))) {
                    motivoParcial = "necesito una herramienta adecuada para " + material + " (por ejemplo un pico)";
                    descartarObjetivo();
                    return false;
                }
                float velocidad = herramienta.isEmpty() ? 1.0F : herramienta.getDestroySpeed(estado);
                ticksRomper = NoxMinado.ticksParaRomper(estado.getDestroySpeed(nivel, objetivo), velocidad);
            }
            if (ticksRomper % 6 == 0) mob.swing(InteractionHand.MAIN_HAND);
            if (--ticksRomper > 0) return false;

            return romper(mob, nivel, estado, herramienta);
        }

        private boolean elegirObjetivo(CobaltEntity mob, ServerLevel nivel) {
            candidatos.removeIf(p -> descartados.contains(p) || !NoxMinado.esObjetivo(nivel.getBlockState(p), material));
            if (candidatos.isEmpty()) {
                candidatos = NoxMinado.buscarBloques(nivel, mob.blockPosition(), RADIO, s -> NoxMinado.esObjetivo(s, material),
                        base, NoxMinado.RADIO_BASE_PROTEGIDA, 24, descartados::contains);
            }
            if (candidatos.isEmpty()) return false;
            objetivo = candidatos.remove(0);
            acceso = NoxMinado.accesoAire(nivel, objetivo, mob.getX(), mob.getY(), mob.getZ());
            ticksBloque = 0;
            ticksRomper = -1;
            return true;
        }

        private static boolean hayLineaDeVista(CobaltEntity mob, ServerLevel nivel, BlockPos bloque) {
            BlockHitResult golpe = nivel.clip(new ClipContext(mob.getEyePosition(), Vec3.atCenterOf(bloque),
                    ClipContext.Block.COLLIDER, ClipContext.Fluid.NONE, mob));
            if (golpe.getType() == HitResult.Type.MISS || golpe.getBlockPos().equals(bloque)) return true;
            BlockState objetivoEstado = nivel.getBlockState(bloque);
            boolean parteDeArbol = NoxArboles.esTronco(objetivoEstado) || objetivoEstado.is(net.minecraft.tags.BlockTags.LEAVES);
            BlockState tapa = nivel.getBlockState(golpe.getBlockPos());
            return parteDeArbol && (NoxArboles.esTronco(tapa) || tapa.is(net.minecraft.tags.BlockTags.LEAVES));
        }

        static ItemStack mejorHerramienta(CobaltEntity mob, BlockState estado) {
            ItemStack mejor = ItemStack.EMPTY;
            float velocidad = 1.0F;
            boolean mejorVale = false;
            Container inventario = mob.getCobaltInventory();
            for (int i = 0; i < inventario.getContainerSize(); i++) {
                ItemStack pila = inventario.getItem(i);
                if (NoxTools.tipoDeHerramienta(pila) == null) continue;
                if (com.example.cobaltbot.util.NoxConfig.activo("proteger_durabilidad") && NoxTools.esFragil(pila)) continue; // no se rompe la herramienta
                float v = pila.getDestroySpeed(estado);
                boolean vale = estado.requiresCorrectToolForDrops() && valeParaBotin(pila, estado);
                if (vale != mejorVale ? vale : v > velocidad) {
                    velocidad = v;
                    mejor = pila;
                    mejorVale = vale;
                }
            }
            return mejor;
        }

        static boolean valeParaBotin(ItemStack herramienta, BlockState estado) {
            return !estado.requiresCorrectToolForDrops() || (!herramienta.isEmpty() && herramienta.isCorrectToolForDrops(estado));
        }

        private boolean romper(CobaltEntity mob, ServerLevel nivel, BlockState estado, ItemStack herramienta) {
            BlockPos roto = objetivo;
            List<ItemStack> botin = Block.getDrops(estado, nivel, objetivo, nivel.getBlockEntity(objetivo), mob, herramienta);
            nivel.destroyBlock(objetivo, false, mob);

            SimpleContainer inventario = mob.getCobaltInventory();
            boolean lleno = false;
            boolean esLoPedido = NoxMinado.esObjetivo(estado, material);
            for (ItemStack drop : botin) {
                if (!NoxMinado.debeConservar(drop, contar(inventario, drop), esLoPedido)) continue; // ripio de sobra: se descarta
                ItemStack sobrante = inventario.addItem(drop.copy());
                if (!sobrante.isEmpty()) {
                    Block.popResource(nivel, objetivo, sobrante); // no cabe: cae al suelo
                    lleno = true;
                }
            }
            if (!herramienta.isEmpty()) herramienta.hurtAndBreak(1, mob, m -> {});
            inventario.setChanged();

            if (esLoPedido) {
                minados++;
            } else {
                excavados++; // el túnel no cuenta como mena
                if (++sinAntorcha >= INTERVALO_ANTORCHA && colocarAntorcha(mob, nivel, roto)) sinAntorcha = 0;
            }
            objetivo = null;
            objetivoEnRuta = false;
            ticksRomper = -1;
            return lleno ? terminar(mob, "inventario lleno") : false;
        }

        private boolean colocarAntorcha(CobaltEntity mob, ServerLevel nivel, BlockPos pos) {
            if (!com.example.cobaltbot.util.NoxConfig.activo("antorchas_tunel")) return false;
            SimpleContainer inventario = mob.getCobaltInventory();
            int hueco = -1;
            for (int i = 0; i < inventario.getContainerSize(); i++) {
                if (inventario.getItem(i).is(net.minecraft.world.item.Items.TORCH)) {
                    hueco = i;
                    break;
                }
            }
            if (hueco < 0) return false;
            BlockState antorcha = net.minecraft.world.level.block.Blocks.TORCH.defaultBlockState();
            if (!nivel.getBlockState(pos).isAir() || !antorcha.canSurvive(nivel, pos)) return false;
            nivel.setBlock(pos, antorcha, 3);
            inventario.removeItem(hueco, 1);
            return true;
        }

        private void descartarObjetivo() {
            descartados.add(objetivo);
            if (objetivoEnRuta) {
                if (minaDestino != null) {
                    descartados.add(minaDestino);
                } else if (frenteAnterior != null) {
                    frente = frenteAnterior;
                    if (rastro.size() > 1) rastro.remove(rastro.size() - 1);
                    direccionPrevia = null;
                    frenteAnterior = null;
                }
                ruta.clear();
            }
            objetivo = null;
            objetivoEnRuta = false;
        }

        private static int contar(Container inventario, ItemStack modelo) {
            int total = 0;
            for (int i = 0; i < inventario.getContainerSize(); i++) {
                if (ItemStack.isSameItem(inventario.getItem(i), modelo)) total += inventario.getItem(i).getCount();
            }
            return total;
        }

        private BlockPos puntoDeBusqueda(ServerLevel nivel, CobaltEntity mob) {
            if (frente != null && nivel.getBlockState(frente).isAir() && mob.blockPosition().distSqr(frente) <= 144.0D) return frente;
            return mob.blockPosition();
        }

        private boolean explorar(CobaltEntity mob, ServerLevel nivel) {
            if (!com.example.cobaltbot.util.NoxConfig.activo("mineria_profunda") || !NoxMinado.esMena(material)) return false;
            if (excavados >= MAX_EXCAVADOS || nivel.dimension() == Level.END) return false;
            boolean nether = nivel.dimension() == Level.NETHER;
            int yObjetivo = Math.max(NoxMinado.alturaIdeal(material, nether), nivel.getMinBuildHeight() + 6);
            if (frente == null) {
                BlockPos p = mob.blockPosition();
                for (int i = 0; i < 24 && nivel.getBlockState(p.below()).isAir(); i++) p = p.below(); // hasta el suelo
                frente = p;
                rastro.add(frente);
                mob.avisarAlDueno("§7[Cobalt]: No hay " + material + " cerca. Exploro en profundidad hacia y=" + yObjetivo
                        + " (puede tardar; 'stop' me detiene). Volveré a la entrada del túnel al terminar.");
            }
            boolean bajar = frente.getY() > yObjetivo + 1;
            NoxMinado.Segmento tramo = NoxMinado.elegirSegmento(nivel, frente, direccionPrevia, bajar, yObjetivo, NODOS_SEGMENTO, base,
                    NoxMinado.RADIO_BASE_PROTEGIDA, nivel::hasChunkAt, descartados::contains);
            if (tramo == null) return false;
            frenteAnterior = frente;
            frente = tramo.frente();
            direccionPrevia = tramo.dir();
            rastro.add(frente);
            minaDestino = null;
            ruta.clear();
            ruta.addAll(tramo.celdas());
            return true;
        }

        private boolean volver(CobaltEntity mob) {
            if (++ticksRetorno > MAX_TICKS_RETORNO || rastro.isEmpty()) return finalizar(mob, motivoFinal);
            BlockPos meta = rastro.get(rastro.size() - 1);
            if (mob.position().distanceTo(Vec3.atCenterOf(meta)) <= 2.5D) {
                rastro.remove(rastro.size() - 1);
                return false;
            }
            acercarse(mob, meta.getX() + 0.5D, meta.getY() + 0.1D, meta.getZ() + 0.5D, 1.6D);
            return false;
        }

        private boolean tomarDeRuta(CobaltEntity mob, ServerLevel nivel) {
            while (!ruta.isEmpty()) {
                BlockPos siguiente = ruta.pollFirst();
                if (nivel.getBlockState(siguiente).isAir()) continue; // ya está abierto
                objetivo = siguiente;
                objetivoEnRuta = true;
                acceso = NoxMinado.accesoAire(nivel, objetivo, mob.getX(), mob.getY(), mob.getZ());
                ticksBloque = 0;
                ticksRomper = -1;
                return true;
            }
            return false;
        }

        private boolean planificarTunel(CobaltEntity mob, ServerLevel nivel) {
            if (!com.example.cobaltbot.util.NoxConfig.activo("mineria_tunel")) return false;
            if (tunelesPlanificados >= MAX_TUNELES || excavados >= MAX_EXCAVADOS) return false;
            List<BlockPos> plan = NoxMinado.planificarTunel(nivel, puntoDeBusqueda(nivel, mob), s -> NoxMinado.esObjetivo(s, material), base,
                    NoxMinado.RADIO_BASE_PROTEGIDA, RADIO_TUNEL, NoxMinado.MAX_EXCAVACION, descartados::contains);
            if (plan.isEmpty()) return false;
            tunelesPlanificados++;
            ruta.clear();
            ruta.addAll(plan);
            minaDestino = plan.get(plan.size() - 1);
            mob.avisarAlDueno("§7[Cobalt]: No veo " + material + " a la vista. Abro un túnel de " + plan.size() + " bloque(s) hasta una veta cercana.");
            return true;
        }

        private boolean terminar(CobaltEntity mob, String motivo) {
            if (volviendo || rastro.size() < 2) return finalizar(mob, motivo);
            volviendo = true;
            motivoFinal = motivo;
            ticksRetorno = 0;
            mob.getNavigation().stop();
            mob.avisarAlDueno("§7[Cobalt]: Termino aquí y vuelvo a la entrada del túnel.");
            return false;
        }

        private boolean finalizar(CobaltEntity mob, String motivo) {
            String estado = motivo == null ? "success" : (minados > 0 ? "partial" : "failed");
            JsonObject extra = new JsonObject();
            extra.addProperty("mined", minados);
            extra.addProperty("excavated", excavados);
            extra.addProperty("deepest_y", frente != null ? frente.getY() : (int) Math.floor(mob.getY()));
            extra.addProperty("wanted", cantidad);
            extra.addProperty("material", material);
            feedback("mine_feedback.json", estado, motivo, extra);
            if (motivo == null) {
                mob.avisarAlDueno("§a[Cobalt]: Minería completada: " + minados + " bloque(s) de " + material
                        + (excavados > 0 ? " (abrí " + excavados + " bloques de túnel)." : "."));
            } else {
                mob.avisarAlDueno("§e[Cobalt]: Minería detenida (" + minados + "/" + cantidad + " de " + material + "): " + motivo + ".");
            }
            return true;
        }
    }

    public static final class TareaDar implements Tarea {
        private final String material;
        private final int cantidad; // 0 = todo lo que coincida
        private int ticks = 0;

        public TareaDar(String material, int cantidad) {
            this.material = material == null ? "" : material.trim();
            this.cantidad = Math.max(0, cantidad);
        }

        @Override
        public String nombre() {
            return "give:" + material;
        }

        @Override
        public boolean tick(CobaltEntity mob) {
            Player dueno = mob.getCobaltOwner();
            if (dueno == null) return terminar(mob, "failed", 0, "no encuentro al jugador");
            if (++ticks > 600) return terminar(mob, "failed", 0, "no logré llegar hasta el jugador");
            if (mob.distanceTo(dueno) > 3.5F) {
                acercarse(mob, dueno.getX(), dueno.getY(), dueno.getZ(), 1.6D);
                return false;
            }
            mob.getNavigation().stop();

            Container inventario = mob.getCobaltInventory();
            boolean todoLoUtil = NoxMinado.esGenerico(material); // sin material concreto: materiales, no herramientas ni comida
            int dados = 0;
            for (int i = 0; i < inventario.getContainerSize(); i++) {
                ItemStack pila = inventario.getItem(i);
                if (pila.isEmpty()) continue;
                boolean encaja = todoLoUtil
                        ? (NoxTools.tipoDeHerramienta(pila) == null && !pila.getItem().isEdible())
                        : NoxMinado.itemCoincide(pila, material);
                if (!encaja) continue;
                int n = cantidad == 0 ? pila.getCount() : Math.min(pila.getCount(), cantidad - dados);
                if (n <= 0) break;
                ItemHandlerHelper.giveItemToPlayer(dueno, pila.split(n));
                dados += n;
                if (cantidad > 0 && dados >= cantidad) break;
            }
            inventario.setChanged();
            return terminar(mob, dados > 0 ? "success" : "failed", dados, dados > 0 ? null : "no tengo '" + material + "' para darte");
        }

        private boolean terminar(CobaltEntity mob, String estado, int dados, String motivo) {
            JsonObject extra = new JsonObject();
            extra.addProperty("given", dados);
            extra.addProperty("material", material);
            feedback("logistica_feedback.json", estado, motivo, extra);
            if (dados > 0) mob.avisarAlDueno("§a[Cobalt]: Te entregué " + dados + " x " + (material.isEmpty() ? "materiales" : material) + ".");
            else if (motivo != null) mob.avisarAlDueno("§e[Cobalt]: " + motivo + ".");
            return true;
        }
    }

    static java.util.List<net.minecraft.world.level.block.entity.BlockEntity> buscarAlmacenes(ServerLevel nivel, BlockPos centro, int radio) {
        java.util.List<net.minecraft.world.level.block.entity.BlockEntity> lista = new java.util.ArrayList<>();
        double radio2 = (double) radio * radio;
        for (int cx = (centro.getX() - radio) >> 4; cx <= (centro.getX() + radio) >> 4; cx++) {
            for (int cz = (centro.getZ() - radio) >> 4; cz <= (centro.getZ() + radio) >> 4; cz++) {
                net.minecraft.world.level.chunk.LevelChunk chunk = nivel.getChunkSource().getChunkNow(cx, cz); // solo chunks ya cargados
                if (chunk == null) continue;
                for (java.util.Map.Entry<BlockPos, net.minecraft.world.level.block.entity.BlockEntity> entrada : chunk.getBlockEntities().entrySet()) {
                    net.minecraft.world.level.block.entity.BlockEntity be = entrada.getValue();
                    if (be.isRemoved() || entrada.getKey().distSqr(centro) > radio2) continue;
                    String ruta = net.minecraft.core.registries.BuiltInRegistries.BLOCK.getKey(be.getBlockState().getBlock()).getPath();
                    if (!NoxMinado.esAlmacen(ruta)) continue;
                    if (!be.getCapability(net.minecraftforge.common.capabilities.ForgeCapabilities.ITEM_HANDLER, null).isPresent()) continue;
                    lista.add(be);
                }
            }
        }
        lista.sort(java.util.Comparator.comparingDouble(be -> be.getBlockPos().distSqr(centro)));
        return lista;
    }

    private static net.minecraftforge.items.IItemHandler manejadorDe(net.minecraft.world.level.block.entity.BlockEntity be) {
        return be.getCapability(net.minecraftforge.common.capabilities.ForgeCapabilities.ITEM_HANDLER, null).resolve().orElse(null);
    }

    private static boolean esGuardable(ItemStack pila) {
        return !pila.isEmpty() && NoxTools.tipoDeHerramienta(pila) == null && !pila.getItem().isEdible();
    }

    private static int contarGuardables(Container inventario) {
        int total = 0;
        for (int i = 0; i < inventario.getContainerSize(); i++) {
            if (esGuardable(inventario.getItem(i))) total += inventario.getItem(i).getCount();
        }
        return total;
    }

    public static final class TareaGuardar implements Tarea {
        private static final int RADIO_BUSQUEDA = 32;

        private final BlockPos destinoPedido; // null = el almacén más cercano
        private BlockPos destino;
        private final java.util.List<String> materiales;
        private int ticks = 0;

        public TareaGuardar(BlockPos destino) {
            this(destino, java.util.List.of());
        }

        public TareaGuardar(BlockPos destino, java.util.List<String> materiales) {
            this.destinoPedido = destino;
            this.destino = destino;
            this.materiales = materiales == null ? java.util.List.of() : materiales;
        }

        private boolean guardable(ItemStack pila) {
            if (materiales.isEmpty()) return esGuardable(pila);
            if (pila.isEmpty()) return false;
            for (String m : materiales) if (NoxMinado.itemCoincide(pila, m)) return true;
            return false;
        }

        private int contar(Container inventario) {
            int total = 0;
            for (int i = 0; i < inventario.getContainerSize(); i++) if (guardable(inventario.getItem(i))) total += inventario.getItem(i).getCount();
            return total;
        }

        @Override
        public String nombre() {
            return destinoPedido == null ? "store" : "store_at:" + destinoPedido.toShortString();
        }

        @Override
        public boolean tick(CobaltEntity mob) {
            if (!(mob.level() instanceof ServerLevel nivel)) return true;
            if (++ticks > 600) return terminar(mob, "failed", 0, "no logré llegar al destino");
            if (destino == null) { // sin coordenadas: el almacén más cercano dentro del radio de búsqueda
                java.util.List<net.minecraft.world.level.block.entity.BlockEntity> cercanos = buscarAlmacenes(nivel, mob.blockPosition(), RADIO_BUSQUEDA);
                if (cercanos.isEmpty()) return terminar(mob, "failed", 0, "no encontré un cofre o barril a " + RADIO_BUSQUEDA + " bloques");
                destino = cercanos.get(0).getBlockPos();
            }
            if (mob.position().distanceTo(Vec3.atCenterOf(destino)) > 3.5D) {
                acercarse(mob, destino.getX() + 0.5D, destino.getY() + 0.5D, destino.getZ() + 0.5D, 1.6D);
                return false;
            }
            mob.getNavigation().stop();

            java.util.List<net.minecraft.world.level.block.entity.BlockEntity> almacenes =
                    buscarAlmacenes(nivel, destino, 6);
            if (almacenes.isEmpty()) return terminar(mob, "failed", 0, "no encontré un cofre o barril en ese punto");

            SimpleContainer inventario = mob.getCobaltInventory();
            int movidos = 0;
            for (net.minecraft.world.level.block.entity.BlockEntity almacen : almacenes) {
                net.minecraftforge.items.IItemHandler manejador = manejadorDe(almacen);
                if (manejador == null) continue;
                for (int i = 0; i < inventario.getContainerSize(); i++) {
                    ItemStack pila = inventario.getItem(i);
                    if (!guardable(pila)) continue;
                    ItemStack resto = net.minecraftforge.items.ItemHandlerHelper.insertItem(manejador, pila.copy(), false);
                    int guardados = pila.getCount() - resto.getCount();
                    if (guardados > 0) {
                        inventario.setItem(i, resto);
                        movidos += guardados;
                    }
                }
                if (contar(inventario) == 0) break;
            }
            inventario.setChanged();

            int sobran = contar(inventario);
            if (movidos == 0 && sobran > 0) return terminar(mob, "failed", 0, "los contenedores cercanos están llenos");
            if (sobran > 0) return terminar(mob, "partial", movidos, "los contenedores se llenaron (me quedan " + sobran + " ítems)");
            return terminar(mob, "success", movidos, movidos == 0 ? (materiales.isEmpty() ? "no tenía nada que guardar (conservo herramientas y comida)" : "no llevaba nada de lo que me pediste guardar") : null);
        }

        private boolean terminar(CobaltEntity mob, String estado, int movidos, String detalle) {
            JsonObject extra = new JsonObject();
            extra.addProperty("stored", movidos);
            feedback("logistica_feedback.json", estado, detalle, extra);
            if (movidos > 0) mob.avisarAlDueno("\u00a7a[Cobalt]: Guard\u00e9 " + movidos + " \u00edtems en el almac\u00e9n" + (detalle != null ? " (" + detalle + ")" : "") + ".");
            else if (detalle != null) mob.avisarAlDueno("\u00a7e[Cobalt]: " + detalle + ".");
            return true;
        }
    }

    public static final class TareaRestock implements Tarea {
        private static final int RADIO_BUSQUEDA = 32;

        private final String material;
        private final int cantidad;
        private int ticks = 0;
        private int conseguidos = 0;
        private net.minecraft.world.level.block.entity.BlockEntity destino = null;
        private final java.util.Set<BlockPos> visitados = new java.util.HashSet<>();

        public TareaRestock(String material, int cantidad) {
            this.material = material == null ? "" : material.trim();
            this.cantidad = Math.max(1, Math.min(256, cantidad));
        }

        @Override
        public String nombre() {
            return "restock:" + material + " " + conseguidos + "/" + cantidad;
        }

        @Override
        public boolean tick(CobaltEntity mob) {
            if (!(mob.level() instanceof ServerLevel nivel)) return true;
            if (material.isEmpty() || NoxMinado.esGenerico(material)) return terminar(mob, "failed", "no me dijiste qu\u00e9 material traer");
            if (++ticks > 1200) return terminar(mob, conseguidos > 0 ? "partial" : "failed", "tiempo agotado (1 min)");

            if (destino == null || destino.isRemoved()) {
                destino = elegirAlmacen(nivel, mob);
                if (destino == null) {
                    return terminar(mob, conseguidos > 0 ? "partial" : "failed",
                            conseguidos > 0 ? "no hay m\u00e1s '" + material + "' en los contenedores"
                                    : "no hay '" + material + "' en contenedores a " + RADIO_BUSQUEDA + " bloques");
                }
            }
            Vec3 centro = Vec3.atCenterOf(destino.getBlockPos());
            if (mob.position().distanceTo(centro) > 4.0D) {
                acercarse(mob, centro.x, centro.y, centro.z, 1.6D);
                return false;
            }
            mob.getNavigation().stop();

            net.minecraftforge.items.IItemHandler manejador = manejadorDe(destino);
            if (manejador != null) conseguidos += extraer(mob, nivel, manejador, cantidad - conseguidos);
            visitados.add(destino.getBlockPos());
            destino = null; // siguiente almac\u00e9n si a\u00fan falta
            if (conseguidos >= cantidad || inventarioSinHuecos(mob.getCobaltInventory())) {
                return terminar(mob, conseguidos >= cantidad ? "success" : "partial", conseguidos >= cantidad ? null : "inventario lleno");
            }
            return false;
        }

        private net.minecraft.world.level.block.entity.BlockEntity elegirAlmacen(ServerLevel nivel, CobaltEntity mob) {
            for (net.minecraft.world.level.block.entity.BlockEntity be : buscarAlmacenes(nivel, mob.blockPosition(), RADIO_BUSQUEDA)) {
                if (visitados.contains(be.getBlockPos())) continue;
                net.minecraftforge.items.IItemHandler manejador = manejadorDe(be);
                if (manejador == null) continue;
                for (int i = 0; i < manejador.getSlots(); i++) {
                    if (NoxMinado.itemCoincide(manejador.getStackInSlot(i), material)) return be;
                }
            }
            return null;
        }

        private int extraer(CobaltEntity mob, ServerLevel nivel, net.minecraftforge.items.IItemHandler manejador, int quiero) {
            SimpleContainer inventario = mob.getCobaltInventory();
            int total = 0;
            for (int i = 0; i < manejador.getSlots() && total < quiero; i++) {
                if (!NoxMinado.itemCoincide(manejador.getStackInSlot(i), material)) continue;
                ItemStack sacada = manejador.extractItem(i, Math.min(quiero - total, manejador.getStackInSlot(i).getCount()), false);
                if (sacada.isEmpty()) continue;
                ItemStack resto = inventario.addItem(sacada.copy());
                total += sacada.getCount() - resto.getCount();
                if (!resto.isEmpty()) { // no cabe en Cobalt: se devuelve al contenedor (o cae al suelo si tampoco)
                    ItemStack devuelto = net.minecraftforge.items.ItemHandlerHelper.insertItem(manejador, resto, false);
                    if (!devuelto.isEmpty()) net.minecraft.world.level.block.Block.popResource(nivel, mob.blockPosition(), devuelto);
                    break;
                }
            }
            inventario.setChanged();
            return total;
        }

        private boolean terminar(CobaltEntity mob, String estado, String detalle) {
            JsonObject extra = new JsonObject();
            extra.addProperty("obtained", conseguidos);
            extra.addProperty("wanted", cantidad);
            extra.addProperty("material", material);
            feedback("logistica_feedback.json", estado, detalle, extra);
            if (conseguidos > 0) mob.avisarAlDueno("\u00a7a[Cobalt]: Traje " + conseguidos + " x " + material + " de los almacenes" + (detalle != null ? " (" + detalle + ")" : "") + ".");
            else if (detalle != null) mob.avisarAlDueno("\u00a7e[Cobalt]: " + detalle + ".");
            return true;
        }
    }

    public static final class TareaLimpiar implements Tarea {
        private static final int MAX_TICKS = 6000;           // 5 minutos
        private static final int MAX_TICKS_POR_BLOQUE = 160; // 8 s intentando llegar a uno
        private static final double ALCANCE = 4.5D;

        private final BlockPos a;
        private final BlockPos b;
        private List<BlockPos> pendientes = null;
        private int total = 0;
        private int limpiados = 0;
        private int omitidos = 0;
        private int ticks = 0;
        private int ticksBloque = 0;
        private int ticksRomper = -1;
        private BlockPos objetivo = null;
        private BlockPos base = null;

        public TareaLimpiar(BlockPos a, BlockPos b) {
            this.a = a;
            this.b = b;
        }

        @Override
        public String nombre() {
            return "clear_area " + limpiados + "/" + total;
        }

        @Override
        public void cancelar(CobaltEntity mob) {
            terminar(mob, "cancelada por una orden de detenerse");
        }

        @Override
        public boolean tick(CobaltEntity mob) {
            if (!(mob.level() instanceof ServerLevel nivel)) return true;
            if (pendientes == null) {
                if (NoxMinado.volumenCaja(a.getX(), a.getY(), a.getZ(), b.getX(), b.getY(), b.getZ()) > NoxMinado.MAX_VOLUMEN_CAJA) {
                    return terminar(mob, "la zona es demasiado grande (m\u00e1ximo " + NoxMinado.MAX_VOLUMEN_CAJA + " bloques de volumen)");
                }
                base = NoxMinado.leerBase();
                pendientes = NoxMinado.bloquesALimpiar(nivel, a, b, base, NoxMinado.RADIO_BASE_LIMPIEZA, NoxMinado.MAX_BLOQUES_LIMPIEZA);
                total = pendientes.size();
                if (total == 0) return terminar(mob, null); // ya estaba despejado (o todo es zona protegida/no limpiable)
            }
            if (++ticks > MAX_TICKS) return terminar(mob, "tiempo agotado (5 min)");

            if (objetivo == null) {
                while (!pendientes.isEmpty() && objetivo == null) {
                    BlockPos candidato = pendientes.remove(0);
                    if (NoxMinado.limpiableSeguroPlaneado(nivel, candidato)) objetivo = candidato; // si ya es aire u otra cosa, se salta
                }
                if (objetivo == null) return terminar(mob, null);
                ticksBloque = 0;
                ticksRomper = -1;
            }
            if (++ticksBloque > MAX_TICKS_POR_BLOQUE) { // no se llega a este bloque: se omite
                omitidos++;
                objetivo = null;
                return false;
            }
            BlockState estado = nivel.getBlockState(objetivo);
            if (!NoxMinado.limpiableSeguroPlaneado(nivel, objetivo)) { // alguien lo quit\u00f3 o algo cambi\u00f3 a su alrededor
                objetivo = null;
                return false;
            }

            Vec3 centro = Vec3.atCenterOf(objetivo);
            if (mob.getEyePosition().distanceTo(centro) > ALCANCE || !TareaMinar.hayLineaDeVista(mob, nivel, objetivo)) {
                BlockPos acceso = NoxMinado.accesoAire(nivel, objetivo, mob.getX(), mob.getY(), mob.getZ());
                BlockPos destino = acceso != null ? acceso : objetivo;
                acercarse(mob, destino.getX() + 0.5D, destino.getY() + 0.5D, destino.getZ() + 0.5D, 1.5D);
                return false;
            }

            mob.getNavigation().stop();
            mob.getLookControl().setLookAt(centro.x, centro.y, centro.z);
            ItemStack herramienta = TareaMinar.mejorHerramienta(mob, estado);
            if (ticksRomper < 0) {
                float velocidad = herramienta.isEmpty() ? 1.0F : herramienta.getDestroySpeed(estado);
                ticksRomper = NoxMinado.ticksParaRomper(estado.getDestroySpeed(nivel, objetivo), velocidad);
            }
            if (ticksRomper % 6 == 0) mob.swing(InteractionHand.MAIN_HAND);
            if (--ticksRomper > 0) return false;

            nivel.destroyBlock(objetivo, false, mob); // sin botín: es terreno que estorba, no material
            limpiados++;
            objetivo = null;
            return false;
        }

        private boolean terminar(CobaltEntity mob, String motivo) {
            String estado = motivo != null ? (limpiados > 0 ? "partial" : "failed") : (omitidos > 0 ? "partial" : "success");
            String detalle = motivo != null ? motivo : (omitidos > 0 ? omitidos + " bloque(s) no se pudieron alcanzar" : null);
            JsonObject extra = new JsonObject();
            extra.addProperty("cleared", limpiados);
            extra.addProperty("skipped", omitidos);
            extra.addProperty("planned", total);
            feedback("clear_feedback.json", estado, detalle, extra);
            if (estado.equals("success")) mob.avisarAlDueno("\u00a7a[Cobalt]: Zona despejada (" + limpiados + " bloques).");
            else mob.avisarAlDueno("\u00a7e[Cobalt]: Despeje " + estado + " (" + limpiados + "/" + total + "): " + detalle + ".");
            return true;
        }
    }

    public static final class TareaTalar implements Tarea {
        private static final int MAX_TICKS = 6000;            // 5 minutos
        private static final int MAX_TICKS_POR_TRONCO = 240;  // 12 s intentando llegar a uno
        private static final int MAX_CANTIDAD = 256;
        private static final int MAX_RADIO = 32;
        private static final double ALCANCE = 4.5D;

        private final int radio;
        private final int cantidad;
        private int talados = 0;
        private int arboles = 0;
        private int omitidos = 0;
        private int ticks = 0;
        private int ticksTronco = 0;
        private int ticksRomper = -1;
        private final ArrayDeque<BlockPos> pendientes = new ArrayDeque<>(); // troncos del árbol en curso, de abajo arriba
        private final Set<BlockPos> descartados = new HashSet<>();
        private BlockPos objetivo = null;
        private BlockPos acceso = null;
        private BlockPos base = null;
        private boolean baseLeida = false;
        private String motivoParcial = null;
        private int sinArboles = 0;

        public TareaTalar(int radio, int cantidad) {
            this.radio = Math.max(4, Math.min(MAX_RADIO, radio));
            this.cantidad = Math.max(1, Math.min(MAX_CANTIDAD, cantidad));
        }

        @Override
        public String nombre() {
            return "chop_wood " + talados + "/" + cantidad;
        }

        @Override
        public void cancelar(CobaltEntity mob) {
            terminar(mob, "cancelada por una orden de detenerse");
        }

        @Override
        public boolean tick(CobaltEntity mob) {
            if (!(mob.level() instanceof ServerLevel nivel)) return true;
            if (!baseLeida) {
                base = NoxMinado.leerBase();
                baseLeida = true;
            }
            if (++ticks > MAX_TICKS) return terminar(mob, "tiempo agotado (" + (MAX_TICKS / 1200) + " min)");
            if (talados >= cantidad) return terminar(mob, null);
            if (inventarioSinHuecos(mob.getCobaltInventory())) return terminar(mob, "inventario lleno");

            if (objetivo == null && !siguienteTronco(mob, nivel)) {
                return terminar(mob, motivoParcial != null ? motivoParcial
                        : talados > 0 ? "no quedan más árboles a la vista" : "no encontré árboles en " + radio + " bloques");
            }
            if (objetivo == null) return false;

            if (++ticksTronco > MAX_TICKS_POR_TRONCO) { // no se llega a este tronco: se salta y se sigue con otro
                omitir();
                return false;
            }
            BlockState estado = nivel.getBlockState(objetivo);
            if (!NoxArboles.esTronco(estado)) { // alguien lo taló ya
                objetivo = null;
                return false;
            }
            if (NoxArboles.lavaPegada(nivel, objetivo)) {
                omitir();
                return false;
            }

            Vec3 centro = Vec3.atCenterOf(objetivo);
            if (mob.getEyePosition().distanceTo(centro) > ALCANCE || !TareaMinar.hayLineaDeVista(mob, nivel, objetivo)) {
                BlockPos destino = acceso != null ? acceso : objetivo;
                acercarse(mob, destino.getX() + 0.5D, destino.getY() + 0.5D, destino.getZ() + 0.5D, 1.5D);
                return false;
            }
            mob.getNavigation().stop();
            mob.getLookControl().setLookAt(centro.x, centro.y, centro.z);

            ItemStack herramienta = TareaMinar.mejorHerramienta(mob, estado);
            if (ticksRomper < 0) {
                float velocidad = herramienta.isEmpty() ? 1.0F : herramienta.getDestroySpeed(estado);
                ticksRomper = NoxMinado.ticksParaRomper(estado.getDestroySpeed(nivel, objetivo), velocidad);
            }
            if (ticksRomper % 6 == 0) mob.swing(InteractionHand.MAIN_HAND);
            if (--ticksRomper > 0) return false;

            List<ItemStack> botin = Block.getDrops(estado, nivel, objetivo, null, mob, herramienta);
            nivel.destroyBlock(objetivo, false, mob);
            SimpleContainer inventario = mob.getCobaltInventory();
            for (ItemStack drop : botin) {
                ItemStack sobrante = inventario.addItem(drop.copy());
                if (!sobrante.isEmpty()) Block.popResource(nivel, objetivo, sobrante); // no cabe: cae al suelo
            }
            if (!herramienta.isEmpty()) herramienta.hurtAndBreak(1, mob, m -> {});
            inventario.setChanged();
            talados++;
            objetivo = null;
            if (pendientes.isEmpty()) arboles++;
            return false;
        }

        private void omitir() {
            descartados.add(objetivo);
            omitidos++;
            objetivo = null;
        }

        private boolean siguienteTronco(CobaltEntity mob, ServerLevel nivel) {
            while (objetivo == null) {
                BlockPos siguiente = pendientes.poll();
                if (siguiente == null) {
                    if (!elegirArbol(mob, nivel)) return false;
                    continue;
                }
                if (descartados.contains(siguiente) || !NoxArboles.esTronco(nivel.getBlockState(siguiente))) continue;
                objetivo = siguiente;
            }
            acceso = NoxMinado.accesoAire(nivel, objetivo, mob.getX(), mob.getY(), mob.getZ());
            ticksTronco = 0;
            ticksRomper = -1;
            return true;
        }

        private boolean elegirArbol(CobaltEntity mob, ServerLevel nivel) {
            for (int ronda = 0; ronda < 12; ronda++) {
                List<BlockPos> troncos = NoxMinado.buscarBloques(nivel, mob.blockPosition(), radio, NoxArboles::esTronco,
                        base, NoxMinado.RADIO_BASE_PROTEGIDA, 24, descartados::contains);
                if (troncos.isEmpty()) break;
                for (BlockPos tronco : troncos) {
                    List<BlockPos> arbol = NoxArboles.arbol(nivel, tronco);
                    if (arbol.isEmpty()) {
                        descartados.add(tronco);
                        continue;
                    }
                    boolean enBase = false;
                    for (BlockPos p : arbol) enBase |= NoxMinado.protegido(p, base, NoxMinado.RADIO_BASE_PROTEGIDA);
                    if (enBase) { // un árbol de la zona de la base se queda como está
                        descartados.addAll(arbol);
                        continue;
                    }
                    pendientes.addAll(arbol);
                    return true;
                }
                sinArboles++;
            }
            if (sinArboles > 0 && talados == 0) motivoParcial = "los troncos que hay cerca son parte de una construcción o de la zona de la base, no árboles";
            return false;
        }

        private boolean terminar(CobaltEntity mob, String motivo) {
            String estado = motivo != null ? (talados > 0 ? "partial" : "failed") : (omitidos > 0 ? "partial" : "success");
            String detalle = motivo != null ? motivo : (omitidos > 0 ? omitidos + " tronco(s) no se pudieron alcanzar" : null);
            JsonObject extra = new JsonObject();
            extra.addProperty("chopped", talados);
            extra.addProperty("trees", arboles);
            extra.addProperty("skipped", omitidos);
            extra.addProperty("wanted", cantidad);
            feedback("chop_feedback.json", estado, detalle, extra);
            if (estado.equals("success")) mob.avisarAlDueno("§a[Cobalt]: Talé " + talados + " troncos (" + arboles + " árboles).");
            else mob.avisarAlDueno("§e[Cobalt]: Tala " + estado + " (" + talados + "/" + cantidad + "): " + detalle + ".");
            return true;
        }
    }

    public static final class TareaPescar implements Tarea {
        private static final int MAX_TICKS = 24000;       // 20 minutos
        private static final int MAX_TICKS_LLEGAR = 600;  // 30 s buscando un sitio junto al agua
        private static final double ALCANCE = 5.0D;

        private final int cantidad;
        private final int radio;
        private final int maxTicks;
        private int capturas = 0;
        private int peces = 0;
        private int ticks = 0;
        private int ticksLlegar = 0;
        private int espera = -1;
        private BlockPos agua = null;
        private final java.util.Map<String, Integer> botin = new java.util.TreeMap<>();

        public TareaPescar(int cantidad, int radio, int minutos) {
            this.cantidad = Math.max(1, Math.min(64, cantidad));
            this.radio = Math.max(4, Math.min(32, radio));
            this.maxTicks = minutos > 0 ? Math.min(MAX_TICKS, minutos * 1200) : MAX_TICKS;
        }

        @Override
        public String nombre() {
            return "fish " + capturas + "/" + cantidad;
        }

        @Override
        public void cancelar(CobaltEntity mob) {
            terminar(mob, "cancelada por una orden de detenerse");
        }

        private static ItemStack buscarCana(CobaltEntity mob) {
            Container inventario = mob.getCobaltInventory();
            for (int i = 0; i < inventario.getContainerSize(); i++) {
                ItemStack pila = inventario.getItem(i);
                if (!NoxPesca.esCana(pila)) continue;
                if (com.example.cobaltbot.util.NoxConfig.activo("proteger_durabilidad") && NoxTools.esFragil(pila)) continue; // no se rompe la caña
                return pila;
            }
            return ItemStack.EMPTY;
        }

        @Override
        public boolean tick(CobaltEntity mob) {
            if (!(mob.level() instanceof ServerLevel nivel)) return true;
            if (++ticks > maxTicks) return terminar(mob, "tiempo agotado (" + (maxTicks / 1200) + " min)");
            if (capturas >= cantidad) return terminar(mob, null);
            if (inventarioSinHuecos(mob.getCobaltInventory())) return terminar(mob, "inventario lleno");
            ItemStack cana = buscarCana(mob);
            if (cana.isEmpty()) return terminar(mob, capturas > 0 ? "la caña se gastó" : "necesito una caña de pescar en el inventario");

            if (agua == null || !NoxPesca.esAguaPescable(nivel, agua)) { // sin sitio elegido, o se secó / la taparon
                agua = NoxPesca.buscarAgua(nivel, mob.blockPosition(), radio);
                espera = -1;
                ticksLlegar = 0;
                if (agua == null) return terminar(mob, capturas > 0 ? "no queda agua donde pescar" : "no encontré agua abierta en " + radio + " bloques");
            }
            Vec3 centro = Vec3.atCenterOf(agua);
            if (mob.position().distanceTo(centro) > ALCANCE) {
                if (++ticksLlegar > MAX_TICKS_LLEGAR) return terminar(mob, capturas > 0 ? "no logro acercarme más al agua" : "no logré llegar hasta el agua");
                acercarse(mob, centro.x, centro.y + 1.0D, centro.z, 1.4D);
                return false;
            }
            mob.getNavigation().stop();
            mob.getLookControl().setLookAt(centro.x, centro.y, centro.z);

            if (espera < 0) { // lanza el anzuelo
                espera = NoxPesca.esperaTicks(mob.getRandom(), NoxPesca.cebo(cana));
                mob.swing(InteractionHand.MAIN_HAND);
                nivel.playSound(null, agua, net.minecraft.sounds.SoundEvents.FISHING_BOBBER_THROW, net.minecraft.sounds.SoundSource.NEUTRAL, 0.5F, 0.4F);
            }
            if (--espera > 0) {
                if (espera % 20 == 0) nivel.sendParticles(net.minecraft.core.particles.ParticleTypes.FISHING, centro.x, centro.y + 0.4D, centro.z, 1, 0.2D, 0.0D, 0.2D, 0.0D);
                return false;
            }

            // pica: recoge la captura
            espera = -1;
            mob.swing(InteractionHand.MAIN_HAND);
            nivel.playSound(null, agua, net.minecraft.sounds.SoundEvents.FISHING_BOBBER_SPLASH, net.minecraft.sounds.SoundSource.NEUTRAL, 0.5F, 1.0F);
            nivel.sendParticles(net.minecraft.core.particles.ParticleTypes.SPLASH, centro.x, centro.y + 0.5D, centro.z, 12, 0.3D, 0.1D, 0.3D, 0.1D);
            SimpleContainer inventario = mob.getCobaltInventory();
            for (ItemStack pieza : NoxPesca.capturar(nivel, agua, cana, mob)) {
                botin.merge(net.minecraft.core.registries.BuiltInRegistries.ITEM.getKey(pieza.getItem()).toString(), pieza.getCount(), Integer::sum);
                if (pieza.is(net.minecraft.tags.ItemTags.FISHES)) peces += pieza.getCount();
                ItemStack sobrante = inventario.addItem(pieza.copy());
                if (!sobrante.isEmpty()) Block.popResource(nivel, mob.blockPosition(), sobrante); // no cabe: cae al suelo
            }
            cana.hurtAndBreak(1, mob, m -> {});
            inventario.setChanged();
            capturas++;
            return false;
        }

        private boolean terminar(CobaltEntity mob, String motivo) {
            String estado = motivo == null ? "success" : (capturas > 0 ? "partial" : "failed");
            JsonObject extra = new JsonObject();
            extra.addProperty("caught", capturas);
            extra.addProperty("fish", peces);
            extra.addProperty("wanted", cantidad);
            JsonObject items = new JsonObject();
            botin.forEach(items::addProperty);
            extra.add("items", items);
            feedback("fish_feedback.json", estado, motivo, extra);
            if (motivo == null) mob.avisarAlDueno("\u00a7a[Cobalt]: Pesca terminada: " + capturas + " capturas (" + peces + " peces).");
            else mob.avisarAlDueno("\u00a7e[Cobalt]: Pesca detenida (" + capturas + "/" + cantidad + "): " + motivo + ".");
            return true;
        }
    }

    public static final class TareaCraftear implements Tarea {
        private static final int MAX_TICKS = 1800;   // 90 s
        private static final int TICKS_ENTRE_CRAFTEOS = 4;

        private final String material;
        private final int cantidad;
        private NoxCrafteo.Plan plan = null;
        private int paso = 0;
        private int vecesHechas = 0;
        private int espera = 0;
        private int ticks = 0;
        private int fabricadas = 0;
        private int crafteos = 0;

        public TareaCraftear(String material, int cantidad) {
            this.material = material == null ? "" : material.trim();
            this.cantidad = Math.max(1, Math.min(NoxCrafteo.MAX_UNIDADES, cantidad));
        }

        @Override
        public String nombre() {
            return "craft:" + material + " " + fabricadas + "/" + cantidad;
        }

        @Override
        public void cancelar(CobaltEntity mob) {
            terminar(mob, "cancelada por una orden de detenerse");
        }

        @Override
        public boolean tick(CobaltEntity mob) {
            if (!(mob.level() instanceof ServerLevel nivel)) return true;
            if (++ticks > MAX_TICKS) return terminar(mob, "tiempo agotado");
            if (plan == null) {
                if (material.isEmpty() || NoxMinado.esGenerico(material)) return terminar(mob, "no me dijiste qu\u00e9 fabricar");
                plan = NoxCrafteo.planificar(material, cantidad, mob.getCobaltInventory(), nivel);
                if (!plan.posible()) return terminar(mob, plan.motivo() + (plan.faltan().isEmpty() ? "" : ": " + describirFaltas(plan)));
            }
            if (espera-- > 0) return false;
            if (paso >= plan.pasos().size()) return terminar(mob, null);

            NoxCrafteo.Paso actual = plan.pasos().get(paso);
            SimpleContainer inventario = mob.getCobaltInventory();
            List<ItemStack> salida = NoxCrafteo.ejecutar(actual.receta(), inventario, nivel);
            if (salida == null) return terminar(mob, "el inventario cambi\u00f3 y ya no puedo completar la receta");
            for (int i = 0; i < salida.size(); i++) {
                ItemStack pieza = salida.get(i);
                if (i == 0 && paso == plan.pasos().size() - 1) fabricadas += pieza.getCount(); // el producto FINAL cuenta; lo intermedio (tablones, palos) no
                ItemStack sobrante = inventario.addItem(pieza.copy());
                if (!sobrante.isEmpty()) Block.popResource(nivel, mob.blockPosition(), sobrante); // no cabe: cae al suelo
            }
            inventario.setChanged();
            crafteos++;
            mob.swing(InteractionHand.MAIN_HAND);
            nivel.playSound(null, mob.blockPosition(), net.minecraft.sounds.SoundEvents.UI_STONECUTTER_TAKE_RESULT, net.minecraft.sounds.SoundSource.NEUTRAL, 0.4F, 1.2F);
            if (++vecesHechas >= actual.veces()) {
                paso++;
                vecesHechas = 0;
            }
            espera = TICKS_ENTRE_CRAFTEOS;
            return false;
        }

        private static String describirFaltas(NoxCrafteo.Plan plan) {
            StringBuilder sb = new StringBuilder();
            plan.faltan().forEach((id, n) -> sb.append(sb.length() > 0 ? ", " : "").append(n).append(" x ").append(id));
            return "me faltan " + sb;
        }

        private boolean terminar(CobaltEntity mob, String motivo) {
            String estado = motivo == null ? "success" : (fabricadas > 0 ? "partial" : "failed");
            JsonObject extra = new JsonObject();
            extra.addProperty("crafted", fabricadas);
            extra.addProperty("wanted", cantidad);
            extra.addProperty("steps", crafteos);
            extra.addProperty("material", material);
            if (plan != null && plan.objetivo() != null) extra.addProperty("item", net.minecraft.core.registries.BuiltInRegistries.ITEM.getKey(plan.objetivo()).toString());
            JsonObject faltan = new JsonObject();
            if (plan != null) plan.faltan().forEach(faltan::addProperty);
            extra.add("missing", faltan);
            feedback("craft_feedback.json", estado, motivo, extra);
            String nombre = plan != null && plan.objetivo() != null ? new ItemStack(plan.objetivo()).getHoverName().getString() : material;
            if (motivo == null) mob.avisarAlDueno("\u00a7a[Cobalt]: Fabriqu\u00e9 " + fabricadas + " x " + nombre + ".");
            else mob.avisarAlDueno("\u00a7e[Cobalt]: No pude fabricar " + nombre + ": " + motivo + ".");
            return true;
        }
    }

    public static final class TareaRecoger implements Tarea {
        private static final int MAX_TICKS = 600; // 30 s
        private static final double ALCANCE = 2.0D;

        private final Integer idEntidad;
        private final String material;
        private final double radio;
        private final int edadMinima;
        private final Set<Integer> descartados = new HashSet<>();
        private int ticks = 0;
        private int recogidos = 0;

        public TareaRecoger(Integer idEntidad, String material, int radio) {
            this(idEntidad, material, radio, 0);
        }

        public TareaRecoger(Integer idEntidad, String material, int radio, int edadMinima) {
            this.idEntidad = idEntidad;
            this.material = material == null ? "" : material.trim();
            this.radio = Math.max(2, Math.min(16, radio));
            this.edadMinima = Math.max(0, edadMinima);
        }

        @Override
        public String nombre() {
            return "pickup:" + (idEntidad != null ? "#" + idEntidad : (material.isEmpty() ? "todo" : material)) + " " + recogidos;
        }

        @Override
        public void cancelar(CobaltEntity mob) {
            terminar(mob, "cancelada por una orden de detenerse");
        }

        @Override
        public boolean tick(CobaltEntity mob) {
            if (!(mob.level() instanceof ServerLevel nivel)) return true;
            if (++ticks > MAX_TICKS) return terminar(mob, "tiempo agotado (30 s)");
            net.minecraft.world.entity.item.ItemEntity objetivo = elegir(mob, nivel);
            if (objetivo == null) return terminar(mob, recogidos > 0 ? null : "no hay nada que recoger cerca");
            if (mob.distanceTo(objetivo) > ALCANCE) {
                acercarse(mob, objetivo.getX(), objetivo.getY(), objetivo.getZ(), 1.6D);
                return false;
            }
            mob.getNavigation().stop();
            ItemStack pila = objetivo.getItem();
            SimpleContainer inventario = mob.getCobaltInventory();
            ItemStack resto = inventario.addItem(pila.copy());
            int tomados = pila.getCount() - resto.getCount();
            if (tomados > 0) {
                recogidos += tomados;
                if (resto.isEmpty()) objetivo.discard(); else objetivo.setItem(resto);
                inventario.setChanged();
            } else {
                descartados.add(objetivo.getId()); // no cabe: se sigue con otro y, si no hay hueco para nada, se termina
                if (inventarioSinHuecos(inventario)) return terminar(mob, "inventario lleno");
            }
            return false;
        }

        private net.minecraft.world.entity.item.ItemEntity elegir(CobaltEntity mob, ServerLevel nivel) {
            if (idEntidad != null) {
                net.minecraft.world.entity.Entity concreto = nivel.getEntity(idEntidad);
                if (concreto instanceof net.minecraft.world.entity.item.ItemEntity objeto && objeto.isAlive() && !descartados.contains(objeto.getId())
                        && objeto.distanceTo(mob) <= 48.0F) return objeto;
                return null;
            }
            net.minecraft.world.entity.item.ItemEntity mejor = null;
            double mejorD = Double.MAX_VALUE;
            for (net.minecraft.world.entity.item.ItemEntity e : nivel.getEntitiesOfClass(net.minecraft.world.entity.item.ItemEntity.class,
                    mob.getBoundingBox().inflate(radio), it -> it.isAlive() && it.getAge() >= edadMinima && !descartados.contains(it.getId()))) {
                if (idEntidad != null ? e.getId() != idEntidad
                        : !(material.isEmpty() || NoxMinado.esGenerico(material) || NoxMinado.itemCoincide(e.getItem(), material))) continue;
                double d = e.distanceToSqr(mob);
                if (d < mejorD) {
                    mejorD = d;
                    mejor = e;
                }
            }
            return mejor;
        }

        private boolean terminar(CobaltEntity mob, String motivo) {
            JsonObject extra = new JsonObject();
            extra.addProperty("picked", recogidos);
            feedback("pickup_feedback.json", motivo == null ? "success" : (recogidos > 0 ? "partial" : "failed"), motivo, extra);
            if (recogidos > 0) mob.avisarAlDueno("\u00a7a[Cobalt]: Recogí " + recogidos + " objeto(s)" + (motivo != null ? " (" + motivo + ")" : "") + ".");
            return true;
        }
    }

    public static final class TareaCosechar implements Tarea {
        private static final int MAX_TICKS = 2400;           // 2 minutos
        private static final int MAX_TICKS_POR_PLANTA = 200; // 10 s intentando llegar a una
        private static final double ALCANCE = 3.0D;

        private final int radio;
        private final Set<BlockPos> descartados = new HashSet<>();
        private int ticks = 0;
        private int ticksPlanta = 0;
        private int cosechados = 0;
        private int replantados = 0;
        private BlockPos objetivo = null;

        public TareaCosechar(int radio) {
            this.radio = Math.max(3, Math.min(24, radio));
        }

        @Override
        public String nombre() {
            return "harvest " + cosechados;
        }

        @Override
        public void cancelar(CobaltEntity mob) {
            terminar(mob, "cancelada por una orden de detenerse");
        }

        @Override
        public boolean tick(CobaltEntity mob) {
            if (!(mob.level() instanceof ServerLevel nivel)) return true;
            if (++ticks > MAX_TICKS) return terminar(mob, "tiempo agotado (2 min)");
            if (objetivo == null) {
                objetivo = NoxAgro.buscarMaduros(nivel, mob.blockPosition(), radio, 32).stream().filter(p -> !descartados.contains(p)).findFirst().orElse(null);
                if (objetivo == null) return terminar(mob, cosechados > 0 ? null : "no hay cultivos maduros en " + radio + " bloques");
                ticksPlanta = 0;
            }
            if (++ticksPlanta > MAX_TICKS_POR_PLANTA) { // no se llega a esta planta: se descarta y se sigue con otra
                descartados.add(objetivo);
                objetivo = null;
                return false;
            }
            BlockState estado = nivel.getBlockState(objetivo);
            if (!NoxAgro.esCultivoMaduro(estado)) { // alguien la cosechó, o cambió
                objetivo = null;
                return false;
            }
            Vec3 centro = Vec3.atCenterOf(objetivo);
            if (mob.getEyePosition().distanceTo(centro) > ALCANCE + 1.0D) {
                acercarse(mob, centro.x, centro.y + 0.5D, centro.z, 1.5D);
                return false;
            }
            mob.getNavigation().stop();
            mob.getLookControl().setLookAt(centro.x, centro.y, centro.z);
            mob.swing(InteractionHand.MAIN_HAND);
            cosechar(mob, nivel, estado, objetivo);
            objetivo = null;
            return false;
        }

        private void cosechar(CobaltEntity mob, ServerLevel nivel, BlockState estado, BlockPos pos) {
            Block cultivo = estado.getBlock();
            List<ItemStack> botin = Block.getDrops(estado, nivel, pos, null, mob, ItemStack.EMPTY);
            nivel.destroyBlock(pos, false, mob);
            SimpleContainer inventario = mob.getCobaltInventory();
            for (ItemStack drop : botin) {
                ItemStack sobrante = inventario.addItem(drop.copy());
                if (!sobrante.isEmpty()) Block.popResource(nivel, pos, sobrante);
            }
            cosechados++;
            if (NoxAgro.puedeReplantar(nivel, pos)) {
                for (int i = 0; i < inventario.getContainerSize(); i++) {
                    ItemStack pila = inventario.getItem(i);
                    if (NoxAgro.semillaDe(cultivo, pila)) {
                        nivel.setBlock(pos, cultivo.defaultBlockState(), 3);
                        pila.shrink(1);
                        replantados++;
                        break;
                    }
                }
            }
            inventario.setChanged();
        }

        private boolean terminar(CobaltEntity mob, String motivo) {
            JsonObject extra = new JsonObject();
            extra.addProperty("harvested", cosechados);
            extra.addProperty("replanted", replantados);
            feedback("harvest_feedback.json", motivo == null ? "success" : (cosechados > 0 ? "partial" : "failed"), motivo, extra);
            if (cosechados > 0) {
                mob.avisarAlDueno("\u00a7a[Cobalt]: Cosecha: " + cosechados + " cultivo(s), " + replantados + " replantado(s)" + (motivo != null ? " (" + motivo + ")" : "") + ".");
            } else if (motivo != null) {
                mob.avisarAlDueno("\u00a7e[Cobalt]: No cosech\u00e9 nada: " + motivo + ".");
            }
            return true;
        }
    }

    public static final class TareaTerraformar implements Tarea {
        private static final int MAX_TICKS = 30000;          // 25 minutos (la obra llega a 10000 bloques)
        private static final int MAX_TICKS_POR_BLOQUE = 160; // 8 s intentando llegar a uno
        private static final double ALCANCE = 4.5D;

        private final String etiqueta;
        private final List<BlockPos> cavar;
        private final List<BlockPos> rellenar;
        private final boolean soloFluido;
        private final boolean lava;
        private final int columnasBloqueadas;
        private BlockPos base = null;
        private boolean baseLeida = false;
        private int idxCavar = 0, idxRellenar = 0, ticks = 0, ticksBloque = 0, ticksRomper = -1;
        private int cavados = 0, colocados = 0, omitidos = 0;
        private boolean faltaMaterial = false;
        private boolean enCavado = false;
        private BlockPos objetivo = null;

        public TareaTerraformar(String etiqueta, List<BlockPos> cavar, List<BlockPos> rellenar, boolean soloFluido, boolean lava, int columnasBloqueadas) {
            this.etiqueta = etiqueta;
            this.cavar = cavar;
            this.rellenar = rellenar;
            this.soloFluido = soloFluido;
            this.lava = lava;
            this.columnasBloqueadas = columnasBloqueadas;
        }

        @Override
        public String nombre() {
            return etiqueta + " " + (cavados + colocados) + "/" + (cavar.size() + rellenar.size());
        }

        @Override
        public void cancelar(CobaltEntity mob) {
            terminar(mob, "cancelada por una orden de detenerse");
        }

        @Override
        public boolean tick(CobaltEntity mob) {
            if (!(mob.level() instanceof ServerLevel nivel)) return true;
            if (!baseLeida) {
                base = NoxMinado.leerBase();
                baseLeida = true;
            }
            if (++ticks > MAX_TICKS) return terminar(mob, "tiempo agotado (7,5 min)");

            if (objetivo == null) {
                if (idxCavar < cavar.size()) {
                    objetivo = cavar.get(idxCavar++);
                    enCavado = true;
                } else if (idxRellenar < rellenar.size()) {
                    objetivo = rellenar.get(idxRellenar++);
                    enCavado = false;
                } else {
                    return terminar(mob, faltaMaterial ? "me quedé sin ripio para rellenar" : (omitidos > 0 ? omitidos + " bloque(s) no se pudieron alcanzar o dejaron de ser seguros" : null));
                }
                ticksBloque = 0;
                ticksRomper = -1;
            }
            if (++ticksBloque > MAX_TICKS_POR_BLOQUE) {
                omitidos++;
                objetivo = null;
                return false;
            }
            return enCavado ? cavarBloque(mob, nivel) : rellenarBloque(mob, nivel);
        }

        private boolean cavarBloque(CobaltEntity mob, ServerLevel nivel) {
            BlockState estado = nivel.getBlockState(objetivo);
            if (estado.isAir() || !estado.getFluidState().isEmpty()) { // ya no está
                objetivo = null;
                return false;
            }
            if (!NoxTerreno.cavableSeguroPlaneado(nivel, objetivo, base, NoxMinado.RADIO_BASE_LIMPIEZA)) { // apareció agua al lado, o algo cambió
                omitidos++;
                objetivo = null;
                return false;
            }
            Vec3 centro = Vec3.atCenterOf(objetivo);
            if (mob.getEyePosition().distanceTo(centro) > ALCANCE || !TareaMinar.hayLineaDeVista(mob, nivel, objetivo)) {
                BlockPos acceso = NoxMinado.accesoAire(nivel, objetivo, mob.getX(), mob.getY(), mob.getZ());
                BlockPos destino = acceso != null ? acceso : objetivo;
                acercarse(mob, destino.getX() + 0.5D, destino.getY() + 0.5D, destino.getZ() + 0.5D, 1.5D);
                return false;
            }
            mob.getNavigation().stop();
            mob.getLookControl().setLookAt(centro.x, centro.y, centro.z);
            ItemStack herramienta = TareaMinar.mejorHerramienta(mob, estado);
            if (ticksRomper < 0) {
                float velocidad = herramienta.isEmpty() ? 1.0F : herramienta.getDestroySpeed(estado);
                ticksRomper = NoxMinado.ticksParaRomper(estado.getDestroySpeed(nivel, objetivo), velocidad);
            }
            if (ticksRomper % 6 == 0) mob.swing(InteractionHand.MAIN_HAND);
            if (--ticksRomper > 0) return false;

            List<ItemStack> botin = Block.getDrops(estado, nivel, objetivo, null, mob, herramienta);
            nivel.destroyBlock(objetivo, false, mob);
            SimpleContainer inventario = mob.getCobaltInventory();
            for (ItemStack drop : botin) {
                ItemStack sobrante = inventario.addItem(drop.copy());
                if (!sobrante.isEmpty()) Block.popResource(nivel, objetivo, sobrante);
            }
            if (!herramienta.isEmpty()) herramienta.hurtAndBreak(1, mob, m -> {});
            inventario.setChanged();
            cavados++;
            objetivo = null;
            return false;
        }

        private boolean rellenarBloque(CobaltEntity mob, ServerLevel nivel) {
            BlockState estado = nivel.getBlockState(objetivo);
            boolean libre = soloFluido ? !estado.getFluidState().isEmpty() : (estado.isAir() || estado.canBeReplaced());
            if (!libre || estado.hasBlockEntity()) { // ya está ocupado (o dejó de ser fluido)
                objetivo = null;
                return false;
            }
            SimpleContainer inventario = mob.getCobaltInventory();
            int hueco = elegirRelleno(inventario);
            if (hueco < 0) {
                faltaMaterial = true;
                return terminar(mob, "no tengo ripio (cobblestone, tierra, grava…) para rellenar");
            }
            Vec3 centro = Vec3.atCenterOf(objetivo);
            if (mob.getEyePosition().distanceTo(centro) > ALCANCE) {
                acercarse(mob, centro.x, centro.y + 3.0D, centro.z, 1.5D); // por ENCIMA: nunca dentro de la lava
                return false;
            }
            mob.getNavigation().stop();
            mob.getLookControl().setLookAt(centro.x, centro.y, centro.z);
            mob.swing(InteractionHand.MAIN_HAND);
            BlockItem objeto = (BlockItem) inventario.getItem(hueco).getItem();
            nivel.setBlock(objetivo, objeto.getBlock().defaultBlockState(), 3);
            nivel.playSound(null, objetivo, objeto.getBlock().defaultBlockState().getSoundType().getPlaceSound(), net.minecraft.sounds.SoundSource.BLOCKS, 1.0F, 1.0F);
            inventario.removeItem(hueco, 1);
            colocados++;
            objetivo = null;
            return false;
        }

        private static int elegirRelleno(Container inventario) {
            for (int i = 0; i < inventario.getContainerSize(); i++) {
                ItemStack pila = inventario.getItem(i);
                if (!pila.isEmpty() && pila.getItem() instanceof BlockItem && NoxMinado.esBasura(pila)) return i;
            }
            return -1;
        }

        private boolean terminar(CobaltEntity mob, String motivo) {
            JsonObject extra = new JsonObject();
            extra.addProperty("planned_dig", cavar.size());
            extra.addProperty("dug", cavados);
            extra.addProperty("planned_fill", rellenar.size());
            extra.addProperty("placed", colocados);
            extra.addProperty("skipped", omitidos);
            extra.addProperty("blocked_columns", columnasBloqueadas);
            extra.addProperty("missing_material", faltaMaterial);
            feedback("terraform_feedback.json", motivo == null ? "success" : ((cavados + colocados) > 0 ? "partial" : "failed"), motivo, extra);
            String resumen = "cavé " + cavados + ", coloqué " + colocados + (columnasBloqueadas > 0 ? ", dejé " + columnasBloqueadas + " columna(s) sin tocar (agua, construcciones, base…)" : "");
            if (motivo == null) mob.avisarAlDueno("\u00a7a[Cobalt]: " + etiqueta + " terminado: " + resumen + ".");
            else mob.avisarAlDueno("\u00a7e[Cobalt]: " + etiqueta + " detenido (" + motivo + "): " + resumen + ".");
            return true;
        }
    }

    public static final class TareaHornos implements Tarea {
        private static final int MAX_TICKS = 1800;            // 90 s
        private static final int MAX_TICKS_POR_HORNO = 160;   // 8 s intentando llegar a uno
        private static final int MAX_HORNOS = 12;
        private static final double ALCANCE = 3.5D;

        private final int radio;
        private List<BlockPos> hornos = null;
        private int idx = 0, ticks = 0, ticksHorno = 0;
        private int atendidos = 0, recogidos = 0, combustible = 0, fundibles = 0;

        public TareaHornos(int radio) {
            this.radio = Math.max(3, Math.min(16, radio));
        }

        @Override
        public String nombre() {
            return "tend_furnaces " + atendidos;
        }

        @Override
        public void cancelar(CobaltEntity mob) {
            terminar(mob, "cancelada por una orden de detenerse");
        }

        @Override
        public boolean tick(CobaltEntity mob) {
            if (!(mob.level() instanceof ServerLevel nivel)) return true;
            if (++ticks > MAX_TICKS) return terminar(mob, "tiempo agotado (90 s)");
            if (hornos == null) {
                hornos = buscar(nivel, mob.blockPosition(), radio);
                if (hornos.isEmpty()) return terminar(mob, "no hay hornos en " + radio + " bloques");
            }
            if (idx >= hornos.size()) return terminar(mob, null);
            BlockPos pos = hornos.get(idx);
            if (!(nivel.getBlockEntity(pos) instanceof net.minecraft.world.level.block.entity.AbstractFurnaceBlockEntity horno)) { // ya no está
                idx++;
                ticksHorno = 0;
                return false;
            }
            if (++ticksHorno > MAX_TICKS_POR_HORNO) {
                idx++;
                ticksHorno = 0;
                return false;
            }
            Vec3 centro = Vec3.atCenterOf(pos);
            if (mob.getEyePosition().distanceTo(centro) > ALCANCE) {
                acercarse(mob, centro.x, centro.y + 1.0D, centro.z, 1.5D);
                return false;
            }
            mob.getNavigation().stop();
            mob.getLookControl().setLookAt(centro.x, centro.y, centro.z);
            mob.swing(InteractionHand.MAIN_HAND);
            atender(mob, nivel, horno);
            atendidos++;
            idx++;
            ticksHorno = 0;
            return false;
        }

        private static List<BlockPos> buscar(ServerLevel nivel, BlockPos centro, int radio) {
            List<BlockPos> lista = new ArrayList<>();
            for (BlockPos p : BlockPos.betweenClosed(centro.offset(-radio, -radio, -radio), centro.offset(radio, radio, radio))) {
                if (!nivel.isLoaded(p)) continue;
                if (nivel.getBlockState(p).getBlock() instanceof net.minecraft.world.level.block.AbstractFurnaceBlock) lista.add(p.immutable());
            }
            lista.sort(java.util.Comparator.comparingDouble(p -> p.distSqr(centro)));
            return lista.size() > MAX_HORNOS ? new ArrayList<>(lista.subList(0, MAX_HORNOS)) : lista;
        }

        private static boolean hayReceta(ServerLevel nivel, net.minecraft.world.level.block.entity.AbstractFurnaceBlockEntity horno, ItemStack pila) {
            SimpleContainer muestra = new SimpleContainer(pila.copyWithCount(1));
            var recetas = nivel.getRecipeManager();
            if (horno instanceof net.minecraft.world.level.block.entity.BlastFurnaceBlockEntity) {
                return recetas.getRecipeFor(net.minecraft.world.item.crafting.RecipeType.BLASTING, muestra, nivel).isPresent();
            }
            if (horno instanceof net.minecraft.world.level.block.entity.SmokerBlockEntity) {
                return recetas.getRecipeFor(net.minecraft.world.item.crafting.RecipeType.SMOKING, muestra, nivel).isPresent();
            }
            return recetas.getRecipeFor(net.minecraft.world.item.crafting.RecipeType.SMELTING, muestra, nivel).isPresent();
        }

        private static String ruta(ItemStack pila) {
            return net.minecraft.core.registries.BuiltInRegistries.ITEM.getKey(pila.getItem()).getPath();
        }

        private void atender(CobaltEntity mob, ServerLevel nivel, net.minecraft.world.level.block.entity.AbstractFurnaceBlockEntity horno) {
            SimpleContainer inventario = mob.getCobaltInventory();

            ItemStack salida = horno.getItem(2);
            if (!salida.isEmpty()) {
                ItemStack resto = inventario.addItem(salida.copy());
                int tomados = salida.getCount() - resto.getCount();
                if (tomados > 0) {
                    recogidos += tomados;
                    horno.setItem(2, resto);
                }
            }

            ItemStack enCombustible = horno.getItem(1);
            for (int i = 0; i < inventario.getContainerSize(); i++) {
                ItemStack pila = inventario.getItem(i);
                if (pila.isEmpty() || !NoxServidor.esCombustibleSeguro(ruta(pila))) continue;
                if (!enCombustible.isEmpty() && !ItemStack.isSameItemSameTags(enCombustible, pila)) continue;
                int n = NoxServidor.cantidadAMeter(enCombustible.getCount(), Math.min(NoxServidor.COMBUSTIBLE_OBJETIVO, pila.getMaxStackSize()), pila.getCount());
                if (n <= 0) continue;
                horno.setItem(1, enCombustible.isEmpty() ? pila.copyWithCount(n) : enCombustible.copyWithCount(enCombustible.getCount() + n));
                pila.shrink(n);
                combustible += n;
                break;
            }

            ItemStack enEntrada = horno.getItem(0);
            for (int i = 0; i < inventario.getContainerSize(); i++) {
                ItemStack pila = inventario.getItem(i);
                if (pila.isEmpty() || !NoxServidor.esFundible(ruta(pila)) || !hayReceta(nivel, horno, pila)) continue;
                if (!enEntrada.isEmpty() && !ItemStack.isSameItemSameTags(enEntrada, pila)) continue;
                int n = NoxServidor.cantidadAMeter(enEntrada.getCount(), Math.min(NoxServidor.ENTRADA_MAXIMA, pila.getMaxStackSize()), pila.getCount());
                if (n <= 0) continue;
                horno.setItem(0, enEntrada.isEmpty() ? pila.copyWithCount(n) : enEntrada.copyWithCount(enEntrada.getCount() + n));
                pila.shrink(n);
                fundibles += n;
                break;
            }
            inventario.setChanged();
            horno.setChanged();
        }

        private boolean terminar(CobaltEntity mob, String motivo) {
            JsonObject extra = new JsonObject();
            extra.addProperty("furnaces", atendidos);
            extra.addProperty("collected", recogidos);
            extra.addProperty("fuel_added", combustible);
            extra.addProperty("input_added", fundibles);
            feedback("furnace_feedback.json", motivo == null ? "success" : (atendidos > 0 ? "partial" : "failed"), motivo, extra);
            if (atendidos > 0) {
                mob.avisarAlDueno("\u00a7a[Cobalt]: Atend\u00ed " + atendidos + " horno(s): recogí " + recogidos + ", combustible +" + combustible + ", a fundir +" + fundibles
                        + (motivo != null ? " (" + motivo + ")" : "") + ".");
            } else if (motivo != null) {
                mob.avisarAlDueno("\u00a7e[Cobalt]: No atend\u00ed ning\u00fan horno: " + motivo + ".");
            }
            return true;
        }
    }
}
