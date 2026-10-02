package com.example.cobaltbot.util;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.material.Fluids;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/** SEGUIR ENTRE DIMENSIONES: reglas PURAS (probadas sin Minecraft en tools/pruebas/PruebasDimension.java) para. */
public final class NoxDimension {

    private NoxDimension() {}

    public static final double DIST_MAX_SEGUIR = 40.0D;
    public static final int TICKS_MAX_SIN_DUENO = 60;
    /** Radio horizontal de la búsqueda de sitio. */
    public static final int RADIO_BUSQUEDA = 6;

    /** Posición de llegada (centro del bloque donde van los pies) y si debe volar (no hay suelo firme debajo). */
    public record Llegada(double x, double y, double z, boolean vuelo) {}

    public static boolean debeSeguir(boolean sigueAlDueno, boolean ocupado, boolean congelado, int ticksSinDueno, double distancia) {
        return sigueAlDueno && !ocupado && !congelado && ticksSinDueno >= 0 && ticksSinDueno <= TICKS_MAX_SIN_DUENO
                && !Double.isNaN(distancia) && distancia <= DIST_MAX_SEGUIR;
    }

    static boolean esPortal(BlockState e) {
        Block b = e.getBlock();
        return b == Blocks.NETHER_PORTAL || b == Blocks.END_PORTAL || b == Blocks.END_GATEWAY;
    }

    static boolean esPeligro(BlockState e) {
        Block b = e.getBlock();
        return e.getFluidState().getType().isSame(Fluids.LAVA) || b == Blocks.FIRE || b == Blocks.SOUL_FIRE || b == Blocks.MAGMA_BLOCK || b == Blocks.CACTUS
                || b == Blocks.SWEET_BERRY_BUSH || b == Blocks.WITHER_ROSE || b == Blocks.CAMPFIRE || b == Blocks.SOUL_CAMPFIRE || b == Blocks.COBWEB
                || b == Blocks.POWDER_SNOW;
    }

    static boolean cabe(BlockGetter n, BlockPos p) {
        for (BlockPos c : new BlockPos[]{p, p.above()}) {
            BlockState e = n.getBlockState(c);
            if (!e.getCollisionShape(n, c).isEmpty() || !e.getFluidState().isEmpty() || esPeligro(e) || esPortal(e)) return false;
        }
        return true;
    }

    static boolean cercaDePortal(BlockGetter n, BlockPos p) {
        for (int dx = -1; dx <= 1; dx++) {
            for (int dz = -1; dz <= 1; dz++) {
                for (int dy = -1; dy <= 2; dy++) {
                    if (esPortal(n.getBlockState(p.offset(dx, dy, dz)))) return true;
                }
            }
        }
        return false;
    }

    static boolean haySuelo(BlockGetter n, BlockPos p) {
        BlockPos abajo = p.below();
        BlockState e = n.getBlockState(abajo);
        return e.isFaceSturdy(n, abajo, Direction.UP) && e.getFluidState().isEmpty() && !esPeligro(e);
    }

    public static Llegada buscarLlegada(BlockGetter n, BlockPos centro) {
        int yMin = n.getMinBuildHeight() + 1, yMax = n.getMaxBuildHeight() - 3;
        List<BlockPos> libres = new ArrayList<>();
        for (int dx = -RADIO_BUSQUEDA; dx <= RADIO_BUSQUEDA; dx++) {
            for (int dz = -RADIO_BUSQUEDA; dz <= RADIO_BUSQUEDA; dz++) {
                for (int dy = -3; dy <= 3; dy++) {
                    BlockPos p = centro.offset(dx, dy, dz);
                    if (p.getY() < yMin || p.getY() > yMax) continue;
                    if (cabe(n, p) && !cercaDePortal(n, p)) libres.add(p.immutable());
                }
            }
        }
        libres.sort(Comparator.comparingDouble((BlockPos p) -> p.distSqr(centro)));
        BlockPos elegido = null;
        boolean vuelo = false;
        for (BlockPos p : libres) { // suelo firme lejos del jugador
            if (p.distSqr(centro) >= 4.0D && haySuelo(n, p)) { elegido = p; break; }
        }
        if (elegido == null) {
            for (BlockPos p : libres) { // suelo firme, aunque sea pegado al jugador
                if (haySuelo(n, p)) { elegido = p; break; }
            }
        }
        if (elegido == null && !libres.isEmpty()) { // sin suelo: aire libre, en vuelo
            elegido = libres.get(0);
            for (BlockPos p : libres) {
                if (p.distSqr(centro) >= 4.0D) { elegido = p; break; }
            }
            vuelo = true;
        }
        return elegido == null ? null : new Llegada(elegido.getX() + 0.5D, elegido.getY(), elegido.getZ() + 0.5D, vuelo);
    }
}
