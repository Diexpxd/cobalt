package com.example.cobaltbot.event;

import com.example.cobaltbot.CobaltMod;
import com.example.cobaltbot.entity.client.NoxRenderer;
import com.example.cobaltbot.registry.ModEntities;
import com.example.cobaltbot.registry.ModItems;
import com.example.cobaltbot.client.gui.NoxInteractScreen; // NUEVO: Importamos tu interfaz

import net.minecraft.client.Minecraft;
import net.minecraft.client.KeyMapping; // NUEVO: Para crear la tecla
import com.mojang.blaze3d.platform.InputConstants; // NUEVO: Para leer el teclado
import org.lwjgl.glfw.GLFW; // NUEVO: Códigos de teclas

import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.monster.Enemy;
import net.minecraft.world.item.CreativeModeTabs;
import net.minecraft.world.phys.AABB;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.EntityRenderersEvent;
import net.minecraftforge.client.event.RegisterKeyMappingsEvent; // NUEVO: Evento para registrar la tecla
import net.minecraftforge.client.event.InputEvent; // NUEVO: Evento para detectar cuando la presionas
import net.minecraftforge.event.BuildCreativeModeTabContentsEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

import java.io.File;
import java.io.FileWriter;
import java.util.List;

public class ClientEvents {

    public static final KeyMapping OPEN_NOX_KEY = new KeyMapping(
            "key.cobaltbot.open_gui", // ID interno del nombre de la tecla
            InputConstants.Type.KEYSYM,
            GLFW.GLFW_KEY_V, // Tecla V por defecto
            "key.categories.cobaltbot" // Categoría en el menú de controles
    );

    @Mod.EventBusSubscriber(modid = CobaltMod.MOD_ID, value = Dist.CLIENT, bus = Mod.EventBusSubscriber.Bus.MOD)
    public static class ClientModEvents {

        // NUEVO: Registramos la tecla en el sistema de Minecraft al cargar el mod
        @SubscribeEvent
        public static void onKeyRegister(RegisterKeyMappingsEvent event) {
            event.register(OPEN_NOX_KEY);
        }

        @SubscribeEvent
        public static void registerEntityRenderers(EntityRenderersEvent.RegisterRenderers event) {
            event.registerEntityRenderer(ModEntities.COBALT.get(), NoxRenderer::new);
        }

        @SubscribeEvent
        public static void addCreative(BuildCreativeModeTabContentsEvent event) {
            if (event.getTabKey() == CreativeModeTabs.TOOLS_AND_UTILITIES) {
                event.accept(ModItems.NOX_SUMMONER);
            }
        }
    }

    @Mod.EventBusSubscriber(modid = CobaltMod.MOD_ID, value = Dist.CLIENT, bus = Mod.EventBusSubscriber.Bus.FORGE)
    public static class ClientForgeEvents {

        // NUEVO: Escuchamos el teclado en tiempo real
        @SubscribeEvent
        public static void onKeyInput(InputEvent.Key event) {
            Minecraft mc = Minecraft.getInstance();
            if (OPEN_NOX_KEY.consumeClick() && mc.screen == null) {
                if (NoxInteractScreen.tieneChip(mc.player)) {
                    mc.setScreen(new NoxInteractScreen());
                } else {
                    mc.setScreen(new com.example.cobaltbot.client.gui.NoxNoSignalScreen());
                }
            }
        }

    }
}
