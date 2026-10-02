package com.example.cobaltbot.entity.client;

import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.world.entity.Entity;
import software.bernie.geckolib.core.animatable.GeoAnimatable;
import software.bernie.geckolib.renderer.GeoEntityRenderer;
import software.bernie.geckolib.renderer.layer.AutoGlowingGeoLayer;

/** Renderer de los efectos de habilidad: modelo GeckoLib con su capa de brillo, sin sombra y a la escala que se pida. */
public class EfectoRenderer<T extends Entity & GeoAnimatable> extends GeoEntityRenderer<T> {
    public EfectoRenderer(EntityRendererProvider.Context contexto, String nombre, float escala) {
        super(contexto, new EfectoModel<T>(nombre));
        this.shadowRadius = 0.0F;
        this.scaleWidth = escala;
        this.scaleHeight = escala;
        this.addRenderLayer(new AutoGlowingGeoLayer<>(this));
    }
}
