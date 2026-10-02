package com.example.cobaltbot.util;

import net.minecraft.core.BlockPos;
import net.minecraft.tags.BlockTags;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.LeavesBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraftforge.common.Tags;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/** ¿Este tronco es de un ÁRBOL o de una construcción? Talar (y despejar/aplanar) puede llevarse por delante los. */
public final class NoxArboles {
    private NoxArboles() {}

    public static final int MAX_TRONCOS = 160;
    private static final int RADIO_HOJAS = 1;

    public static boolean esTronco(BlockState estado) {
        return estado.is(BlockTags.LOGS);
    }

    public static boolean esHojaNatural(BlockState estado) {
        if (!estado.is(BlockTags.LEAVES)) return false;
        return !estado.hasProperty(LeavesBlock.PERSISTENT) || !estado.getValue(LeavesBlock.PERSISTENT);
    }

    private static boolean sueloNatural(BlockState estado) {
        return estado.is(BlockTags.DIRT) || estado.is(BlockTags.SAND) || estado.is(Tags.Blocks.SAND) || estado.is(Tags.Blocks.GRAVEL)
                || estado.is(Blocks.MUD) || estado.is(Blocks.MANGROVE_ROOTS) || estado.is(Blocks.MUDDY_MANGROVE_ROOTS) || estado.is(BlockTags.NYLIUM);
    }

    public static List<BlockPos> arbol(BlockGetter nivel, BlockPos pos) {
        if (!esTronco(nivel.getBlockState(pos))) return List.of();
        Set<BlockPos> visitados = new HashSet<>();
        ArrayDeque<BlockPos> cola = new ArrayDeque<>();
        visitados.add(pos.immutable());
        cola.add(pos.immutable());
        while (!cola.isEmpty()) {
            BlockPos p = cola.poll();
            for (int dx = -1; dx <= 1; dx++) {
                for (int dy = -1; dy <= 1; dy++) {
                    for (int dz = -1; dz <= 1; dz++) {
                        if (dx == 0 && dy == 0 && dz == 0) continue;
                        BlockPos q = p.offset(dx, dy, dz);
                        if (visitados.contains(q) || !esTronco(nivel.getBlockState(q))) continue;
                        if (visitados.size() >= MAX_TRONCOS) return List.of(); // demasiado grande: una construcción
                        visitados.add(q.immutable());
                        cola.add(q.immutable());
                    }
                }
            }
        }
        boolean hojas = false;
        BlockPos masBajo = null;
        for (BlockPos t : visitados) {
            if (masBajo == null || t.getY() < masBajo.getY()) masBajo = t;
            if (!hojas) hojas = hayHojasNaturales(nivel, t);
        }
        if (!hojas || masBajo == null || !sueloNatural(nivel.getBlockState(masBajo.below()))) return List.of();
        List<BlockPos> lista = new ArrayList<>(visitados);
        BlockPos origen = pos;
        lista.sort(Comparator.<BlockPos>comparingInt(BlockPos::getY).thenComparingDouble(p -> p.distSqr(origen)));
        return lista;
    }

    private static boolean hayHojasNaturales(BlockGetter nivel, BlockPos tronco) {
        for (int dx = -RADIO_HOJAS; dx <= RADIO_HOJAS; dx++) {
            for (int dy = -RADIO_HOJAS; dy <= RADIO_HOJAS; dy++) {
                for (int dz = -RADIO_HOJAS; dz <= RADIO_HOJAS; dz++) {
                    if (esHojaNatural(nivel.getBlockState(tronco.offset(dx, dy, dz)))) return true;
                }
            }
        }
        return false;
    }

    public static boolean esTroncoDeArbol(BlockGetter nivel, BlockPos pos) {
        return !arbol(nivel, pos).isEmpty();
    }

    public static boolean lavaPegada(BlockGetter nivel, BlockPos pos) {
        for (net.minecraft.core.Direction cara : net.minecraft.core.Direction.values()) {
            if (nivel.getFluidState(pos.relative(cara)).is(net.minecraft.tags.FluidTags.LAVA)) return true;
        }
        return false;
    }
}
