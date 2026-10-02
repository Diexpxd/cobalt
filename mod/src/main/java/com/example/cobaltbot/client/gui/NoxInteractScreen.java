package com.example.cobaltbot.client.gui;

import com.example.cobaltbot.util.NoxScreenshotUtil;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.components.EditBox;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.util.FormattedCharSequence;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import org.lwjgl.glfw.GLFW;

import net.minecraft.client.Minecraft;
import java.io.File;
import java.io.BufferedReader;
import java.io.FileReader;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;

public class NoxInteractScreen extends Screen {

    private int selectedTab = 0; // 0: Chat, 1: Diagnóstico, 2: Control
    private boolean confirmClear = false;
    private int scrollOffset = 0; // Desplazamiento del chat

    private EditBox inputField;
    private Button sendButton;
    private Button tabChatButton;
    private Button tabDiagButton;
    private Button tabControlButton;

    private Button teleportButton;
    private Button recallButton;
    private Button clearChatButton;
    private Button craftingButton;
    private Button inventoryButton;

    public NoxInteractScreen() {
        super(Component.literal("Terminal Táctica: Nox"));
    }

    public static File getChatFileForCurrentWorld() {
        Minecraft mc = Minecraft.getInstance();
        String worldName = "default_world";
        if (mc.getSingleplayerServer() != null) {
            worldName = mc.getSingleplayerServer().getWorldData().getLevelName();
        } else if (mc.getCurrentServer() != null) {
            worldName = mc.getCurrentServer().ip.replaceAll("[^a-zA-Z0-9]", "_");
        }
        File dir = new File(com.example.cobaltbot.util.NoxRutas.dir(), "worlds_" + worldName);
        if (!dir.exists()) dir.mkdirs();
        return new File(dir, "chat_history.txt");
    }

    @Override
    protected void init() {
        super.init();

        int panelWidth = 440;
        int panelHeight = 240;
        int startX = (this.width - panelWidth) / 2;
        int startY = (this.height - panelHeight) / 2;

        this.tabChatButton = Button.builder(Component.literal("💬 Chat"), b -> {
            this.selectedTab = 0;
            this.rebuildWidgets();
        }).bounds(startX + 130, startY + 10, 90, 20).build();
        this.addRenderableWidget(this.tabChatButton);

        this.tabDiagButton = Button.builder(Component.literal("📊 Diagnóstico"), b -> {
            this.selectedTab = 1;
            this.rebuildWidgets();
        }).bounds(startX + 225, startY + 10, 90, 20).build();
        this.addRenderableWidget(this.tabDiagButton);

        this.tabControlButton = Button.builder(Component.literal("⚙️ Control"), b -> {
            this.selectedTab = 2;
            this.rebuildWidgets();
        }).bounds(startX + 320, startY + 10, 90, 20).build();
        this.addRenderableWidget(this.tabControlButton);

        int sidebarX = startX + 10;
        int sidebarY = startY + 50;

        this.teleportButton = Button.builder(Component.literal("§c🚨 Rescate (TP)"), b -> {
            com.example.cobaltbot.network.NoxMessages.sendToServer(new com.example.cobaltbot.network.NoxTeleportPacket());
            this.minecraft.setScreen(null);
        }).bounds(sidebarX, sidebarY, 110, 20).build();
        this.addRenderableWidget(this.teleportButton);

        this.recallButton = Button.builder(Component.literal("§b💾 Al Chip"), b -> {
            com.example.cobaltbot.network.NoxMessages.sendToServer(new com.example.cobaltbot.network.NoxRecallPacket());
            this.minecraft.setScreen(null);
        }).bounds(sidebarX, sidebarY + 25, 110, 20).build();
        this.addRenderableWidget(this.recallButton);

        String clearLabel = this.confirmClear ? "§c¿Seguro?" : "🧹 Limpiar Chat";
        this.clearChatButton = Button.builder(Component.literal(clearLabel), b -> {
            if (!this.confirmClear) {
                this.confirmClear = true;
                this.rebuildWidgets();
            } else {
                limpiarHistorialDisco();
                this.confirmClear = false;
                this.scrollOffset = 0;
                this.rebuildWidgets();
            }
        }).bounds(sidebarX, sidebarY + 50, 110, 20).build();
        this.addRenderableWidget(this.clearChatButton);

        if (this.selectedTab == 0) {
            int chatX = startX + 130;
            int chatY = startY + 205;
            int chatW = 300;

            this.inputField = new EditBox(this.font, chatX, chatY, chatW - 55, 20, Component.literal("Escribe tu comando..."));
            this.inputField.setMaxLength(256);
            this.addRenderableWidget(this.inputField);

            this.sendButton = Button.builder(Component.literal("Enviar"), b -> this.sendMessageToNox())
                    .bounds(chatX + chatW - 50, chatY, 50, 20).build();
            this.addRenderableWidget(this.sendButton);

        } else if (this.selectedTab == 2) {
            int ctrlX = startX + 140;
            int ctrlY = startY + 125; // Botones más abajo para dejar espacio libre arriba

            // Botón: Mesa de Crafteo Remota
            this.craftingButton = Button.builder(Component.literal("🛠️ Abrir Mesa de Crafteo Remota"), b -> {
                com.example.cobaltbot.network.NoxMessages.sendToServer(new com.example.cobaltbot.network.NoxCraftingPacket());
                this.minecraft.setScreen(null);
            }).bounds(ctrlX, ctrlY, 250, 20).build();
            this.addRenderableWidget(this.craftingButton);

            // Botón: Inventario Remoto
            this.inventoryButton = Button.builder(Component.literal("🎒 Acceder a Inventario de Cobalt"), b -> {
                com.example.cobaltbot.network.NoxMessages.sendToServer(new com.example.cobaltbot.network.NoxInventoryPacket());
                this.minecraft.setScreen(null);
            }).bounds(ctrlX, ctrlY + 25, 250, 20).build();
            this.addRenderableWidget(this.inventoryButton);
        }
    }

