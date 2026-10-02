package com.example.cobaltbot.network;

import com.example.cobaltbot.entity.CobaltEntity;
import com.example.cobaltbot.util.NoxChip;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.SimpleContainer;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.network.NetworkEvent;

import java.util.List;
import java.util.UUID;
import java.util.function.Supplier;

/** Botón "Al Chip". Correcciones: (1) Cobalt se busca en TODAS las dimensiones (antes, con Cobalt en otra. */
public class NoxRecallPacket {
    public NoxRecallPacket() {}
    public NoxRecallPacket(FriendlyByteBuf buf) {}
    public void toBytes(FriendlyByteBuf buf) {}

    public boolean handle(Supplier<NetworkEvent.Context> supplier) {
        NetworkEvent.Context context = supplier.get();
        context.enqueueWork(() -> {
            ServerPlayer player = context.getSender();
            if (player == null || player.getServer() == null) return;

            ItemStack chip = NoxChip.buscarChip(player);
            CompoundTag tag = !chip.isEmpty() ? chip.getOrCreateTag() : new CompoundTag();
            String uuidStr = tag.getString("CobaltUUID");

            List<CobaltEntity> todos = NoxChip.buscarCobalts(player.getServer(), player.getUUID());
            if (!uuidStr.isEmpty()) {
                try {
                    UUID uuid = UUID.fromString(uuidStr);
                    for (ServerLevel nivel : player.getServer().getAllLevels()) {
                        Entity e = nivel.getEntity(uuid);
                        if (e instanceof CobaltEntity c && !todos.contains(c)) todos.add(c);
                    }
                } catch (Exception ignored) {}
            }

            int objetos = 0;
            if (!todos.isEmpty()) {
                CobaltEntity principal = todos.get(0);
                for (CobaltEntity c : todos) {
                    if (c.getUUID().toString().equals(uuidStr)) principal = c;
                }
                SimpleContainer inventario = principal.getCobaltInventory();
                for (CobaltEntity extra : todos) {
                    if (extra == principal) continue;
                    for (int i = 0; i < extra.getCobaltInventory().getContainerSize(); i++) {
                        ItemStack resto = inventario.addItem(extra.getCobaltInventory().getItem(i).copy());
                        if (!resto.isEmpty()) player.getInventory().placeItemBackInInventory(resto);
                    }
                }
                objetos = NoxChip.contarObjetos(inventario);
                if (!chip.isEmpty()) {
                    NoxChip.guardarInventario(chip, inventario); // se conserva TODO el inventario dentro del chip
                } else {
                    for (int i = 0; i < inventario.getContainerSize(); i++) { // sin chip no hay dónde guardarlo: se lo queda el jugador
                        if (!inventario.getItem(i).isEmpty()) player.getInventory().placeItemBackInInventory(inventario.getItem(i).copy());
                    }
                }
                for (CobaltEntity c : todos) c.discard();
            }

            if (!chip.isEmpty()) {
                tag.putBoolean("IsDeployed", false);
                tag.remove("CobaltUUID");
                tag.putBoolean("IsDead", false);
                tag.remove("RegenTicksLeft");
            }
            com.example.cobaltbot.util.NoxSensorWriter.escribirEstadoChip(false, 0);

            if (!todos.isEmpty()) {
                player.sendSystemMessage(Component.literal("§b[Sistema]: Cobalt ha sido guardado exitosamente en el chip" + (objetos > 0 ? " (con " + objetos + " objeto(s) de su inventario)." : ".")
                        + (todos.size() > 1 ? " Se retiraron " + (todos.size() - 1) + " copia(s) duplicada(s)." : "")));
            } else {
                player.sendSystemMessage(Component.literal("§e[Sistema]: Sincronización restablecida. Chip liberado a Standby."
                        + (NoxChip.hayInventarioGuardado(chip) ? " El inventario que llevaba Cobalt sigue guardado en el chip." : "")));
            }
        });
        context.setPacketHandled(true);
        return true;
    }
}
