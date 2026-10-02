package com.example.cobaltbot.network;

import com.example.cobaltbot.entity.CobaltEntity;
import com.example.cobaltbot.item.NoxSummonerItem;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.network.NetworkEvent;

import java.util.function.Supplier;

public class NoxTeleportPacket {
    public NoxTeleportPacket() {}

    public NoxTeleportPacket(FriendlyByteBuf buf) {}

    public void toBytes(FriendlyByteBuf buf) {}

    public boolean handle(Supplier<NetworkEvent.Context> supplier) {
        NetworkEvent.Context context = supplier.get();
        context.enqueueWork(() -> {
            ServerPlayer player = context.getSender();
            if (player != null) {
                // Buscar el NoxSummonerItem en el inventario del jugador
                ItemStack summonerStack = ItemStack.EMPTY;
                for (ItemStack stack : player.getInventory().items) {
                    if (stack.getItem() instanceof NoxSummonerItem) {
                        summonerStack = stack;
                        break;
                    }
                }

                if (summonerStack.isEmpty() && player.getOffhandItem().getItem() instanceof NoxSummonerItem) {
                    summonerStack = player.getOffhandItem();
                }

                if (!summonerStack.isEmpty()) {
                    CompoundTag tag = summonerStack.getOrCreateTag();
                    long lastUse = tag.getLong("TeleportCooldown");
                    long currentTime = player.level().getGameTime();
                    long cooldownTicks = 72000L; // 1 hora en ticks (20 ticks * 60 seg * 60 min)

                    if (currentTime - lastUse < cooldownTicks) {
                        long remainingSeconds = (cooldownTicks - (currentTime - lastUse)) / 20L;
                        long minutes = remainingSeconds / 60;
                        long seconds = remainingSeconds % 60;
                        player.sendSystemMessage(Component.literal("§c[Sistema]: El rescate está en cooldown. Tiempo restante: " + minutes + "m " + seconds + "s."));
                        return;
                    }

                    // Buscar y teletransportar a Cobalt
                    boolean found = false;
                    CobaltEntity nox = com.example.cobaltbot.util.NoxChip.buscarUno(player.getServer(), player.getUUID()); // en cualquier dimensión
                    if (nox != null) {
                        if (nox.level() == player.level()) {
                            nox.teleportTo(player.getX(), player.getY(), player.getZ());
                            nox.setDeltaMovement(0, 0, 0);
                            found = true;
                        } else {
                            found = nox.cruzarDimension(player); // está en otra dimensión: lo trae a un sitio seguro cerca de ti
                        }
                    }

                    if (found) {
                        tag.putLong("TeleportCooldown", currentTime);
                        player.sendSystemMessage(Component.literal("§e[Sistema]: ¡Rescate exitoso! Cobalt ha sido teletransportado a tu posición."));
                    } else {
                        player.sendSystemMessage(Component.literal("§c[Sistema]: Cobalt no está activo en el mundo. Invócalo primero."));
                    }
                }
            }
        });
        context.setPacketHandled(true);
        return true;
    }
}
