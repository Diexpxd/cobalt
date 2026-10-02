package com.example.cobaltbot.util;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.tags.TagKey;
import net.minecraft.tags.BlockTags;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.EmptyBlockGetter;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.BushBlock;
import net.minecraft.world.level.block.CropBlock;
import net.minecraft.world.level.block.FallingBlock;
import net.minecraft.world.level.block.LeavesBlock;
import net.minecraft.world.level.block.StemBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraftforge.common.Tags;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.PriorityQueue;
import java.util.Set;
import java.util.function.Predicate;

/** Reglas PURAS de qué se puede tocar del mundo y cómo buscarlo, para probarlas sin abrir Minecraft (tools/pruebas/PruebasMinado.java). */
public final class NoxMinado {

    private NoxMinado() {}

    public static final double RADIO_BASE_PROTEGIDA = 24.0D;

    private static String normalizar(String material) {
        return material == null ? "" : material.trim().toLowerCase(Locale.ROOT);
    }

    public static boolean esGenerico(String material) {
        String m = normalizar(material);
        return m.isEmpty() || m.equals("cualquiera") || m.equals("any") || m.equals("ore") || m.equals("ores")
                || m.equals("mena") || m.equals("menas") || m.equals("minerales");
    }

    private static boolean esMaderaGenerica(String m) {
        return m.equals("log") || m.equals("logs") || m.equals("wood") || m.equals("tronco") || m.equals("troncos") || m.equals("madera");
    }

    public static boolean esObjetivo(BlockState estado, String material) {
        String m = normalizar(material);
        ResourceLocation etiqueta = etiquetaDe(m);
        if (etiqueta != null) return estado.is(TagKey.create(Registries.BLOCK, etiqueta));
        var clave = BuiltInRegistries.BLOCK.getKey(estado.getBlock());
        String ruta = clave.getPath();
        if (esGenerico(m)) return ruta.endsWith("_ore") || ruta.equals("ancient_debris") || estado.is(Tags.Blocks.ORES);
        if (esMaderaGenerica(m)) return ruta.endsWith("_log") || ruta.endsWith("_stem") || estado.is(BlockTags.LOGS);
        if (m.contains(":")) return clave.toString().equals(m);
        return ruta.equals(m) || ruta.endsWith("_" + m);
    }

    public static ResourceLocation etiquetaDe(String material) {
        String m = normalizar(material);
        if (m.startsWith("#")) m = m.substring(1);
        else if (!(m.startsWith("forge:") || m.startsWith("c:"))) return null;
        return ResourceLocation.tryParse(m);
    }

    public static boolean itemCoincide(ItemStack pila, String material) {
        if (material != null && material.indexOf(',') >= 0) {
            for (String parte : material.split(",")) if (!parte.isBlank() && itemCoincide(pila, parte.trim())) return true;
            return false;
        }
        String m = normalizar(material);
        ResourceLocation etiqueta = etiquetaDe(m);
        if (etiqueta != null) return !pila.isEmpty() && pila.is(TagKey.create(Registries.ITEM, etiqueta));
        if (pila.isEmpty() || m.isEmpty() || esGenerico(m)) return false;
        var clave = BuiltInRegistries.ITEM.getKey(pila.getItem());
        String ruta = clave.getPath();
        if (esMaderaGenerica(m)) return ruta.endsWith("_log") || ruta.endsWith("_stem");
        if (m.contains(":")) return clave.toString().equals(m);
        return ruta.equals(m) || ruta.endsWith("_" + m);
    }

    public static final int MAX_EXCAVACION = 32;

    private static final Set<Block> TERRENO_EXCAVABLE = Set.of(
            Blocks.STONE, Blocks.GRANITE, Blocks.DIORITE, Blocks.ANDESITE, Blocks.DEEPSLATE, Blocks.TUFF, Blocks.CALCITE,
            Blocks.DIRT, Blocks.COARSE_DIRT, Blocks.ROOTED_DIRT, Blocks.PODZOL, Blocks.GRASS_BLOCK, Blocks.CLAY, Blocks.MYCELIUM,
            Blocks.NETHERRACK, Blocks.BASALT, Blocks.SMOOTH_BASALT, Blocks.BLACKSTONE, Blocks.MOSS_BLOCK, Blocks.DRIPSTONE_BLOCK);