    private static List<String[]> cargarHistorialPares() {
        List<String[]> pares = new ArrayList<>();
        File chatFile = getChatFileForCurrentWorld();
        if (chatFile.exists()) {
            try (BufferedReader reader = new BufferedReader(new FileReader(chatFile))) {
                String timestampLine;
                while ((timestampLine = reader.readLine()) != null) {
                    String messageLine = reader.readLine();
                    if (messageLine != null) {
                        pares.add(new String[]{timestampLine, messageLine});
                    }
                }
            } catch (Exception e) {
                System.out.println("[-] Error leyendo historial en pares: " + e.getMessage());
            }
        }
        return pares;
    }

    private static void limpiarHistorialDisco() {
        File chatFile = getChatFileForCurrentWorld();
        if (chatFile.exists()) {
            chatFile.delete();
        }
    }

    @Override
    public boolean mouseScrolled(double mouseX, double mouseY, double delta) {
        if (this.selectedTab == 0) {
            List<String[]> historialPares = cargarHistorialPares();
            int maxScroll = Math.max(0, historialPares.size() - 1);

            if (delta > 0) {
                this.scrollOffset = Math.min(maxScroll, this.scrollOffset + 1);
            } else if (delta < 0) {
                this.scrollOffset = Math.max(0, this.scrollOffset - 1);
            }
            return true;
        }
        return super.mouseScrolled(mouseX, mouseY, delta);
    }

    public static boolean tieneChip(Player player) {
        if (player == null) return false;
        if (player.getMainHandItem().getItem() instanceof com.example.cobaltbot.item.NoxSummonerItem
                || player.getOffhandItem().getItem() instanceof com.example.cobaltbot.item.NoxSummonerItem) {
            return true;
        }
        for (ItemStack stack : player.getInventory().items) {
            if (stack.getItem() instanceof com.example.cobaltbot.item.NoxSummonerItem) {
                return true;
            }
        }
        return false;
    }

    @Override
    public void tick() {
        super.tick();
        if (this.minecraft != null && !tieneChip(this.minecraft.player)) {
            this.minecraft.setScreen(null);
        }
    }

