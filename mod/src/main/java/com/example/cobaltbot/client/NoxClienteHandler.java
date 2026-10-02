package com.example.cobaltbot.client;

import net.minecraft.client.Minecraft;

/** Lo que solo puede hacer un CLIENTE (abrir pantallas). */
public final class NoxClienteHandler {
    private NoxClienteHandler() {}

    public static void abrirPantallaDeNox(boolean hayChip) {
        if (hayChip) {
            Minecraft.getInstance().setScreen(new com.example.cobaltbot.client.gui.NoxInteractScreen());
        } else {
            Minecraft.getInstance().setScreen(new com.example.cobaltbot.client.gui.NoxNoSignalScreen());
        }
    }
}