    public static boolean esTerrenoExcavable(BlockState estado) {
        Block bloque = estado.getBlock();
        if (bloque instanceof FallingBlock) return false;
        if (TERRENO_EXCAVABLE.contains(bloque)) return true;
        String ruta = BuiltInRegistries.BLOCK.getKey(bloque).getPath();
        return ruta.endsWith("_ore") || ruta.equals("ancient_debris")
                || estado.is(BlockTags.BASE_STONE_OVERWORLD) || estado.is(BlockTags.BASE_STONE_NETHER);
    }

    public static boolean excavableSeguro(BlockGetter nivel, BlockPos pos, BlockPos base, double radioBase) {
        BlockState estado = nivel.getBlockState(pos);
        if (!esMinable(estado) || !esTerrenoExcavable(estado) || protegido(pos, base, radioBase)) return false;
        for (Direction cara : Direction.values()) {
            if (!nivel.getBlockState(pos.relative(cara)).getFluidState().isEmpty()) return false;
        }
        return !(nivel.getBlockState(pos.above()).getBlock() instanceof FallingBlock);
    }

    private static int costeCelda(BlockGetter nivel, BlockPos pos, BlockPos base, double radioBase) {
        if (nivel.getBlockState(pos).isAir()) return 0;
        return excavableSeguro(nivel, pos, base, radioBase) ? 1 : -1;
    }

    private static int costeMemo(Map<Long, Integer> memo, BlockGetter nivel, BlockPos pos, BlockPos base, double radioBase) {
        return memo.computeIfAbsent(pos.asLong(), k -> costeCelda(nivel, pos, base, radioBase));
    }

    private record NodoTunel(BlockPos pos, int coste) {}

    /** Plan de túnel: los bloques a picar EN ORDEN (el último es la veta) y el coste proyectado, que es exactamente. */
    public record PlanTunel(List<BlockPos> celdas, int costeProyectado) {}

    private static int costeTransicion(Map<Long, Integer> memo, BlockGetter nivel, BlockPos desde, BlockPos hasta, BlockPos base, double radioBase) {
        int total = 0;
        for (BlockPos celda : new BlockPos[]{hasta, hasta.above()}) {
            if (celda.equals(desde) || celda.equals(desde.above())) continue; // ya pertenece al hitbox de origen: no se cuenta dos veces
            int c = costeMemo(memo, nivel, celda, base, radioBase);
            if (c < 0) return -1;
            total += c;
        }
        return total;
    }

    public static List<BlockPos> planificarTunel(BlockGetter nivel, BlockPos inicio, Predicate<BlockState> objetivo, BlockPos base,
                                                 double radioBase, int radio, int maxExcavar, Predicate<BlockPos> excluido) {
        return planificarTunelConCoste(nivel, inicio, objetivo, base, radioBase, radio, maxExcavar, excluido).celdas();
    }

