package com.example.cobaltbot;

import com.example.cobaltbot.entity.client.EfectoRenderer;
import com.example.cobaltbot.entity.client.NoxRenderer;
import com.example.cobaltbot.registry.ModEntities;
import net.minecraft.client.renderer.entity.NoopRenderer;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.EntityRenderersEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

@Mod.EventBusSubscriber(modid = CobaltMod.MOD_ID, bus = Mod.EventBusSubscriber.Bus.MOD, value = Dist.CLIENT)
public class ClientModEventSubscriber {

    @SubscribeEvent
    public static void registerRenderers(EntityRenderersEvent.RegisterRenderers event) {
        event.registerEntityRenderer(ModEntities.COBALT.get(), NoxRenderer::new);

        event.registerEntityRenderer(ModEntities.PLASMA_BALL.get(), contexto -> new EfectoRenderer<>(contexto, "plasma", 1.6F));

        event.registerEntityRenderer(ModEntities.DRONE.get(), contexto -> new EfectoRenderer<>(contexto, "drone", 1.4F));
        event.registerEntityRenderer(ModEntities.EMP_WAVE.get(), contexto -> new EfectoRenderer<>(contexto, "emp_wave", 1.0F));
    }
}
