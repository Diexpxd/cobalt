package com.example.cobaltbot.util;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.block.LeavesBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.material.FluidState;
import net.minecraft.world.level.material.Fluids;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.function.Predicate;

/** Reglas PURAS para leer el relieve, aplanar terreno y rellenar fluidos, probadas sin Minecraft en tools/pruebas/PruebasTerreno.java. */
public final class NoxTerreno {

    private NoxTerreno() {}

    // Tipos de superficie (códigos que Python lee en terrain_map.json)
    public static final int SUELO = 0, AGUA = 1, LAVA = 2, VACIO = 3, OBSTACULO = 4, DESCONOCIDO = 9;

    public static final int MAX_COLUMNAS_ESCANEO = 4096;
    public static final int MAX_VOLUMEN_BLOQUES = 16384;
    public static final int MAX_BLOQUES_OBRA = 10000;
    public static final int MAX_CORTE = 12;
    public static final int MAX_RELLENO = 12;

    private static boolean esFluido(FluidState f, boolean lava) {
        return !f.isEmpty() && f.getType().isSame(lava ? Fluids.LAVA : Fluids.WATER);
    }

    private static boolean esFollaje(BlockState e) {
        return e.getBlock() instanceof LeavesBlock || (!e.blocksMotion() && e.getFluidState().isEmpty());
    }

    public static int[] superficie(BlockGetter nivel, int x, int z, int yMax, int yMin) {
        for (int y = yMax; y >= yMin; y--) {
            BlockState e = nivel.getBlockState(new BlockPos(x, y, z));
            if (e.isAir() || esFollaje(e)) continue;
            FluidState f = e.getFluidState();
            if (!f.isEmpty()) return new int[]{y, esFluido(f, true) ? LAVA : AGUA};
            boolean natural = !e.hasBlockEntity() && (NoxMinado.esLimpiable(e) || NoxMinado.esTerrenoExcavable(e) || NoxArboles.esTroncoDeArbol(nivel, new BlockPos(x, y, z)));
            return new int[]{y, natural ? SUELO : OBSTACULO};
        }
        return new int[]{yMin - 1, VACIO};
    }

    public static String idDe(BlockState e) {
        var clave = BuiltInRegistries.BLOCK.getKey(e.getBlock());
        return clave == null ? "desconocido" : clave.toString();
    }

    public static boolean esMenaOculta(BlockState e) {
        String id = idDe(e);
        String ruta = id.substring(id.indexOf(':') + 1);
        return ruta.endsWith("_ore") || ruta.equals("ancient_debris");
    }

    public static boolean estaExpuesto(BlockGetter nivel, BlockPos pos) {
        for (Direction d : Direction.values()) {
            if (!nivel.getBlockState(pos.relative(d)).canOcclude()) return true;
        }
        return false;
    }

    public static boolean debeRevelar(BlockGetter nivel, BlockPos pos, BlockState e) {
        return !esMenaOculta(e) || estaExpuesto(nivel, pos);
    }

    public static boolean cavableSeguro(BlockGetter nivel, BlockPos pos, BlockPos base, double radioBase) {
        return cavable(nivel, pos, base, radioBase, false);
    }

    public static boolean cavableSeguroPlaneado(BlockGetter nivel, BlockPos pos, BlockPos base, double radioBase) {
        return cavable(nivel, pos, base, radioBase, true);
    }

    private static boolean cavable(BlockGetter nivel, BlockPos pos, BlockPos base, double radioBase, boolean planeado) {
        BlockState e = nivel.getBlockState(pos);
        if (e.isAir() || e.hasBlockEntity() || NoxMinado.protegido(pos, base, radioBase)) return false;
        boolean arbol = planeado ? NoxArboles.esTronco(e) : NoxArboles.esTroncoDeArbol(nivel, pos);
        if (!NoxMinado.esLimpiable(e) && !NoxMinado.esTerrenoExcavable(e) && !arbol) return false;
        for (Direction d : Direction.values()) {
            if (!nivel.getBlockState(pos.relative(d)).getFluidState().isEmpty()) return false;
        }
        return true;
    }

