package com.example.cobaltbot.network;

import net.minecraft.network.FriendlyByteBuf;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.network.NetworkEvent;

import java.util.function.Supplier;

public class NoxOpenScreenPacket {
    private final boolean hasSignal;

    public NoxOpenScreenPacket(boolean hasSignal) {
        this.hasSignal = hasSignal;
    }

    public NoxOpenScreenPacket(FriendlyByteBuf buf) {
        this.hasSignal = buf.readBoolean();
    }

    public void toBytes(FriendlyByteBuf buf) {
        buf.writeBoolean(hasSignal);
    }

    public boolean handle(Supplier<NetworkEvent.Context> supplier) {
        NetworkEvent.Context context = supplier.get();
        final boolean hayChip = this.hasSignal;
        context.enqueueWork(() -> DistExecutor.unsafeRunWhenOn(Dist.CLIENT, () -> () -> com.example.cobaltbot.client.NoxClienteHandler.abrirPantallaDeNox(hayChip)));
        context.setPacketHandled(true);
        return true;
    }
}
