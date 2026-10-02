package com.example.cobaltbot.util;

import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.Property;

import java.util.Optional;

/** H5 (schematics): colocación de bloques con ESTADO ("facing=east,half=bottom") y el ítem que de verdad hace falta para colocarlos. */
public final class NoxBloques {
    public static final int MAX_LARGO_PROPIEDADES = 300;
    public static final int MAX_PROPIEDADES = 24;

    private NoxBloques() {}

    /** Resultado de aplicar propiedades: el estado final y cuántas se aplicaron o se ignoraron. */
    public record Resultado(BlockState estado, int aplicadas, int ignoradas) {}

    public static Resultado aplicarPropiedades(BlockState base, String propiedades) {
        if (base == null || propiedades == null || propiedades.isBlank()) return new Resultado(base, 0, 0);
        if (propiedades.length() > MAX_LARGO_PROPIEDADES) return new Resultado(base, 0, 1); // entrada absurda: se descarta entera
        BlockState estado = base;
        int aplicadas = 0, ignoradas = 0, vistas = 0;
        for (String par : propiedades.split(",")) {
            if (par.isBlank()) continue;
            if (++vistas > MAX_PROPIEDADES) { ignoradas++; break; }
            int i = par.indexOf('=');
            if (i <= 0 || i == par.length() - 1) { ignoradas++; continue; }
            Property<?> propiedad = base.getBlock().getStateDefinition().getProperty(par.substring(0, i).trim());
            BlockState nuevo = propiedad == null ? null : conValor(estado, propiedad, par.substring(i + 1).trim());
            if (nuevo == null) { ignoradas++; continue; }
            estado = nuevo;
            aplicadas++;
        }
        return new Resultado(estado, aplicadas, ignoradas);
    }

    private static <T extends Comparable<T>> BlockState conValor(BlockState estado, Property<T> propiedad, String valor) {
        Optional<T> v = propiedad.getValue(valor);
        return v.isPresent() ? estado.setValue(propiedad, v.get()) : null;
    }

    public static Block bloqueDe(String id) {
        try {
            Block b = BuiltInRegistries.BLOCK.get(new ResourceLocation(id));
            return b == Blocks.AIR ? null : b;
        } catch (Exception e) { // ResourceLocation inválido
            return null;
        }
    }

    public static Item itemDe(Block bloque) {
        if (bloque == null) return null;
        Item item = bloque.asItem();
        return item == Items.AIR ? null : item;
    }

    public static String idDe(Item item) {
        return item == null ? "" : BuiltInRegistries.ITEM.getKey(item).toString();
    }
}