    public static PlanTunel planificarTunelConCoste(BlockGetter nivel, BlockPos inicio, Predicate<BlockState> objetivo, BlockPos base,
                                                    double radioBase, int radio, int maxExcavar, Predicate<BlockPos> excluido) {
        PlanTunel vacio = new PlanTunel(new ArrayList<>(), 0);
        BlockPos ini = inicio.immutable();
        Map<BlockPos, Integer> dist = new HashMap<>();
        Map<BlockPos, BlockPos> padre = new HashMap<>();
        Map<Long, Integer> memo = new HashMap<>(); // coste por celda: cada una se evalúa una sola vez
        PriorityQueue<NodoTunel> abiertos = new PriorityQueue<>(Comparator.comparingInt(NodoTunel::coste));
        dist.put(ini, 0);
        abiertos.add(new NodoTunel(ini, 0));
        while (!abiertos.isEmpty()) {
            NodoTunel actual = abiertos.poll();
            if (actual.coste() > dist.getOrDefault(actual.pos(), Integer.MAX_VALUE)) continue; // entrada vieja
            for (Direction cara : Direction.values()) {
                BlockPos vecino = actual.pos().relative(cara);
                if (Math.abs(vecino.getX() - ini.getX()) > radio || Math.abs(vecino.getY() - ini.getY()) > radio
                        || Math.abs(vecino.getZ() - ini.getZ()) > radio) continue;
                int paso = costeTransicion(memo, nivel, actual.pos(), vecino, base, radioBase);
                if (paso < 0) continue;
                int nuevo = actual.coste() + paso;
                if (nuevo > maxExcavar || nuevo >= dist.getOrDefault(vecino, Integer.MAX_VALUE)) continue;
                dist.put(vecino, nuevo);
                padre.put(vecino, actual.pos());
                abiertos.add(new NodoTunel(vecino.immutable(), nuevo));
            }
        }

        BlockPos mejorVeta = null;
        BlockPos mejorNodo = null;
        int mejorCoste = Integer.MAX_VALUE;
        double mejorDistancia = Double.MAX_VALUE;
        for (int dx = -radio; dx <= radio; dx++) {
            for (int dy = -radio; dy <= radio; dy++) {
                for (int dz = -radio; dz <= radio; dz++) {
                    BlockPos veta = ini.offset(dx, dy, dz);
                    BlockState estado = nivel.getBlockState(veta);
                    if (!objetivo.test(estado) || (excluido != null && excluido.test(veta))) continue;
                    if (!excavableSeguro(nivel, veta, base, radioBase)) continue;
                    for (Direction cara : Direction.values()) {
                        BlockPos celda = veta.relative(cara);
                        for (BlockPos nodo : new BlockPos[]{celda, celda.below()}) {
                            Integer d = dist.get(nodo);
                            if (d == null) continue;
                            int coste = d + (veta.equals(nodo) || veta.equals(nodo.above()) ? 0 : 1);
                            double distancia = veta.distSqr(ini);
                            if (coste < mejorCoste || (coste == mejorCoste && distancia < mejorDistancia)) {
                                mejorCoste = coste;
                                mejorDistancia = distancia;
                                mejorVeta = veta;
                                mejorNodo = nodo;
                            }
                        }
                    }
                }
            }
        }
        if (mejorVeta == null || mejorCoste > maxExcavar) return vacio;

        List<BlockPos> camino = new ArrayList<>();
        for (BlockPos n = mejorNodo; n != null && !n.equals(ini); n = padre.get(n)) camino.add(0, n);
        LinkedHashSet<BlockPos> aPicar = new LinkedHashSet<>();
        for (BlockPos nodo : camino) {
            for (BlockPos celda : new BlockPos[]{nodo, nodo.above()}) {
                if (!nivel.getBlockState(celda).isAir()) aPicar.add(celda.immutable());
            }
        }
        aPicar.remove(mejorVeta); // la veta va siempre la última
        List<BlockPos> plan = new ArrayList<>(aPicar);
        plan.add(mejorVeta.immutable());
        return new PlanTunel(plan, mejorCoste);
    }

    private static final String[] PALABRAS_MENA = {"iron", "gold", "diamond", "coal", "copper", "redstone", "lapis", "emerald", "quartz", "debris", "netherite"};

    public static boolean esMena(String material) {
        String m = normalizar(material);
        if (esGenerico(m)) return true;
        if (esMaderaGenerica(m) || m.endsWith("_log") || m.endsWith("_block") || m.endsWith("planks")) return false;
        if (m.endsWith("_ore")) return true;
        for (String palabra : PALABRAS_MENA) {
            if (m.contains(palabra)) return true;
        }
        return false;
    }

    public static int alturaIdeal(String material, boolean nether) {
        if (nether) return 15;
        String m = normalizar(material);
        if (m.contains("diamond") || m.contains("redstone")) return -58;
        if (m.contains("gold")) return -16;
        if (m.contains("lapis")) return 0;
        if (m.contains("iron")) return 16;
        if (m.contains("coal")) return 45;
        if (m.contains("copper")) return 48;
        return 0;
    }

