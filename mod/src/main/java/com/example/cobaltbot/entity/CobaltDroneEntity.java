package com.example.cobaltbot.entity;

import com.example.cobaltbot.registry.ModEntities;
import com.example.cobaltbot.util.NoxDrones;
import com.example.cobaltbot.util.NoxSensorWriter;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.tags.DamageTypeTags;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.PathfinderMob;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.projectile.ItemSupplier;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/** Dron de apoyo del enjambre de Cobalt: vuela en formación alrededor de Cobalt (o de su objetivo), dispara el. */
public class CobaltDroneEntity extends PathfinderMob implements ItemSupplier, software.bernie.geckolib.animatable.GeoEntity {

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

    private static final double ALCANCE_DISPARO = 22.0D;
    private static final double DIST_ASEDIO = 7.0D;
    private static final double RADIO_ORBITA = 2.6D;
    private static final int CADENCIA_TICKS = 26;
    private static final double DISTANCIA_MAX_AL_DUENO = 48.0D;

    private UUID duenoId = null;
    private int vidaTicks = 0;
    private int indice = 0;
    private int total = 1;
    private int cadencia = 0;
    private int reevaluar = 0;
    private float escalaDano = 0.4F;
    private LivingEntity objetivo = null;

    public CobaltDroneEntity(EntityType<? extends CobaltDroneEntity> tipo, Level nivel) {
        super(tipo, nivel);
        this.setNoGravity(true);
        this.xpReward = 0;
    }

    public static AttributeSupplier.Builder createAttributes() {
        return Mob.createMobAttributes()
                .add(Attributes.MAX_HEALTH, 4.0D)
                .add(Attributes.FLYING_SPEED, 0.6D)
                .add(Attributes.MOVEMENT_SPEED, 0.6D)
                .add(Attributes.FOLLOW_RANGE, 32.0D);
    }

    public void iniciar(CobaltEntity dueno, int indice, int total, int vidaTicks, float escalaDano) {
        this.duenoId = dueno.getUUID();
        this.indice = indice;
        this.total = Math.max(1, total);
        this.vidaTicks = vidaTicks;
        this.escalaDano = escalaDano;
        this.cadencia = 10 + indice * 3; // no disparan todos a la vez
    }

    public UUID getDuenoId() {
        return this.duenoId;
    }

    @Override
    public ItemStack getItem() {
        return new ItemStack(Items.ENDER_EYE);
    }

    @Override
    public boolean isInvulnerableTo(DamageSource fuente) {
        return !fuente.is(DamageTypeTags.BYPASSES_INVULNERABILITY); // solo el vacío
    }

    @Override
    public boolean isPushable() {
        return false;
    }

    @Override
    public boolean isPushedByFluid() {
        return false;
    }

    @Override
    public boolean canBreatheUnderwater() {
        return true;
    }

    @Override
    public boolean shouldBeSaved() {
        return false; // un enjambre no sobrevive a guardar y recargar el mundo
    }

    @Override
    public boolean removeWhenFarAway(double distanciaAlJugador) {
        return false; // se retira él solo (vida o dueño)
    }

    @Override
    public boolean causeFallDamage(float distancia, float multiplicador, DamageSource fuente) {
        return false;
    }

    @Override
    public void tick() {
        super.tick();
        if (this.level().isClientSide() && this.tickCount % 2 == 0) {
            this.level().addParticle(ParticleTypes.END_ROD, this.getX(), this.getY() + 0.1D, this.getZ(), 0.0D, 0.0D, 0.0D);
        }
    }

    @Override
    protected void customServerAiStep() {
        super.customServerAiStep();
        if (!(this.level() instanceof ServerLevel nivel)) return;

        Entity e = this.duenoId == null ? null : nivel.getEntity(this.duenoId);
        if (!(e instanceof CobaltEntity dueno) || !dueno.isAlive() || --this.vidaTicks <= 0) {
            this.retirarse(nivel);
            return;
        }
        if (this.distanceToSqr(dueno) > DISTANCIA_MAX_AL_DUENO * DISTANCIA_MAX_AL_DUENO) { // se quedó atrás o atascado
            this.teleportTo(dueno.getX(), dueno.getY() + 1.0D, dueno.getZ());
        }

        if (--this.reevaluar <= 0) {
            this.reevaluar = 10;
            this.objetivo = this.elegirObjetivo(dueno);
        }
        if (this.objetivo != null && !this.objetivo.isAlive()) this.objetivo = null;

        Vec3 centro = this.objetivo != null ? this.objetivo.position() : dueno.position();
        double[] o = NoxDrones.posicionEnAnillo(this.indice, this.total, this.tickCount, this.objetivo != null ? DIST_ASEDIO : RADIO_ORBITA,
                this.objetivo != null ? 3.0D : 2.0D);
        Vec3 hacia = centro.add(o[0], o[1], o[2]).subtract(this.position());
        double d = hacia.length();
        Vec3 deseado = d > 1.0E-6D ? hacia.scale(NoxDrones.velocidadHacia(d) / d) : Vec3.ZERO;
        this.setDeltaMovement(this.getDeltaMovement().scale(0.5D).add(deseado.scale(0.5D)));

        if (this.objetivo != null) {
            this.getLookControl().setLookAt(this.objetivo, 30.0F, 30.0F);
            if (--this.cadencia <= 0 && this.distanceToSqr(this.objetivo) <= ALCANCE_DISPARO * ALCANCE_DISPARO && this.hasLineOfSight(this.objetivo)) {
                this.cadencia = CADENCIA_TICKS + (this.indice % 3) * 2;
                this.disparar(this.objetivo);
            }
        }
    }

    private LivingEntity elegirObjetivo(CobaltEntity dueno) {
        List<LivingEntity> lista = new ArrayList<>(NoxSensorWriter.hostilesEnRadio(this.level(), dueno, 24.0D));
        lista.removeIf(x -> !NoxSensorWriter.esAmenaza(dueno, x) || NoxSensorWriter.esAliado(x));
        LivingEntity deDueno = dueno.getTarget();
        boolean prioridad = deDueno != null && deDueno.isAlive() && lista.contains(deDueno);
        if (prioridad) {
            lista.remove(deDueno);
            lista.add(0, deDueno);
        }
        int i = NoxDrones.elegirCandidato(this.indice, lista.size(), prioridad);
        return i < 0 ? null : lista.get(i);
    }

    private void disparar(LivingEntity blanco) {
        double dx = blanco.getX() - this.getX();
        double dy = blanco.getY(0.5D) - (this.getY() + 0.25D);
        double dz = blanco.getZ() - this.getZ();
        if (dx * dx + dy * dy + dz * dz < 1.0E-4D) return; // vector nulo -> NaN en el proyectil
        PlasmaBallEntity plasma = new PlasmaBallEntity(ModEntities.PLASMA_BALL.get(), this, dx, dy, dz, this.level());
        plasma.setPos(this.getX(), this.getY() + 0.25D, this.getZ());
        plasma.setEscalaDano(this.escalaDano);
        this.level().addFreshEntity(plasma);
        this.level().playSound(null, this.getX(), this.getY(), this.getZ(), SoundEvents.BLAZE_SHOOT, SoundSource.NEUTRAL, 0.35F, 1.8F);
    }

    public void retirarse(ServerLevel nivel) {
        nivel.sendParticles(ParticleTypes.POOF, this.getX(), this.getY(), this.getZ(), 8, 0.2D, 0.2D, 0.2D, 0.02D);
        this.discard();
    }
}
