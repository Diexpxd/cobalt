package com.example.cobaltbot.entity.client;

import com.example.cobaltbot.CobaltMod;
import com.example.cobaltbot.entity.CobaltEntity;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import software.bernie.geckolib.renderer.GeoEntityRenderer;
import software.bernie.geckolib.renderer.layer.AutoGlowingGeoLayer;

public class NoxRenderer extends GeoEntityRenderer<CobaltEntity> {
    public NoxRenderer(EntityRendererProvider.Context renderManager) {
        super(renderManager, new NoxModel());

        this.shadowRadius = 0.5f;

        this.addRenderLayer(new AutoGlowingGeoLayer<>(this));
    }
}