    private void sendMessageToNox() {
        String message = this.inputField.getValue();
        if (!message.trim().isEmpty()) {

            Player player = this.minecraft.player;
            if (player != null) {
                player.sendSystemMessage(Component.literal("§bTú: §f" + message));
            }

            registrarMensajeDiscoLocal("Tú", message);
            this.scrollOffset = 0;

            // Si el mensaje pide visión, activamos la captura con delay y autolimpieza
            String msgLower = message.toLowerCase();
            if (msgLower.contains("mira") || msgLower.contains("que ves") || msgLower.contains("qué ves") || msgLower.contains("observa")) {
                NoxScreenshotUtil.tomarCapturaConDelay();
            }

            this.minecraft.setScreen(null);

            com.example.cobaltbot.network.NoxMessages.sendToServer(
                    new com.example.cobaltbot.network.NoxChatPacket(message)
            );

            this.inputField.setValue("");
        }
    }

    public static void registrarMensajeDiscoLocal(String emisor, String mensaje) {
        DateTimeFormatter dtf = DateTimeFormatter.ofPattern("dd/MM/yyyy - EEEE - hh:mm a");
        String timestamp = "§7[" + dtf.format(LocalDateTime.now()) + "]";
        String formatoEmisor = "§b" + emisor + ": §f" + mensaje;

        try {
            File chatFile = getChatFileForCurrentWorld();
            File dir = chatFile.getParentFile();
            if (!dir.exists()) dir.mkdirs();

            try (PrintWriter out = new PrintWriter(new FileWriter(chatFile, true))) {
                out.println(timestamp);
                out.println(formatoEmisor);
            }
        } catch (Exception e) {
            System.out.println("[-] Error guardando mensaje en disco: " + e.getMessage());
        }
    }

    @Override
    public boolean keyPressed(int keyCode, int scanCode, int modifiers) {
        if (this.selectedTab == 0 && (keyCode == GLFW.GLFW_KEY_ENTER || keyCode == GLFW.GLFW_KEY_KP_ENTER)) {
            this.sendMessageToNox();
            return true;
        }
        return super.keyPressed(keyCode, scanCode, modifiers);
    }

