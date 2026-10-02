package com.example.cobaltbot.client.gui;

import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;

public class NoxNoSignalScreen extends Screen {

    public NoxNoSignalScreen() {
        super(Component.literal("Señal Débil"));
    }

    @Override
    protected void init() {
        super.init();
    }

    @Override
    public void render(GuiGraphics guiGraphics, int mouseX, int mouseY, float partialTick) {
        // Fondo semi-transparente estilo terminal táctica
        this.renderBackground(guiGraphics);

        int centerX = this.width / 2;
        int centerY = this.height / 2;

        // Panel de advertencia visual
        guiGraphics.fill(centerX - 130, centerY - 50, centerX + 130, centerY + 50, 0xC0101010); // Fondo oscuro
        guiGraphics.renderOutline(centerX - 130, centerY - 50, 260, 100, 0xFFFF5555); // Borde rojo alerta

        // Textos de estado
        guiGraphics.drawCenteredString(this.font, "§c⚠ SEÑAL DE ENLACE DÉBIL ⚠", centerX, centerY - 30, 0xFF5555);
        guiGraphics.drawCenteredString(this.font, "§eDebes tener el chip de invocación", centerX, centerY - 10, 0xFFFF55);
        guiGraphics.drawCenteredString(this.font, "§7en tu inventario para interactuar.", centerX, centerY + 10, 0xAAAAAA);

        super.render(guiGraphics, mouseX, mouseY, partialTick);
    }

    @Override
    public boolean keyPressed(int keyCode, int scanCode, int modifiers) {
        if (com.example.cobaltbot.event.ClientEvents.OPEN_NOX_KEY.matches(keyCode, scanCode)) {
            this.onClose();
            return true;
        }
        return super.keyPressed(keyCode, scanCode, modifiers);
    }

    @Override
    public boolean isPauseScreen() {
        return false; // Permite ver el juego de fondo sin pausarlo
    }
}