    private static final Set<String> BASURA = Set.of("cobblestone", "cobbled_deepslate", "dirt", "coarse_dirt", "rooted_dirt", "granite", "diorite",
            "andesite", "tuff", "netherrack", "gravel", "blackstone", "basalt", "calcite", "dripstone_block", "stone", "deepslate", "moss_block");

    public static boolean esBasura(ItemStack pila) {
        return !pila.isEmpty() && BASURA.contains(BuiltInRegistries.ITEM.getKey(pila.getItem()).getPath());
    }

    public static final int CONSERVAR_BASURA = 64;

    public static boolean debeConservar(ItemStack botin, int yaTengo, boolean esLoPedido) {
        if (esLoPedido || !esBasura(botin)) return true;
        return yaTengo < CONSERVAR_BASURA;
    }

    /** Tramo de túnel/escalera: bloques a picar (en orden), dónde queda el frente, hacia dónde va y cuántos pasos da. */
    public record Segmento(List<BlockPos> celdas, BlockPos frente, Direction dir, int nodos) {}

    private static int costeVetable(BlockGetter nivel, BlockPos pos, BlockPos base, double radioBase, Predicate<BlockPos> vetado) {
        if (vetado != null && vetado.test(pos)) return -1;
        return costeCelda(nivel, pos, base, radioBase);
    }

    public static Segmento planificarSegmento(BlockGetter nivel, BlockPos frente, Direction dir, boolean bajar, int yMinimo, int nodosMax,
                                              BlockPos base, double radioBase, Predicate<BlockPos> cargado, Predicate<BlockPos> vetado) {
        LinkedHashSet<BlockPos> celdas = new LinkedHashSet<>();
        BlockPos actual = frente.immutable();
        boolean tocaBajar = false;
        int nodos = 0;
        while (nodos < nodosMax) {
            BlockPos siguiente = (bajar && tocaBajar) ? actual.below() : actual.relative(dir);
            if (siguiente.getY() < yMinimo && bajar && tocaBajar) break;
            if (cargado != null && (!cargado.test(siguiente) || !cargado.test(siguiente.above()))) break;
            int pies = costeVetable(nivel, siguiente, base, radioBase, vetado);
            int cabeza = pies < 0 ? -1 : costeVetable(nivel, siguiente.above(), base, radioBase, vetado);
            if (pies < 0 || cabeza < 0) break;
            if (pies == 1) celdas.add(siguiente.immutable());
            if (cabeza == 1) celdas.add(siguiente.above().immutable());
            actual = siguiente.immutable();
            nodos++;
            if (bajar) tocaBajar = !tocaBajar;
        }
        return new Segmento(new ArrayList<>(celdas), actual, dir, nodos);
    }

    public static Segmento elegirSegmento(BlockGetter nivel, BlockPos frente, Direction previa, boolean bajar, int yMinimo, int nodosMax,
                                          BlockPos base, double radioBase, Predicate<BlockPos> cargado, Predicate<BlockPos> vetado) {
        Direction[] orden = previa != null
                ? new Direction[]{previa, previa.getClockWise(), previa.getCounterClockWise()}
                : new Direction[]{Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST};
        Segmento mejor = null;
        for (Direction d : orden) {
            Segmento seg = planificarSegmento(nivel, frente, d, bajar, yMinimo, nodosMax, base, radioBase, cargado, vetado);
            if (seg.nodos() == 0 || seg.celdas().isEmpty()) continue;
            if (mejor == null || seg.nodos() > mejor.nodos()) mejor = seg; // a igualdad gana el primero (seguir recto)
        }
        return mejor;
    }

    public static final double RADIO_BASE_LIMPIEZA = 32.0D;
    public static final int MAX_BLOQUES_LIMPIEZA = 2000;
    public static final long MAX_VOLUMEN_CAJA = 20000L;

    public static long volumenCaja(int x1, int y1, int z1, int x2, int y2, int z2) {
        return ((long) Math.abs(x2 - x1) + 1L) * ((long) Math.abs(y2 - y1) + 1L) * ((long) Math.abs(z2 - z1) + 1L);
    }

