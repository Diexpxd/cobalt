package com.example.cobaltbot;

import com.example.cobaltbot.entity.CobaltEntity;
import com.example.cobaltbot.network.NoxMessages;
import com.example.cobaltbot.registry.ModEntities;
import com.example.cobaltbot.registry.ModItems;
import net.minecraftforge.event.entity.EntityAttributeCreationEvent;
import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.javafmlmod.FMLJavaModLoadingContext;

import software.bernie.geckolib.GeckoLib;

@Mod(CobaltMod.MOD_ID)
public class CobaltMod {
    public static final String MOD_ID = "cobaltbot";

    public CobaltMod() {
        IEventBus modEventBus = FMLJavaModLoadingContext.get().getModEventBus();

        // 1. ¡ESTA ES LA LÍNEA MÁGICA QUE ENCIENDE LOS MODELOS 3D!
        GeckoLib.initialize();

        // 2. Registramos a la entidad y los ítems en el juego
        ModEntities.register(modEventBus);
        ModItems.register(modEventBus);
        NoxMessages.register();

        // 3. Le inyectamos su vida y velocidad
        modEventBus.addListener(this::registerAttributes);
    }

    private void registerAttributes(EntityAttributeCreationEvent event) {
        event.put(ModEntities.COBALT.get(), CobaltEntity.createAttributes().build());
        event.put(ModEntities.DRONE.get(), com.example.cobaltbot.entity.CobaltDroneEntity.createAttributes().build());
    }
}
