package com.example.cobaltbot.network;

import com.example.cobaltbot.entity.CobaltEntity;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.network.chat.Component;
import net.minecraftforge.network.NetworkEvent;

import java.io.File;
import java.io.FileWriter;
import java.util.function.Supplier;

public class NoxChatPacket {
    private final String message;

    public NoxChatPacket(String message) {
        this.message = message;
    }

    public NoxChatPacket(FriendlyByteBuf buf) {
        this.message = buf.readUtf();
    }

    public void toBytes(FriendlyByteBuf buf) {
        buf.writeUtf(this.message);
    }

    // Lógica en el Servidor conectada al servidor local de Python (cerebro.py)
    public boolean handle(Supplier<NetworkEvent.Context> supplier) {
        NetworkEvent.Context context = supplier.get();
        context.enqueueWork(() -> {
            ServerPlayer player = context.getSender();
            if (player != null) {
                ServerLevel serverLevel = player.serverLevel();

                boolean isDeployed = com.example.cobaltbot.util.NoxChip.buscarUno(player.getServer(), player.getUUID()) != null;

                if (!isDeployed) {
                    player.sendSystemMessage(Component.literal("§c[Sistema]: Comandos físicos bloqueados. Cobalt está guardado en el chip."));
                    return;
                }

                try {
                    // la carpeta de intercambio debe existir
                    File dir = com.example.cobaltbot.util.NoxRutas.dir();
                    if (!dir.exists()) {
                        dir.mkdirs();
                    }

                    // Escribir el formato JSON exacto que cerebro.py lee en chat_input.json
                    File file = com.example.cobaltbot.util.NoxRutas.archivo("chat_input.json");
                    String jsonContent = "{\"username\": \"" + player.getName().getString() + "\", \"message\": \"" + message.replace("\"", "\\\"") + "\"}";

                    try (FileWriter writer = new FileWriter(file)) {
                        writer.write(jsonContent);
                    }

                    player.sendSystemMessage(Component.literal("§7[Comando enviado al núcleo de Python...]"));
                } catch (Exception e) {
                    player.sendSystemMessage(Component.literal("§c[Error] No se pudo comunicar con el archivo de cerebro.py"));
                    e.printStackTrace();
                }
            }
        });
        context.setPacketHandled(true);
        return true;
    }
}
