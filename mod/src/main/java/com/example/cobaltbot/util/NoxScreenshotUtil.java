package com.example.cobaltbot.util;

import net.minecraft.client.Minecraft;
import net.minecraft.client.Screenshot;

import java.io.File;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;

public class NoxScreenshotUtil {

    public static void tomarCapturaConDelay() {
        File dir = com.example.cobaltbot.util.NoxRutas.dir();
        if (!dir.exists()) {
            dir.mkdirs();
        }

        File outputFile = new File(dir, "captura.png");
        if (outputFile.exists()) {
            outputFile.delete();
        }

        CompletableFuture.delayedExecutor(1, TimeUnit.SECONDS).execute(() -> {
            Minecraft minecraft = Minecraft.getInstance();
            if (minecraft == null || minecraft.getMainRenderTarget() == null) return;

            minecraft.execute(() -> {
                try {
                    Screenshot.grab(
                            dir,
                            "captura.png",
                            minecraft.getMainRenderTarget(),
                            message -> {}
                    );
                    System.out.println("[Nox Vision] Captura con delay generada con éxito para LLaVA.");
                } catch (Exception e) {
                    System.out.println("[-] Error tomando captura con delay: " + e.getMessage());
                }
            });
        });
    }
}
