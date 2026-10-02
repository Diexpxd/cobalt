package com.example.cobaltbot.registry;

import com.example.cobaltbot.CobaltMod;
import com.example.cobaltbot.entity.CobaltDroneEntity;
import com.example.cobaltbot.entity.CobaltEntity;
import com.example.cobaltbot.entity.EmpWaveEntity;
import com.example.cobaltbot.entity.PlasmaBallEntity; // <-- NUEVA IMPORTACIÓN
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.MobCategory;
import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;

public class ModEntities {
    public static final DeferredRegister<EntityType<?>> ENTITIES =
            DeferredRegister.create(ForgeRegistries.ENTITY_TYPES, CobaltMod.MOD_ID);

    // Registramos a Nox (con el nombre interno "nox")
    public static final RegistryObject<EntityType<CobaltEntity>> COBALT =
            ENTITIES.register("nox", () -> EntityType.Builder.of(CobaltEntity::new, MobCategory.MONSTER)
                    .sized(0.6f, 1.95f) // Ancho y alto de la caja de colisión (Hitbox)
                    .build(new ResourceLocation(CobaltMod.MOD_ID, "nox").toString()));

    public static final RegistryObject<EntityType<PlasmaBallEntity>> PLASMA_BALL =
            ENTITIES.register("plasma_ball", () -> EntityType.Builder.<PlasmaBallEntity>of(PlasmaBallEntity::new, MobCategory.MISC)
                    .sized(0.5f, 0.5f) // Tamaño de la hitbox del proyectil
                    .clientTrackingRange(4)
                    .updateInterval(10)
                    .build(new ResourceLocation(CobaltMod.MOD_ID, "plasma_ball").toString()));

    public static final RegistryObject<EntityType<CobaltDroneEntity>> DRONE =
            ENTITIES.register("cobalt_drone", () -> EntityType.Builder.<CobaltDroneEntity>of(CobaltDroneEntity::new, MobCategory.MISC)
                    .sized(0.5f, 0.5f)
                    .fireImmune()
                    .clientTrackingRange(8)
                    .updateInterval(2)
                    .build(new ResourceLocation(CobaltMod.MOD_ID, "cobalt_drone").toString()));

    public static final RegistryObject<EntityType<EmpWaveEntity>> EMP_WAVE =
            ENTITIES.register("emp_wave", () -> EntityType.Builder.<EmpWaveEntity>of(EmpWaveEntity::new, MobCategory.MISC)
                    .sized(0.1f, 0.1f)
                    .fireImmune()
                    .clientTrackingRange(10)
                    .updateInterval(20)
                    .build(new ResourceLocation(CobaltMod.MOD_ID, "emp_wave").toString()));

    public static void register(IEventBus eventBus) {
        ENTITIES.register(eventBus);
    }
}
