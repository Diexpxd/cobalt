package com.example.cobaltbot.util;

import com.example.cobaltbot.entity.CobaltEntity;
import com.example.cobaltbot.item.NoxSummonerItem;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.Container;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/** Chip de invocación e inventario de Cobalt. */
public final class NoxChip {

    private NoxChip() {}

    public static final String CLAVE_INVENTARIO = "CobaltInventory";

    public static List<CobaltEntity> buscarCobalts(MinecraftServer servidor, UUID dueno) {
        List<CobaltEntity> lista = new ArrayList<>();
        if (servidor == null || dueno == null) return lista;
        for (ServerLevel nivel : servidor.getAllLevels()) {
            for (Entity e : nivel.getAllEntities()) {
                if (e instanceof CobaltEntity c && !c.isRemoved() && dueno.equals(c.getOwnerUUID())) lista.add(c);
            }
        }
        return lista;
    }

    public static CobaltEntity buscarUno(MinecraftServer servidor, UUID dueno) {
        List<CobaltEntity> todos = buscarCobalts(servidor, dueno);
        return todos.isEmpty() ? null : todos.get(0);
    }

    public static ItemStack buscarChip(Player jugador) {
        if (jugador.getMainHandItem().getItem() instanceof NoxSummonerItem) return jugador.getMainHandItem();
        if (jugador.getOffhandItem().getItem() instanceof NoxSummonerItem) return jugador.getOffhandItem();
        for (ItemStack pila : jugador.getInventory().items) {
            if (pila.getItem() instanceof NoxSummonerItem) return pila;
        }
        return ItemStack.EMPTY;
    }

    public static ListTag serializar(Container inventario) {
        ListTag lista = new ListTag();
        for (int i = 0; i < inventario.getContainerSize(); i++) {
            ItemStack pila = inventario.getItem(i);
            if (pila.isEmpty()) continue;
            CompoundTag c = new CompoundTag();
            c.putByte("Slot", (byte) i);
            pila.save(c);
            lista.add(c);
        }
        return lista;
    }

    public static void deserializar(ListTag lista, Container destino) {
        for (int i = 0; i < destino.getContainerSize(); i++) destino.setItem(i, ItemStack.EMPTY);
        if (lista == null) return;
        for (int i = 0; i < lista.size(); i++) {
            CompoundTag c = lista.getCompound(i);
            int casilla = c.getByte("Slot") & 255;
            ItemStack pila = ItemStack.of(c);
            if (casilla < destino.getContainerSize() && !pila.isEmpty()) destino.setItem(casilla, pila);
        }
    }

    public static int huella(Container inventario) {
        int h = 17;
        for (int i = 0; i < inventario.getContainerSize(); i++) {
            ItemStack pila = inventario.getItem(i);
            if (pila.isEmpty()) continue;
            h = 31 * h + i;
            h = 31 * h + pila.getItem().hashCode();
            h = 31 * h + pila.getCount();
            h = 31 * h + (pila.getTag() == null ? 0 : pila.getTag().hashCode());
        }
        return h;
    }

    public static int contarObjetos(Container inventario) {
        int n = 0;
        for (int i = 0; i < inventario.getContainerSize(); i++) n += inventario.getItem(i).getCount();
        return n;
    }

    public static void guardarInventario(ItemStack chip, Container inventario) {
        if (chip.isEmpty()) return;
        chip.getOrCreateTag().put(CLAVE_INVENTARIO, serializar(inventario));
    }

    public static boolean hayInventarioGuardado(ItemStack chip) {
        return !chip.isEmpty() && chip.getTag() != null && chip.getTag().getList(CLAVE_INVENTARIO, Tag.TAG_COMPOUND).size() > 0;
    }

    public static int restaurarInventario(ItemStack chip, Container destino) {
        if (!hayInventarioGuardado(chip)) return 0;
        deserializar(chip.getTag().getList(CLAVE_INVENTARIO, Tag.TAG_COMPOUND), destino);
        return contarObjetos(destino);
    }

    public static void borrarInventarioGuardado(ItemStack chip) {
        if (!chip.isEmpty() && chip.getTag() != null) chip.getTag().remove(CLAVE_INVENTARIO);
    }
}