    /** Resultado del plan de aplanado: qué cavar (de arriba abajo), qué rellenar (de abajo arriba) y cuántas. */
    public record PlanAplanado(List<BlockPos> cavar, List<BlockPos> rellenar, int columnasBloqueadas, int columnas, boolean truncado) {}

    public static PlanAplanado planAplanado(BlockGetter nivel, int x1, int z1, int x2, int z2, int yObj, BlockPos base, double radioBase,
                                            Predicate<BlockPos> cargado, int max) {
        int x0 = Math.min(x1, x2), xf = Math.max(x1, x2), z0 = Math.min(z1, z2), zf = Math.max(z1, z2);
        List<BlockPos> cavar = new ArrayList<>();
        List<BlockPos> rellenar = new ArrayList<>();
        int bloqueadas = 0, columnas = 0;
        boolean truncado = false;
        for (int x = x0; x <= xf; x++) {
            for (int z = z0; z <= zf; z++) {
                columnas++;
                BlockPos ref = new BlockPos(x, yObj, z);
                if ((cargado != null && !cargado.test(ref)) || NoxMinado.protegido(ref, base, radioBase)) {
                    bloqueadas++;
                    continue;
                }
                int[] sup = superficie(nivel, x, z, yObj + MAX_CORTE + 1, yObj - MAX_RELLENO - 1); // +1: una colina más alta que MAX_CORTE se detecta (y se deja)
                int ySup = sup[0];
                if (sup[1] == AGUA || sup[1] == LAVA || sup[1] == VACIO) { // lagos y precipicios NO se aplanan
                    bloqueadas++;
                    continue;
                }
                if (ySup > yObj) {
                    boolean limpio = true;
                    List<BlockPos> columna = new ArrayList<>();
                    for (int y = ySup; y > yObj && limpio; y--) {
                        BlockPos p = new BlockPos(x, y, z);
                        BlockState e = nivel.getBlockState(p);
                        if (e.isAir() || esFollaje(e)) continue; // hueco o plantas: nada que cavar
                        limpio = cavableSeguro(nivel, p, base, radioBase);
                        columna.add(p);
                    }
                    if (!limpio || ySup - yObj > MAX_CORTE) {
                        bloqueadas++;
                        continue;
                    }
                    columna.sort(Comparator.comparingInt((BlockPos p) -> p.getY()).reversed());
                    if (cavar.size() + columna.size() > max) {
                        truncado = true;
                        break;
                    }
                    cavar.addAll(columna);
                } else if (ySup < yObj) {
                    if (yObj - ySup > MAX_RELLENO) {
                        bloqueadas++;
                        continue;
                    }
                    if (rellenar.size() + (yObj - ySup) > max) {
                        truncado = true;
                        break;
                    }
                    for (int y = ySup + 1; y <= yObj; y++) rellenar.add(new BlockPos(x, y, z));
                }
            }
            if (truncado) break;
        }
        rellenar.sort(Comparator.comparingInt(BlockPos::getY)); // primero las capas de abajo
        return new PlanAplanado(cavar, rellenar, bloqueadas, columnas, truncado);
    }

    public static List<BlockPos> buscarFluido(BlockGetter nivel, BlockPos centro, int radio, boolean lava, int max) {
        List<BlockPos> lista = new ArrayList<>();
        double radio2 = (double) radio * radio;
        for (int dx = -radio; dx <= radio; dx++) {
            for (int dy = -radio; dy <= radio; dy++) {
                for (int dz = -radio; dz <= radio; dz++) {
                    if ((double) dx * dx + dy * dy + dz * dz > radio2) continue;
                    BlockPos p = centro.offset(dx, dy, dz);
                    if (esFluido(nivel.getBlockState(p).getFluidState(), lava)) lista.add(p.immutable());
                }
            }
        }
        lista.sort(Comparator.comparingInt((BlockPos p) -> p.getY()).reversed().thenComparingDouble(p -> p.distSqr(centro)));
        return lista.size() > max ? new ArrayList<>(lista.subList(0, max)) : lista;
    }

    public static boolean tocaFluido(BlockGetter nivel, BlockPos pos, boolean lava) {
        for (Direction d : Direction.values()) {
            if (esFluido(nivel.getBlockState(pos.relative(d)).getFluidState(), lava)) return true;
        }
        return false;
    }
}
