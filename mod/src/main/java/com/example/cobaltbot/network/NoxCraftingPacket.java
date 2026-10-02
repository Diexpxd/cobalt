package com.example.cobaltbot.network;

import com.example.cobaltbot.entity.CobaltEntity;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.SimpleMenuProvider;
import net.minecraft.world.inventory.ContainerLevelAccess;
import net.minecraft.world.inventory.CraftingMenu;
import net.minecraft.world.phys.AABB;
import net.minecraftforge.network.NetworkEvent;

import java.util.List;
import java.util.function.Supplier;

public class NoxCraftingPacket {

    public NoxCraftingPacket() {}

    public NoxCraftingPacket(FriendlyByteBuf buf) {}

    public void encode(FriendlyByteBuf buf) {}

    public boolean handle(Supplier<NetworkEvent.Context> supplier) {
        NetworkEvent.Context context = supplier.get();
        context.enqueueWork(() -> {
            ServerPlayer player = context.getSender();
            if (player != null && player.level() instanceof net.minecraft.server.level.ServerLevel serverLevel) {

                AABB searchBox = player.getBoundingBox().inflate(32.0D);
                List<CobaltEntity> colabtsCercanos = serverLevel.getEntitiesOfClass(CobaltEntity.class, searchBox);

                if (!colabtsCercanos.isEmpty()) {
                    CobaltEntity cobalt = colabtsCercanos.get(0);

                    if (player.distanceToSqr(cobalt) <= 256.0D) {
                        player.openMenu(new SimpleMenuProvider((id, inventory, p) ->
                                new CraftingMenu(id, inventory, ContainerLevelAccess.NULL),
                                Component.literal("🛠️ Mesa de Crafteo Remota")
                        ));
                    } else {
                        player.sendSystemMessage(Component.literal("§c[Sistema]: Estás demasiado lejos de Cobalt (>16 bloques). Enlace inalámbrico perdido."));
                    }
                } else {
                    player.sendSystemMessage(Component.literal("§c[Sistema]: No se detecta a Cobalt desplegado en este mundo."));
                }
            }
        });
        context.setPacketHandled(true);
        return true;
    }
}
