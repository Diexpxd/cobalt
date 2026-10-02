package com.example.cobaltbot.network;

import com.example.cobaltbot.entity.CobaltEntity;
import com.example.cobaltbot.util.NoxChip;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.SimpleContainer;
import net.minecraft.world.SimpleMenuProvider;
import net.minecraft.world.inventory.ChestMenu;
import net.minecraft.world.inventory.MenuType;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.network.NetworkEvent;

import java.util.function.Supplier;

public class NoxInventoryPacket {

    public NoxInventoryPacket() {
    }

    public NoxInventoryPacket(FriendlyByteBuf buf) {
    }

    public void toBytes(FriendlyByteBuf buf) {
    }

    public boolean handle(Supplier<NetworkEvent.Context> supplier) {
        NetworkEvent.Context context = supplier.get();
        context.enqueueWork(() -> {
            ServerPlayer player = context.getSender();
            if (player == null) return;

            // Cobalt desplegado (en cualquier dimensión): se abre su inventario remoto
            CobaltEntity nox = NoxChip.buscarUno(player.getServer(), player.getUUID());
            if (nox != null) {
                nox.openRemoteInventory(player);
                return;
            }

            ItemStack chip = NoxChip.buscarChip(player);
            if (chip.isEmpty()) {
                player.sendSystemMessage(Component.literal("§e[Sistema]: Necesitas el chip de invocación para ver el inventario de Cobalt."));
                return;
            }
            SimpleContainer guardado = new SimpleContainer(36);
            if (NoxChip.restaurarInventario(chip, guardado) == 0) {
                player.sendSystemMessage(Component.literal("§e[Sistema]: Cobalt está guardado en el chip y no lleva ningún objeto."));
                return;
            }
            guardado.addListener(c -> NoxChip.guardarInventario(chip, guardado));
            player.openMenu(new SimpleMenuProvider(
                    (containerId, playerInventory, p) -> new ChestMenu(MenuType.GENERIC_9x4, containerId, playerInventory, guardado, 4),
                    Component.literal("§bInventario de Cobalt (guardado en el chip)")));
        });
        context.setPacketHandled(true);
        return true;
    }
}
