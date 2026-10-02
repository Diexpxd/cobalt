package com.example.cobaltbot.entity.client;

import com.example.cobaltbot.CobaltMod;
import net.minecraft.resources.ResourceLocation;
import software.bernie.geckolib.core.animatable.GeoAnimatable;
import software.bernie.geckolib.model.GeoModel;

/** Modelo GeckoLib de un efecto de habilidad (plasma, onda EMP, dron): los tres archivos se llaman igual. */
public class EfectoModel<T extends GeoAnimatable> extends GeoModel<T> {
    private final ResourceLocation geo;
    private final ResourceLocation textura;
    private final ResourceLocation animaciones;

    public EfectoModel(String nombre) {
        this.geo = new ResourceLocation(CobaltMod.MOD_ID, "geo/" + nombre + ".geo.json");
        this.textura = new ResourceLocation(CobaltMod.MOD_ID, "textures/entity/" + nombre + ".png");
        this.animaciones = new ResourceLocation(CobaltMod.MOD_ID, "animations/" + nombre + ".animation.json");
    }

    @Override
    public ResourceLocation getModelResource(T animatable) {
        return geo;
    }

    @Override
    public ResourceLocation getTextureResource(T animatable) {
        return textura;
    }

    @Override
    public ResourceLocation getAnimationResource(T animatable) {
        return animaciones;
    }
}
