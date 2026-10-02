package com.example.cobaltbot.client;

import net.minecraft.client.Minecraft;
import net.minecraft.client.Screenshot;
import com.mojang.blaze3d.platform.NativeImage;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

import java.io.File;

@Mod.EventBusSubscriber(modid = "cobaltbot", bus = Mod.EventBusSubscriber.Bus.FORGE, value = Dist.CLIENT)
public class CobaltVisionTimer {

    private static int tickCounter = 0;
    private static final int SCREENSHOT_INTERVAL = 200;

    @SubscribeEvent
    public static void onClientTick(TickEvent.ClientTickEvent event) {
        // Solo ejecutar al final del tick para evitar dobles llamadas
        if (event.phase != TickEvent.Phase.END) return;

        Minecraft mc = Minecraft.getInstance();
        // Evitar que tome fotos en el menú principal
        if (mc.player == null || mc.level == null) return;

        if (!com.example.cobaltbot.util.NoxConfig.activo("vision_continua", false)) {
            tickCounter = 0;
            return;
        }

        tickCounter++;
        if (tickCounter >= SCREENSHOT_INTERVAL) {
            tickCounter = 0;

            if (mc.getMainRenderTarget() != null) {
                NativeImage imagenPantalla = Screenshot.takeScreenshot(mc.getMainRenderTarget());

                new Thread(() -> {
                    try {
                        File dir = com.example.cobaltbot.util.NoxRutas.dir();
                        if (!dir.exists()) dir.mkdirs();

                        // Guardamos en un archivo separado para el flujo continuo
                        File archivoCaptura = new File(dir, "vision_continua.png");
                        imagenPantalla.writeToFile(archivoCaptura);

                    } catch (Exception e) {
                        System.out.println("Error en la cámara de fondo: " + e.getMessage());
                    } finally {
                        // Es vital cerrar la imagen para liberar la memoria RAM
                        imagenPantalla.close();
                    }
                }).start();
            }
        }
    }
}
