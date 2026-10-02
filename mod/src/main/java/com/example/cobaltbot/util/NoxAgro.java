package com.example.cobaltbot.util;

import net.minecraft.core.BlockPos;
import net.minecraft.world.item.BlockItem;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.CropBlock;
import net.minecraft.world.level.block.state.BlockState;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/** Reglas PURAS de qué cultivos se cosechan y cómo se replantan, probadas sin Minecraft en tools/pruebas/PruebasAgro.java. */
public final class NoxAgro {

    private NoxAgro() {}

    public static boolean esCultivoMaduro(BlockState estado) {
        return estado.getBlock() instanceof CropBlock cultivo && cultivo.isMaxAge(estado);
    }

    public static boolean semillaDe(Block cultivo, ItemStack pila) {
        return !pila.isEmpty() && pila.getItem() instanceof BlockItem objeto && objeto.getBlock() == cultivo;
    }

    public static boolean puedeReplantar(BlockGetter nivel, BlockPos pos) {
        return nivel.getBlockState(pos).isAir() && nivel.getBlockState(pos.below()).is(Blocks.FARMLAND);
    }

    public static List<BlockPos> buscarMaduros(BlockGetter nivel, BlockPos centro, int radio, int max) {
        List<BlockPos> lista = new ArrayList<>();
        double radio2 = (double) radio * radio;
        for (int dx = -radio; dx <= radio; dx++) {
            for (int dy = -radio; dy <= radio; dy++) {
                for (int dz = -radio; dz <= radio; dz++) {
                    if ((double) dx * dx + dy * dy + dz * dz > radio2) continue;
                    BlockPos pos = centro.offset(dx, dy, dz);
                    if (esCultivoMaduro(nivel.getBlockState(pos))) lista.add(pos.immutable());
                }
            }
        }
        lista.sort(Comparator.comparingDouble(p -> p.distSqr(centro)));
        return lista.size() > max ? new ArrayList<>(lista.subList(0, max)) : lista;
    }
}
