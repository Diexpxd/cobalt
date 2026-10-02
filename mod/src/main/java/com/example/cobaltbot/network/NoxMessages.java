package com.example.cobaltbot.network;

import com.example.cobaltbot.CobaltMod;
import net.minecraft.resources.ResourceLocation;
import net.minecraftforge.network.NetworkRegistry;
import net.minecraftforge.network.simple.SimpleChannel;
import net.minecraftforge.network.NetworkDirection;

public class NoxMessages {

    private static SimpleChannel CHANNEL;

    private static int packetId = 0;
    private static int id() {
        return packetId++;
    }

    public static void register() {
        SimpleChannel net = NetworkRegistry.ChannelBuilder
                .named(new ResourceLocation(CobaltMod.MOD_ID, "messages"))
                .networkProtocolVersion(() -> "1.0")
                .clientAcceptedVersions(s -> true)
                .serverAcceptedVersions(s -> true)
                .simpleChannel();

        CHANNEL = net;

        // REGISTRO DEL PAQUETE DE CHAT DE NOX
        net.messageBuilder(NoxChatPacket.class, id(), NetworkDirection.PLAY_TO_SERVER)
                .decoder(NoxChatPacket::new)
                .encoder(NoxChatPacket::toBytes)
                .consumerNetworkThread(NoxChatPacket::handle)
                .add();

        net.messageBuilder(NoxTeleportPacket.class, id(), NetworkDirection.PLAY_TO_SERVER)
                .decoder(NoxTeleportPacket::new)
                .encoder(NoxTeleportPacket::toBytes)
                .consumerNetworkThread(NoxTeleportPacket::handle)
                .add();

        net.messageBuilder(NoxRecallPacket.class, id(), NetworkDirection.PLAY_TO_SERVER)
                .decoder(NoxRecallPacket::new)
                .encoder(NoxRecallPacket::toBytes)
                .consumerNetworkThread(NoxRecallPacket::handle)
                .add();

        net.messageBuilder(NoxCraftingPacket.class, id(), NetworkDirection.PLAY_TO_SERVER)
                .decoder(NoxCraftingPacket::new)
                .encoder(NoxCraftingPacket::encode)
                .consumerNetworkThread(NoxCraftingPacket::handle)
                .add();

        net.messageBuilder(NoxOpenScreenPacket.class, id(), NetworkDirection.PLAY_TO_CLIENT)
                .decoder(NoxOpenScreenPacket::new)
                .encoder(NoxOpenScreenPacket::toBytes)
                .consumerNetworkThread(NoxOpenScreenPacket::handle)
                .add();

        // (Justo debajo de tus otros registros en NoxMessages.java)
        net.messageBuilder(NoxInventoryPacket.class, id(), NetworkDirection.PLAY_TO_SERVER)
                .decoder(NoxInventoryPacket::new)
                .encoder(NoxInventoryPacket::toBytes)
                .consumerMainThread(NoxInventoryPacket::handle)
                .add();

    }

    public static <MSG> void sendToServer(MSG message) {
        CHANNEL.sendToServer(message);
    }

    public static <MSG> void sendToPlayer(MSG message, net.minecraft.server.level.ServerPlayer player) {
        CHANNEL.send(net.minecraftforge.network.PacketDistributor.PLAYER.with(() -> player), message);
    }
}