    @Override
    public void render(GuiGraphics guiGraphics, int mouseX, int mouseY, float partialTick) {
        this.renderBackground(guiGraphics);

        int panelWidth = 440;
        int panelHeight = 240;
        int startX = (this.width - panelWidth) / 2;
        int startY = (this.height - panelHeight) / 2;

        guiGraphics.fill(startX, startY, startX + panelWidth, startY + panelHeight, 0xEE10141A);
        guiGraphics.renderOutline(startX, startY, panelWidth, panelHeight, 0xFF00FFFF);
        guiGraphics.fill(startX + 125, startY + 45, startX + 126, startY + panelHeight - 10, 0xFF005555);

        guiGraphics.drawString(this.font, "Terminal Táctica: Nox", startX + 15, startY + 16, 0x00FFFF, false);

        if (this.selectedTab == 0) {
            List<String[]> historialPares = cargarHistorialPares();

            // Escudo anti-crasheo si el chat está vacío
            if (historialPares == null || historialPares.isEmpty()) {
                super.render(guiGraphics, mouseX, mouseY, partialTick);
                return;
            }

            int renderY = startY + 50;
            int maxY = startY + 195;

            int startIndex = Math.max(0, historialPares.size() - 1 - this.scrollOffset);

            for (int i = startIndex; i >= 0; i--) {
                String[] par = historialPares.get(i);
                String timestamp = par[0];
                String mensajeEmisor = par[1];

                List<FormattedCharSequence> lineasMensaje = this.font.split(Component.literal(mensajeEmisor), 285);
                int alturaBloque = 12 + (lineasMensaje.size() * 11);

                if (renderY + alturaBloque > maxY) {
                    break;
                }

                guiGraphics.drawString(this.font, timestamp, startX + 135, renderY, 0xFFFFFFFF, false);
                renderY += 11;

                for (FormattedCharSequence seq : lineasMensaje) {
                    guiGraphics.drawString(this.font, seq, startX + 135, renderY, 0xFFFFFFFF, false);
                    renderY += 11;
                }

                renderY += 4;
            }

            if (historialPares.size() > 5) {
                int barX = startX + 425;
                int barTop = startY + 50;
                int barBottom = startY + 195;
                int barHeight = barBottom - barTop;
                int maxS = Math.max(1, historialPares.size() - 1);
                int thumbHeight = Math.max(15, barHeight * 5 / historialPares.size());
                int thumbY = barTop + (int)((barHeight - thumbHeight) * ((double)this.scrollOffset / maxS));

                guiGraphics.fill(barX, barTop, barX + 4, barBottom, 0xFF222222);
                guiGraphics.fill(barX, thumbY, barX + 4, thumbY + thumbHeight, 0xFF00FFFF);
            }

        } else if (this.selectedTab == 1) {
            int diagX = startX + 140;
            int diagY = startY + 60;

            guiGraphics.drawString(this.font, "§e=== ESTADO DEL NÚCLEO NBT ===", diagX, diagY, 0xFFFF55, false);

            if (this.minecraft != null && this.minecraft.player != null) {
                Player player = this.minecraft.player;
                ItemStack stack = ItemStack.EMPTY;

                if (player.getMainHandItem().getItem() instanceof com.example.cobaltbot.item.NoxSummonerItem) {
                    stack = player.getMainHandItem();
                } else if (player.getOffhandItem().getItem() instanceof com.example.cobaltbot.item.NoxSummonerItem) {
                    stack = player.getOffhandItem();
                } else {
                    for (ItemStack invStack : player.getInventory().items) {
                        if (invStack.getItem() instanceof com.example.cobaltbot.item.NoxSummonerItem) {
                            stack = invStack;
                            break;
                        }
                    }
                }

                if (!stack.isEmpty()) {
                    CompoundTag tag = stack.getTag();
                    if (tag != null && tag.contains("IsDead") && tag.getBoolean("IsDead")) {
                        formatCriticalState(guiGraphics, diagX, diagY, tag);
                    } else if (tag != null && tag.getBoolean("IsDeployed")) {
                        guiGraphics.drawString(this.font, "§e[ESTADO: ACTIVO]", diagX, diagY + 20, 0xFFFF55, false);
                        guiGraphics.drawString(this.font, "Unidad operando en el mundo físico.", diagX, diagY + 35, 0xFFFFFF, false);
                    } else {
                        guiGraphics.drawString(this.font, "§a[ESTADO: STANDBY]", diagX, diagY + 20, 0x55FF55, false);
                        guiGraphics.drawString(this.font, "Sistema neuronal listo en el chip.", diagX, diagY + 35, 0xFFFFFF, false);
                    }
                } else {
                    guiGraphics.drawString(this.font, "§c[AVISO]: Chip no localizado.", diagX, diagY + 20, 0xFF5555, false);
                    guiGraphics.drawString(this.font, "Ten el chip en mano o inventario.", diagX, diagY + 35, 0xAAAAAA, false);
                }
            }

        } else if (this.selectedTab == 2) {
            int ctrlX = startX + 140;
            int ctrlY = startY + 65;

            // Texto descriptivo posicionado limpio y sin invadir los botones
            guiGraphics.drawString(this.font, "§b=== CONTROL INDUSTRIAL ===", ctrlX, ctrlY, 0x00FFFF, false);
            guiGraphics.drawString(this.font, "Interfaz inalámbrica para gestión de inventarios", ctrlX, ctrlY + 15, 0xAAAAAA, false);
            guiGraphics.drawString(this.font, "y crafteos a distancia (Rango: 16 bloques).", ctrlX, ctrlY + 27, 0xAAAAAA, false);
        }

        super.render(guiGraphics, mouseX, mouseY, partialTick);
    }

    private void formatCriticalState(GuiGraphics guiGraphics, int diagX, int diagY, CompoundTag tag) {
        float regenTicksLeft = tag.getFloat("RegenTicksLeft");
        int remainingMinutes = (int) Math.ceil(regenTicksLeft / 1200.0f);
        guiGraphics.drawString(this.font, "§c[ESTADO: CRÍTICO]", diagX, diagY + 20, 0xFF5555, false);
        guiGraphics.drawString(this.font, "Núcleo destruido en combate.", diagX, diagY + 35, 0xFFFFFF, false);
        guiGraphics.drawString(this.font, "Reconstrucción: ~" + remainingMinutes + " min", diagX, diagY + 50, 0xFFAA00, false);
    }

    @Override
    public boolean isPauseScreen() {
        return false;
    }
}
