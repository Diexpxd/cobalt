package com.example.cobaltbot.entity;

import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.monster.Enemy;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.entity.projectile.AbstractHurtingProjectile;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.EntityHitResult;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.common.Tags;
import net.minecraftforge.entity.PartEntity;

public class PlasmaBallEntity extends AbstractHurtingProjectile implements software.bernie.geckolib.animatable.GeoEntity {

    private final software.bernie.geckolib.core.animatable.instance.AnimatableInstanceCache cacheAnim = software.bernie.geckolib.util.GeckoLibUtil.createInstanceCache(this);

    @Override
    public void registerControllers(software.bernie.geckolib.core.animation.AnimatableManager.ControllerRegistrar controllers) {
        controllers.add(new software.bernie.geckolib.core.animation.AnimationController<>(this, "spin", 0, estado -> {
            estado.getController().setAnimation(software.bernie.geckolib.core.animation.RawAnimation.begin().then("spin", software.bernie.geckolib.core.animation.Animation.LoopType.LOOP));
            return software.bernie.geckolib.core.object.PlayState.CONTINUE;
        }));
    }

    @Override
    public software.bernie.geckolib.core.animatable.instance.AnimatableInstanceCache getAnimatableInstanceCache() {
        return this.cacheAnim;
    }

    // Daño mágico puro: perfora armaduras básicas
    private static final float DANO_DIRECTO = 8.0F;   // 4 corazones al blanco impactado
    private static final float DANO_AREA = 5.0F;      // 2.5 corazones a los hostiles cercanos al impacto
    private static final double RADIO_AREA = 2.5D;

    private float escalaDano = 1.0F;

    public void setEscalaDano(float escala) {
        this.escalaDano = Math.max(0.0F, escala);
    }

    // Constructor por defecto necesario para el registro de Forge
    public PlasmaBallEntity(EntityType<? extends AbstractHurtingProjectile> entityType, Level level) {
        super(entityType, level);
    }

    // Constructor para dispararlo desde Cobalt hacia un objetivo
    public PlasmaBallEntity(EntityType<? extends AbstractHurtingProjectile> entityType, LivingEntity shooter, double accelX, double accelY, double accelZ, Level level) {
        super(entityType, shooter, accelX, accelY, accelZ, level);
    }

    private static boolean esBlancoValido(Entity entidad) {
        if (entidad instanceof PartEntity<?> parte) {
            entidad = parte.getParent();
        }
        if (entidad == null || entidad instanceof Player || entidad instanceof CobaltEntity) {
            return false;
        }
        return entidad instanceof LivingEntity
                && (entidad instanceof Enemy || entidad.getType().is(Tags.EntityTypes.BOSSES));
    }

    @Override
    protected boolean canHitEntity(Entity entidad) {
        return esBlancoValido(entidad) && super.canHitEntity(entidad);
    }

    @Override
    protected void onHitEntity(EntityHitResult result) {
        super.onHitEntity(result);
        if (!this.level().isClientSide()) {
            Entity golpeada = result.getEntity();
            if (esBlancoValido(golpeada)) {
                golpeada.hurt(this.damageSources().indirectMagic(this, this.getOwner()), DANO_DIRECTO * this.escalaDano);
            }
        }
    }

    @Override
    protected void onHit(HitResult result) {
        super.onHit(result);
        if (this.level() instanceof ServerLevel nivel) {
            Entity directa = result instanceof EntityHitResult ehr ? ehr.getEntity() : null;
            this.explosionSelectiva(nivel, directa);
            this.discard();
        }
    }

    private void explosionSelectiva(ServerLevel nivel, Entity directa) {
        final Vec3 centro = this.position();
        final Entity yaGolpeada = (directa instanceof PartEntity<?> parte) ? parte.getParent() : directa;

        AABB zona = new AABB(centro, centro).inflate(RADIO_AREA);
        for (LivingEntity e : nivel.getEntitiesOfClass(LivingEntity.class, zona,
                x -> x != yaGolpeada && esBlancoValido(x) && x.distanceToSqr(centro) <= RADIO_AREA * RADIO_AREA)) {
            e.hurt(this.damageSources().indirectMagic(this, this.getOwner()), DANO_AREA * this.escalaDano);
        }

        nivel.sendParticles(ParticleTypes.EXPLOSION, centro.x, centro.y, centro.z, 1, 0.0D, 0.0D, 0.0D, 0.0D);
        nivel.sendParticles(ParticleTypes.SOUL_FIRE_FLAME, centro.x, centro.y, centro.z, 20, 0.4D, 0.4D, 0.4D, 0.05D);
        nivel.playSound(null, centro.x, centro.y, centro.z, SoundEvents.GENERIC_EXPLODE, SoundSource.HOSTILE, 1.0F, 1.4F);
    }

    @Override
    protected boolean shouldBurn() {
        return false;
    }

    @Override
    public void tick() {
        super.tick();
        if (this.level().isClientSide()) {
            this.level().addParticle(ParticleTypes.SOUL_FIRE_FLAME,
                    this.getX(), this.getY() + 0.15D, this.getZ(),
                    0.0D, 0.0D, 0.0D);
            this.level().addParticle(ParticleTypes.ELECTRIC_SPARK,
                    this.getX(), this.getY() + 0.15D, this.getZ(),
                    (this.random.nextDouble() - 0.5) * 0.2,
                    (this.random.nextDouble() - 0.5) * 0.2,
                    (this.random.nextDouble() - 0.5) * 0.2);
        }
    }
}
