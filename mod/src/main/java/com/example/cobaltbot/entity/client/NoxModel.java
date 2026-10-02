package com.example.cobaltbot.entity.client;

import com.example.cobaltbot.CobaltMod;
import com.example.cobaltbot.entity.CobaltEntity;
import net.minecraft.resources.ResourceLocation;
import software.bernie.geckolib.model.GeoModel;

public class NoxModel extends GeoModel<CobaltEntity> {

    @Override
    public ResourceLocation getModelResource(CobaltEntity animatable) {
        return new ResourceLocation(CobaltMod.MOD_ID, "geo/nox.geo.json");
    }

    @Override
    public ResourceLocation getTextureResource(CobaltEntity animatable) {
        return new ResourceLocation(CobaltMod.MOD_ID, "textures/entity/nox.png");
    }

    @Override
    public ResourceLocation getAnimationResource(CobaltEntity animatable) {
        return new ResourceLocation(CobaltMod.MOD_ID, "animations/nox.animation.json");
    }
}
