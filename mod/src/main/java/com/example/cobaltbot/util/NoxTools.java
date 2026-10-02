package com.example.cobaltbot.util;

import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.item.AxeItem;
import net.minecraft.world.item.HoeItem;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.PickaxeItem;
import net.minecraft.world.item.ShovelItem;
import net.minecraft.world.item.SwordItem;
import net.minecraftforge.common.ToolActions;

/** Clasificación ÚNICA de herramientas. */
public final class NoxTools {

    private NoxTools() {}

    public static String tipoDeHerramienta(ItemStack pila) {
        if (pila == null || pila.isEmpty()) return null;
        Item item = pila.getItem();

        if (item instanceof PickaxeItem) return "pickaxe";
        if (item instanceof AxeItem) return "axe";
        if (item instanceof SwordItem) return "sword";
        if (item instanceof ShovelItem) return "shovel";
        if (item instanceof HoeItem) return "hoe";

        String ruta = BuiltInRegistries.ITEM.getKey(item).getPath();
        if (ruta.endsWith("_pickaxe")) return "pickaxe";
        if (ruta.endsWith("_axe")) return "axe";
        if (ruta.endsWith("_sword")) return "sword";
        if (ruta.endsWith("_shovel")) return "shovel";
        if (ruta.endsWith("_hoe")) return "hoe";

        if (pila.canPerformAction(ToolActions.PICKAXE_DIG)) return "pickaxe";
        if (pila.canPerformAction(ToolActions.AXE_DIG)) return "axe";
        if (pila.canPerformAction(ToolActions.SHOVEL_DIG)) return "shovel";
        if (pila.canPerformAction(ToolActions.HOE_DIG)) return "hoe";
        if (pila.canPerformAction(ToolActions.SWORD_DIG)) return "sword";
        return null;
    }

    public static boolean esHerramienta(ItemStack pila, String tipo) {
        return tipo != null && tipo.equals(tipoDeHerramienta(pila));
    }

    public static final double UMBRAL_FRAGIL_PCT = 5.0D;

    public static double durabilidadRestantePct(ItemStack pila) {
        if (pila.isEmpty() || !pila.isDamageableItem()) return 100.0D;
        int max = pila.getMaxDamage();
        if (max <= 0) return 100.0D;
        return 100.0D * (max - pila.getDamageValue()) / max;
    }

    public static boolean esFragil(ItemStack pila) {
        return !pila.isEmpty() && pila.isDamageableItem() && durabilidadRestantePct(pila) < UMBRAL_FRAGIL_PCT;
    }
}