    public static boolean limpiableSeguro(BlockGetter nivel, BlockPos pos) {
        if (!esLimpiable(nivel.getBlockState(pos)) && !NoxArboles.esTroncoDeArbol(nivel, pos)) return false;
        return sinLiquidoPegado(nivel, pos);
    }

    public static boolean limpiableSeguroPlaneado(BlockGetter nivel, BlockPos pos) {
        BlockState estado = nivel.getBlockState(pos);
        if (!esLimpiable(estado) && !NoxArboles.esTronco(estado)) return false;
        return sinLiquidoPegado(nivel, pos);
    }

    public static boolean sinLiquidoPegado(BlockGetter nivel, BlockPos pos) {
        for (Direction cara : Direction.values()) {
            if (!nivel.getBlockState(pos.relative(cara)).getFluidState().isEmpty()) return false;
        }
        return true;
    }

    public static List<BlockPos> bloquesALimpiar(BlockGetter nivel, BlockPos a, BlockPos b, BlockPos base, double radioBase, int max) {
        List<BlockPos> lista = new ArrayList<>();
        if (volumenCaja(a.getX(), a.getY(), a.getZ(), b.getX(), b.getY(), b.getZ()) > MAX_VOLUMEN_CAJA) return lista;
        int x0 = Math.min(a.getX(), b.getX()), x1 = Math.max(a.getX(), b.getX());
        int y0 = Math.min(a.getY(), b.getY()), y1 = Math.max(a.getY(), b.getY());
        int z0 = Math.min(a.getZ(), b.getZ()), z1 = Math.max(a.getZ(), b.getZ());
        for (int y = y1; y >= y0; y--) {
            for (int x = x0; x <= x1; x++) {
                for (int z = z0; z <= z1; z++) {
                    BlockPos pos = new BlockPos(x, y, z);
                    if (protegido(pos, base, radioBase) || !limpiableSeguro(nivel, pos)) continue;
                    lista.add(pos);
                    if (lista.size() >= max) return lista;
                }
            }
        }
        return lista;
    }

    public static boolean esAlmacen(String rutaBloque) {
        if (rutaBloque == null) return false;
        String r = rutaBloque.toLowerCase(Locale.ROOT);
        if (r.contains("ender_chest")) return false;
        return r.equals("chest") || r.equals("barrel") || r.equals("crate") || r.endsWith("shulker_box")
                || r.endsWith("_chest") || r.endsWith("_barrel") || r.endsWith("_crate");
    }

    public static boolean esMineralDeFundicion(ItemStack pila, String mineral) {
        String m = normalizar(mineral);
        if (pila.isEmpty() || m.isEmpty()) return false;
        String ruta = BuiltInRegistries.ITEM.getKey(pila.getItem()).getPath();
        return ruta.equals("raw_" + m) || ruta.equals(m + "_ore") || ruta.endsWith("_" + m + "_ore");
    }

    public static boolean esMinable(BlockState estado) {
        if (estado.isAir() || !estado.getFluidState().isEmpty() || estado.hasBlockEntity()) return false;
        return estado.getDestroySpeed(EmptyBlockGetter.INSTANCE, BlockPos.ZERO) >= 0.0F;
    }

    public static boolean expuestoYSeguro(BlockGetter nivel, BlockPos pos) {
        boolean expuesto = false;
        for (Direction cara : Direction.values()) {
            BlockState vecino = nivel.getBlockState(pos.relative(cara));
            if (!vecino.getFluidState().isEmpty()) return false;
            if (vecino.isAir() || !vecino.blocksMotion()) expuesto = true;
        }
        return expuesto;
    }

    public static boolean protegido(BlockPos pos, BlockPos base, double radio) {
        return base != null && pos.distSqr(base) <= radio * radio;
    }

