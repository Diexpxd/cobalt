package com.example.cobaltbot.util;

import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.tags.FluidTags;
import net.minecraft.util.RandomSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.item.FishingRodItem;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.enchantment.EnchantmentHelper;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.storage.loot.BuiltInLootTables;
import net.minecraft.world.level.storage.loot.LootParams;
import net.minecraft.world.level.storage.loot.parameters.LootContextParamSets;
import net.minecraft.world.level.storage.loot.parameters.LootContextParams;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.common.ToolActions;

import java.util.List;

/** Pesca de Cobalt. */
public final class NoxPesca {
    private NoxPesca() {}

    public static final int ESPERA_MIN = 100, ESPERA_MAX = 300;

    public static boolean esCana(ItemStack pila) {
        return !pila.isEmpty() && (pila.getItem() instanceof FishingRodItem || pila.canPerformAction(ToolActions.FISHING_ROD_CAST));
    }

    public static boolean esAguaPescable(BlockGetter nivel, BlockPos pos) {
        return nivel.getFluidState(pos).is(FluidTags.WATER) && nivel.getBlockState(pos.above()).isAir();
    }

    public static BlockPos buscarAgua(BlockGetter nivel, BlockPos centro, int radio) {
        BlockPos mejor = null;
        double mejorDistancia = Double.MAX_VALUE;
        for (int dx = -radio; dx <= radio; dx++) {
            for (int dz = -radio; dz <= radio; dz++) {
                if ((double) dx * dx + dz * dz > (double) radio * radio) continue;
                for (int dy = -6; dy <= 6; dy++) {
                    BlockPos pos = centro.offset(dx, dy, dz);
                    double distancia = pos.distSqr(centro);
                    if (distancia >= mejorDistancia || !esAguaPescable(nivel, pos)) continue;
                    mejor = pos.immutable();
                    mejorDistancia = distancia;
                }
            }
        }
        return mejor;
    }

    public static int esperaTicks(RandomSource azar, int cebo) {
        int min = Math.max(20, ESPERA_MIN - 25 * cebo);
        int max = Math.max(min + 20, ESPERA_MAX - 75 * cebo);
        return min + azar.nextInt(max - min + 1);
    }

    public static int cebo(ItemStack cana) {
        return EnchantmentHelper.getFishingSpeedBonus(cana);
    }

    public static List<ItemStack> capturar(ServerLevel nivel, BlockPos agua, ItemStack cana, Entity pescador) {
        LootParams parametros = new LootParams.Builder(nivel)
                .withParameter(LootContextParams.ORIGIN, Vec3.atCenterOf(agua))
                .withParameter(LootContextParams.TOOL, cana)
                .withParameter(LootContextParams.THIS_ENTITY, pescador)
                .withLuck(EnchantmentHelper.getFishingLuckBonus(cana))
                .create(LootContextParamSets.FISHING);
        return nivel.getServer().getLootData().getLootTable(BuiltInLootTables.FISHING).getRandomItems(parametros);
    }
}