    private static final Set<Block> TERRENO_NATURAL = Set.of(
            Blocks.DIRT, Blocks.GRASS_BLOCK, Blocks.COARSE_DIRT, Blocks.PODZOL, Blocks.MYCELIUM, Blocks.ROOTED_DIRT,
            Blocks.SAND, Blocks.RED_SAND, Blocks.GRAVEL, Blocks.CLAY, Blocks.SNOW_BLOCK,
            Blocks.STONE, Blocks.GRANITE, Blocks.DIORITE, Blocks.ANDESITE, Blocks.DEEPSLATE, Blocks.TUFF);

    public static boolean esLimpiable(BlockState estado) {
        if (estado.isAir() || !estado.getFluidState().isEmpty() || estado.hasBlockEntity()) return false;
        Block bloque = estado.getBlock();
        if (bloque instanceof CropBlock || bloque instanceof StemBlock) return false;
        return TERRENO_NATURAL.contains(bloque) || bloque instanceof LeavesBlock || bloque instanceof BushBlock || estado.canBeReplaced();
    }

    public static int ticksParaRomper(float dureza, float velocidad) {
        int ticks = (int) Math.ceil(Math.max(0.0F, dureza) * 30.0F / Math.max(1.0F, velocidad));
        return Math.max(4, Math.min(200, ticks));
    }

    public static List<BlockPos> buscarBloques(BlockGetter nivel, BlockPos centro, int radio, Predicate<BlockState> objetivo,
                                               BlockPos base, double radioBase, int max, Predicate<BlockPos> excluido) {
        List<BlockPos> encontrados = new ArrayList<>();
        double radio2 = (double) radio * radio;
        for (int dx = -radio; dx <= radio; dx++) {
            for (int dy = -radio; dy <= radio; dy++) {
                for (int dz = -radio; dz <= radio; dz++) {
                    if ((double) dx * dx + dy * dy + dz * dz > radio2) continue;
                    BlockPos pos = centro.offset(dx, dy, dz);
                    BlockState estado = nivel.getBlockState(pos);
                    if (!objetivo.test(estado) || !esMinable(estado)) continue;
                    if (protegido(pos, base, radioBase) || (excluido != null && excluido.test(pos))) continue;
                    if (!expuestoYSeguro(nivel, pos)) continue;
                    encontrados.add(pos.immutable());
                }
            }
        }
        encontrados.sort(Comparator.comparingDouble(p -> p.distSqr(centro)));
        return encontrados.size() > max ? new ArrayList<>(encontrados.subList(0, max)) : encontrados;
    }

    public static BlockPos accesoAire(BlockGetter nivel, BlockPos objetivo, double desdeX, double desdeY, double desdeZ) {
        BlockPos mejor = null;
        double mejorDistancia = Double.MAX_VALUE;
        for (Direction cara : Direction.values()) {
            BlockPos vecino = objetivo.relative(cara);
            if (!nivel.getBlockState(vecino).isAir()) continue;
            double dx = vecino.getX() + 0.5D - desdeX, dy = vecino.getY() + 0.5D - desdeY, dz = vecino.getZ() + 0.5D - desdeZ;
            double distancia = dx * dx + dy * dy + dz * dz;
            if (distancia < mejorDistancia) {
                mejor = vecino;
                mejorDistancia = distancia;
            }
        }
        return mejor;
    }

    public static BlockPos leerBase() {
        try {
            File archivo = com.example.cobaltbot.util.NoxRutas.archivo("waypoints.json");
            if (!archivo.exists()) return null;
            JsonObject raiz = JsonParser.parseString(Files.readString(archivo.toPath(), StandardCharsets.UTF_8)).getAsJsonObject();
            return coordenadasDe(raiz.get("base"));
        } catch (Exception e) {
            return null;
        }
    }

    public static BlockPos coordenadasDe(com.google.gson.JsonElement elemento) {
        if (elemento == null || !elemento.isJsonObject()) return null;
        JsonObject o = elemento.getAsJsonObject();
        if (!o.has("x") || !o.has("y") || !o.has("z")) return null;
        try {
            return new BlockPos((int) Math.floor(o.get("x").getAsDouble()), (int) Math.floor(o.get("y").getAsDouble()),
                    (int) Math.floor(o.get("z").getAsDouble()));
        } catch (Exception e) {
            return null;
        }
    }
}
