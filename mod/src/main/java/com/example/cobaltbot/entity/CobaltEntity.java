package com.example.cobaltbot.entity;

import com.example.cobaltbot.network.NoxOpenScreenPacket;
import com.example.cobaltbot.util.NoxSensorWriter;
import com.example.cobaltbot.util.NoxTools;
import com.example.cobaltbot.util.NoxBloques;
import com.example.cobaltbot.util.NoxLotes;
import com.example.cobaltbot.util.NoxMods;
import com.example.cobaltbot.util.NoxCarga;
import com.example.cobaltbot.util.NoxChunkLoader;
import com.example.cobaltbot.util.NoxConfig;
import com.example.cobaltbot.util.NoxSupervivencia;
import com.example.cobaltbot.util.NoxCombate;
import com.example.cobaltbot.util.NoxCuerpo;
import com.example.cobaltbot.util.NoxDrones;
import com.example.cobaltbot.util.NoxChip;
import com.example.cobaltbot.util.NoxDimension;
import com.example.cobaltbot.util.NoxServidor;
import com.example.cobaltbot.util.NoxTerreno;
import com.example.cobaltbot.util.NoxJefes;
import com.example.cobaltbot.util.NoxMinado;
import com.example.cobaltbot.util.NoxMovimiento;
import net.minecraft.client.Minecraft;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.network.syncher.EntityDataAccessor;
import net.minecraft.network.syncher.EntityDataSerializers;
import net.minecraft.network.syncher.SynchedEntityData;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.PathfinderMob;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.ai.control.FlyingMoveControl;
import net.minecraft.world.entity.ai.control.MoveControl;
import net.minecraft.world.entity.ai.goal.FloatGoal;
import net.minecraft.world.entity.ai.goal.Goal;
import net.minecraft.world.entity.ai.goal.LookAtPlayerGoal;
import net.minecraft.world.entity.ai.goal.RandomLookAroundGoal;
import net.minecraft.world.entity.ai.navigation.FlyingPathNavigation;
import net.minecraft.world.entity.ai.navigation.GroundPathNavigation;
import net.minecraft.world.entity.ai.navigation.WaterBoundPathNavigation;
import net.minecraft.world.entity.monster.Enemy;
import net.minecraft.world.entity.monster.RangedAttackMob;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.state.BlockState;
import software.bernie.geckolib.animatable.GeoEntity;
import software.bernie.geckolib.core.animatable.instance.AnimatableInstanceCache;
import software.bernie.geckolib.core.animation.*;
import software.bernie.geckolib.core.object.PlayState;
import software.bernie.geckolib.util.GeckoLibUtil;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.mojang.logging.LogUtils;
import net.minecraft.tags.FluidTags;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.phys.Vec3;
import org.slf4j.Logger;

import java.io.File;
import java.io.FileWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.EnumSet;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.UUID;

public class CobaltEntity extends PathfinderMob implements GeoEntity, RangedAttackMob {

    private static final Logger LOGGER = LogUtils.getLogger();

    private final AnimatableInstanceCache cache = GeckoLibUtil.createInstanceCache(this);
    private int empCooldownTicks = 0;
    private int dronesCooldownTicks = 0;   // enjambre: enfriamiento restante (empieza al desplegar)
    private int dronesRestantesTicks = 0;  // enjambre: lo que queda de apoyo

    private int lecturasCorruptas = 0;
    private final Set<String> accionesAvisadas = new HashSet<>();
    private static final Set<String> ACCIONES_SIN_EFECTO = Set.of("ninguna", "none", "");
    private boolean muerteReal = false;

    private static final double FOLLOW_RANGE_PATHFINDING = 64.0D;
    private static final double RADIO_DEFENSA_DUENO = 28.0D;  // solo adquiere blancos a <= 28 m del jugador (si lo sigue)
    private static final double RADIO_SOLTAR_DUENO = 36.0D;   // y suelta el blanco si se aleja a > 36 m del jugador
    private int combateSuprimidoTicks = 0;                    // tras 'ven'/'follow' no se inicia combate durante un rato
    private java.util.List<int[]> chunksMantenidos = java.util.List.of(); // chunks a los que Cobalt renueva su ticket de carga (ver NoxChunkLoader)
    private double distDuenoPrev = -1.0D;
    private int rezagoTicks = 0;                              // cuánto lleva lejos y sin acercarse
    private boolean venReanudaSeguimiento = false;
    private boolean venEsDueno = false;
    private double venMejorDist = 1.0E9D;                     // mejor distancia lograda hacia el destino de 'ven'/'go_to'
    private int venSinProgreso = 0;                           // ticks sin acercarse a ese destino
    private int objetivoExplicitoHasta = 0;

    private UUID ownerUUID;

    private static final EntityDataAccessor<Boolean> IS_FLYING =
            SynchedEntityData.defineId(CobaltEntity.class, EntityDataSerializers.BOOLEAN);

    private boolean isFlying = false;
    private boolean wasFlying = false;
    private boolean isPerformingEMP = false;
    private int empAnimationTicks = 0;

    private boolean isFollowingOwner = false;
    private int deathAnimationTicks = 0;
    private boolean isPerformingDeathAnim = false;

    private int autoTpCooldown = 0;
    private int stuckTicks = 0;
    private BlockPos lastPosForStuckCheck = BlockPos.ZERO;

    private final net.minecraft.world.SimpleContainer inventory = new net.minecraft.world.SimpleContainer(36);

    public net.minecraft.world.SimpleContainer getCobaltInventory() {
        return this.inventory;
    }

    public CobaltEntity(EntityType<? extends PathfinderMob> entityType, Level level) {
        super(entityType, level);
        this.setModoVuelo(false);
        this.setCustomName(Component.literal("§b[AGI] Cobalt"));
        this.setCustomNameVisible(true);
    }

    @Override
    protected void defineSynchedData() {
        super.defineSynchedData();
        this.entityData.define(IS_FLYING, false);
    }

    @Override
    public void addAdditionalSaveData(CompoundTag tag) {
        super.addAdditionalSaveData(tag);
        if (this.ownerUUID != null) {
            tag.putUUID("OwnerUUID", this.ownerUUID);
        }
        tag.putBoolean("IsFollowing", this.isFollowingOwner);
        tag.putInt("AutoTpCooldown", this.autoTpCooldown);
        tag.putInt("DronesCooldown", this.dronesCooldownTicks); // recargar el mundo no reinicia el enfriamiento
        tag.put("CobaltInv", NoxChip.serializar(this.inventory));
    }

    @Override
    public void readAdditionalSaveData(CompoundTag tag) {
        super.readAdditionalSaveData(tag);
        if (this.getAttribute(Attributes.FOLLOW_RANGE) != null) {
            this.getAttribute(Attributes.FOLLOW_RANGE).setBaseValue(FOLLOW_RANGE_PATHFINDING);
        }
        if (tag.hasUUID("OwnerUUID")) {
            this.ownerUUID = tag.getUUID("OwnerUUID");
        }
        this.isFollowingOwner = tag.getBoolean("IsFollowing");
        if (tag.contains("AutoTpCooldown")) {
            this.autoTpCooldown = tag.getInt("AutoTpCooldown");
        }
        this.dronesCooldownTicks = Math.max(0, tag.getInt("DronesCooldown"));
        if (tag.contains("CobaltInv")) NoxChip.deserializar(tag.getList("CobaltInv", 10), this.inventory);
    }

    public Player getCobaltOwner() {
        if (this.ownerUUID != null && this.level() instanceof ServerLevel serverLevel) {
            return serverLevel.getPlayerByUUID(this.ownerUUID); // Búsqueda global absoluta
        }
        return null;
    }

    public void setOwnerUUID(UUID ownerUUID) { this.ownerUUID = ownerUUID; }
    public UUID getOwnerUUID() { return this.ownerUUID; }

    public void openRemoteInventory(net.minecraft.server.level.ServerPlayer player) {
        player.openMenu(new net.minecraft.world.SimpleMenuProvider(
                (containerId, playerInventory, p) -> new net.minecraft.world.inventory.ChestMenu(
                        net.minecraft.world.inventory.MenuType.GENERIC_9x4,
                        containerId,
                        playerInventory,
                        this.inventory,
                        4
                ),
                Component.literal("§bInventario Táctico: Cobalt")
        ));
    }

    @Override
    protected void registerGoals() {
        this.goalSelector.addGoal(0, new CobaltFloatGoal(this));
        this.goalSelector.addGoal(1, new CobaltKitingGoal(this, 1.25D, 20));
        this.goalSelector.addGoal(6, new LookAtPlayerGoal(this, Player.class, 8.0F));
        this.goalSelector.addGoal(7, new RandomLookAroundGoal(this));
    }

    @Override
    public void performRangedAttack(net.minecraft.world.entity.LivingEntity target, float distanceFactor) {
        this.dispararPlasma(target);
    }

    private void dispararPlasma(LivingEntity target) {
        if (this.level().isClientSide()) return;

        double apuntarX = target.getX();
        double apuntarZ = target.getZ();
        if (NoxConfig.activo("prediccion_disparo")) {
            Vec3 vel = target.getDeltaMovement();
            double[] punto = NoxCombate.puntoDeApuntado(this.getX(), this.getY() + this.getEyeHeight(), this.getZ(),
                    target.getX(), target.getY(0.5D), target.getZ(), vel.x, vel.z);
            apuntarX = punto[0];
            apuntarZ = punto[2];
        }
        double d0 = apuntarX - this.getX();
        double d1 = target.getY(0.5D) - (this.getY() + this.getEyeHeight());
        double d2 = apuntarZ - this.getZ();

        if (d0 * d0 + d1 * d1 + d2 * d2 < 1.0E-4D) return;

        if (NoxConfig.activo("intercepcion_fuego_amigo") && this.jugadorEnLaTrayectoria(target, apuntarX, apuntarZ)) return;

        this.triggerAnim("attackController", "attack"); // animación de disparo (llega al cliente por paquete)
        PlasmaBallEntity plasma = new PlasmaBallEntity(com.example.cobaltbot.registry.ModEntities.PLASMA_BALL.get(), this, d0, d1, d2, this.level());
        plasma.setPos(this.getX(), this.getY() + this.getEyeHeight(), this.getZ());
        this.level().addFreshEntity(plasma);

        this.level().playSound(null, this.getX(), this.getY(), this.getZ(),
                net.minecraft.sounds.SoundEvents.BLAZE_SHOOT, net.minecraft.sounds.SoundSource.HOSTILE, 1.0F, 1.0F);
    }

    @Override
    public void registerControllers(AnimatableManager.ControllerRegistrar controllers) {
        controllers.add(new AnimationController<>(this, "controller", 8, this::predicate));
        controllers.add(new AnimationController<>(this, "attackController", 2, this::attackPredicate)
                .triggerableAnim("attack", RawAnimation.begin().then("attack", Animation.LoopType.PLAY_ONCE))
                .triggerableAnim("cast_spell", RawAnimation.begin().then("cast_spell", Animation.LoopType.PLAY_ONCE))
                .triggerableAnim("emp", RawAnimation.begin().then("emp", Animation.LoopType.PLAY_ONCE)));
        controllers.add(new AnimationController<>(this, "runico", 0, this::runicoPredicate));
    }

    private static boolean enAnimacion(AnimationController<?> c, String nombre) {
        var actual = c.getCurrentAnimation();
        return actual != null && nombre.equals(actual.animation().name()) && !c.hasAnimationFinished();
    }

    private <T extends GeoEntity> PlayState predicate(AnimationState<T> event) {
        AnimationController<T> c = event.getController();
        if (this.isDeadOrDying() || this.isPerformingDeathAnim) {
            c.setAnimation(RawAnimation.begin().then("death", Animation.LoopType.HOLD_ON_LAST_FRAME));
            return PlayState.CONTINUE;
        }

        boolean avanzando = event.isMoving();
        if (this.entityData.get(IS_FLYING)) {
            String vuelo = avanzando ? "fly_move" : "fly";
            if (!wasFlying) {
                wasFlying = true;
                c.setAnimation(RawAnimation.begin().then("fly_start", Animation.LoopType.PLAY_ONCE).then(vuelo, Animation.LoopType.LOOP));
            } else if (!enAnimacion(c, "fly_start")) {
                c.setAnimation(RawAnimation.begin().then(vuelo, Animation.LoopType.LOOP));
            }
            return PlayState.CONTINUE;
        }
        if (wasFlying) {
            wasFlying = false;
            c.setAnimation(RawAnimation.begin().then("fly_end", Animation.LoopType.PLAY_ONCE));
            return PlayState.CONTINUE;
        }
        if (enAnimacion(c, "fly_end")) return PlayState.CONTINUE; // aterrizando: se deja terminar

        if (this.isInWater() && this.getFluidHeight(net.minecraft.tags.FluidTags.WATER) > this.getBbHeight() * 0.5D) {
            c.setAnimation(RawAnimation.begin().then("swim", Animation.LoopType.LOOP));
            return PlayState.CONTINUE;
        }

        if (avanzando) {
            c.setAnimation(RawAnimation.begin().then("walk", Animation.LoopType.LOOP));
            return PlayState.CONTINUE;
        }

        c.setAnimation(RawAnimation.begin().then("idle", Animation.LoopType.LOOP));
        return PlayState.CONTINUE;
    }

    private <T extends GeoEntity> PlayState attackPredicate(AnimationState<T> event) {
        return PlayState.STOP;
    }

    private <T extends GeoEntity> PlayState runicoPredicate(AnimationState<T> event) {
        if (this.isDeadOrDying() || this.isPerformingDeathAnim) return PlayState.STOP;
        event.getController().setAnimation(RawAnimation.begin().then("runico", Animation.LoopType.LOOP));
        return PlayState.CONTINUE;
    }

    @Override
    public AnimatableInstanceCache getAnimatableInstanceCache() { return this.cache; }

    public static AttributeSupplier.Builder createAttributes() {
        return PathfinderMob.createMobAttributes()
                .add(Attributes.MAX_HEALTH, 50.0D)
                .add(Attributes.MOVEMENT_SPEED, 0.3F)
                .add(Attributes.FLYING_SPEED, 0.6F)
                .add(Attributes.ATTACK_DAMAGE, 5.0D)
                .add(Attributes.FOLLOW_RANGE, FOLLOW_RANGE_PATHFINDING);
    }

    @Override
    public boolean isPersistenceRequired() { return true; }

    @Override
    public InteractionResult mobInteract(Player player, InteractionHand hand) {
        if (hand == InteractionHand.MAIN_HAND) {
            if (this.level().isClientSide()) return InteractionResult.CONSUME;

            if (player instanceof net.minecraft.server.level.ServerPlayer serverPlayer) {
                boolean hasSummonerItem = serverPlayer.getMainHandItem().getItem() instanceof com.example.cobaltbot.item.NoxSummonerItem ||
                        serverPlayer.getOffhandItem().getItem() instanceof com.example.cobaltbot.item.NoxSummonerItem;

                if (!hasSummonerItem) {
                    for (ItemStack stack : serverPlayer.getInventory().items) {
                        if (stack.getItem() instanceof com.example.cobaltbot.item.NoxSummonerItem) {
                            hasSummonerItem = true;
                            break;
                        }
                    }
                }

                com.example.cobaltbot.network.NoxMessages.sendToPlayer(new NoxOpenScreenPacket(hasSummonerItem), serverPlayer);

                if (hasSummonerItem) {
                    this.getNavigation().stop();
                    this.lookAt(player, 30.0F, 30.0F);
                }
            }
            return InteractionResult.SUCCESS;
        }
        return super.mobInteract(player, hand);
    }

    @Override
    public boolean hurt(DamageSource source, float amount) {
        if (this.getHealth() - amount <= 0.0f) {
            if (source.getEntity() instanceof net.minecraft.world.entity.LivingEntity killer) {
                this.registrarEncuentroJefe(killer, "derrota");
            }

            if (!this.level().isClientSide() && !this.isPerformingDeathAnim) {
                this.isPerformingDeathAnim = true;
                this.setDeltaMovement(0, 0, 0);
                this.deathAnimationTicks = 40;
            }
            return false;
        }
        return super.hurt(source, amount);
    }

    public void recallToBase() {
        if (!this.level().isClientSide() && this.level() instanceof net.minecraft.server.level.ServerLevel serverLevel) {
            boolean tieneItems = false;
            for (int i = 0; i < this.inventory.getContainerSize(); i++) {
                if (!this.inventory.getItem(i).isEmpty()) { tieneItems = true; break; }
            }

            if (tieneItems) {
                BlockPos pos = this.blockPosition();
                serverLevel.setBlock(pos, net.minecraft.world.level.block.Blocks.CHEST.defaultBlockState(), 3);
                if (serverLevel.getBlockEntity(pos) instanceof net.minecraft.world.level.block.entity.ChestBlockEntity chest) {
                    for (int i = 0; i < this.inventory.getContainerSize(); i++) {
                        ItemStack stack = this.inventory.getItem(i);
                        if (!stack.isEmpty()) {
                            if (i < chest.getContainerSize()) chest.setItem(i, stack.copy()); else this.desbordeCofreMuerte(serverLevel, pos, stack.copy());
                            this.inventory.setItem(i, ItemStack.EMPTY);
                        }
                    }
                    chest.setChanged();
                }

                this.registrarWaypoint("inventario_nox_", pos);
            }
            this.discard();
        }
    }

    public void recallToBaseRealDeath() {
        if (!this.level().isClientSide() && this.level() instanceof net.minecraft.server.level.ServerLevel serverLevel) {
            boolean tieneItems = false;
            for (int i = 0; i < this.inventory.getContainerSize(); i++) {
                if (!this.inventory.getItem(i).isEmpty()) { tieneItems = true; break; }
            }

            if (tieneItems) {
                BlockPos pos = this.blockPosition();
                serverLevel.setBlock(pos, net.minecraft.world.level.block.Blocks.CHEST.defaultBlockState(), 3);
                if (serverLevel.getBlockEntity(pos) instanceof net.minecraft.world.level.block.entity.ChestBlockEntity chest) {
                    for (int i = 0; i < this.inventory.getContainerSize(); i++) {
                        ItemStack stack = this.inventory.getItem(i);
                        if (!stack.isEmpty()) {
                            if (i < chest.getContainerSize()) chest.setItem(i, stack.copy()); else this.desbordeCofreMuerte(serverLevel, pos, stack.copy());
                            this.inventory.setItem(i, ItemStack.EMPTY);
                        }
                    }
                    chest.setChanged();
                }

                this.registrarWaypoint("muerte_nox_", pos);
            }

            this.muerteReal = true; // remove() se lo comunica a cerebro.py vía nox_status.json
            Player owner = this.duenoEnCualquierDimension();
            if (owner != null) {
                for (ItemStack stack : owner.getInventory().items) {
                    if (stack.getItem() instanceof com.example.cobaltbot.item.NoxSummonerItem) {
                        CompoundTag tag = stack.getOrCreateTag();
                        tag.putBoolean("IsDeployed", false);
                        tag.putBoolean("IsDead", true);
                        tag.putFloat("RegenTicksLeft", 18000.0f);
                        NoxChip.borrarInventarioGuardado(stack); // lo que llevaba está en el cofre: sin esto se DUPLICARÍA al reconstruirse
                        owner.sendSystemMessage(Component.literal("§c[Alerta]: Cobalt destruido en combate. Inventario asegurado en cofre. Reconstrucción iniciada (~15 min)."));
                        break;
                    }
                }
            }
            this.discard();
        }
    }

    @Override
    public void tick() {
        super.tick();

        if (this.isPerformingDeathAnim) {
            this.setDeltaMovement(0, 0, 0);
            if (deathAnimationTicks > 0) deathAnimationTicks--;
            else if (!this.level().isClientSide()) this.recallToBaseRealDeath();
            return;
        }

        if (this.autoTpCooldown > 0) this.autoTpCooldown--;
        if (this.empCooldownTicks > 0) this.empCooldownTicks--;
        if (this.dronesCooldownTicks > 0) this.dronesCooldownTicks--;
        if (this.dronesRestantesTicks > 0) this.dronesRestantesTicks--;

        if (this.isPerformingEMP) {
            this.empAnimationTicks--;
            if (this.empAnimationTicks <= 0) this.isPerformingEMP = false;
        }

        if (!this.level().isClientSide() && this.level() instanceof ServerLevel serverLevel) {
            if (this.tickCount % 10 == 0 && NoxConfig.activo("carga_chunks")) this.mantenerChunks(serverLevel);

            if (this.tickCount % 5 == 0) {
                Player visto = this.getCobaltOwner();
                if (visto != null) {
                    this.tickDueno = this.tickCount;
                    this.distDueno = this.distanceTo(visto);
                }
            }

            if (this.tickCount % 10 == 0 && this.isFollowingOwner && !this.tareas.ocupado() && !this.aterrizando && !this.huyendo) {
                Player owner = this.getCobaltOwner();
                if (owner != null) {
                    double distSqr = this.distanceToSqr(owner);
                    boolean kiteando = this.enCombate() && distSqr <= 1600.0D;
                    if (distSqr > 9.0D && !kiteando) {
                        double vel = this.navigation instanceof WaterBoundPathNavigation ? 2.5D
                                : (this.isFlying ? NoxCuerpo.velocidadSeguimientoVuelo(Math.sqrt(distSqr), NoxConfig.numero("seguir_vuelo_max", 3.0D)) : 1.3D);
                        boolean hasPath = this.getNavigation().moveTo(owner, vel);

                        if (!hasPath || distSqr > FOLLOW_RANGE_PATHFINDING * FOLLOW_RANGE_PATHFINDING) {
                            this.getMoveControl().setWantedPosition(owner.getX(), owner.getY(), owner.getZ(), vel);
                        }

                        double distAhora = Math.sqrt(distSqr);
                        if (distAhora > 40.0D && (this.distDuenoPrev < 0.0D || NoxMovimiento.sinAcercarse(this.distDuenoPrev, distAhora, 2.0D))) this.rezagoTicks += 10; else this.rezagoTicks = 0;
                        this.distDuenoPrev = distAhora;
                        if ((this.rezagoTicks >= 100 || distAhora > 120.0D) && this.tpCuantico(owner, distAhora > 120.0D ? "quedó muy lejos de ti" : "no lograba alcanzarte")) this.rezagoTicks = 0;

                        // Detector de atascos: Si no se ha movido 2 bloques en 10 segundos
                        if (this.blockPosition().distSqr(this.lastPosForStuckCheck) < 4.0D) {
                            this.stuckTicks += 10; // el motor de seguimiento corre cada 10 ticks
                            if (this.stuckTicks >= 200) {
                                this.tpCuantico(owner, "se atascó en el terreno"); // (si está disponible)
                                this.stuckTicks = 0;
                            }
                        } else {
                            this.stuckTicks = 0;
                            this.lastPosForStuckCheck = this.blockPosition();
                        }
                    } else {
                        this.stuckTicks = 0;
                    }
                }
            }

            if (this.venDestino != null && this.tickCount % 5 == 0) this.avanzarHaciaVen();
            if (this.tickCount % 100 == 50) this.copiarInventarioAlChip();

            if (this.congelado) { // Protocolo OMEGA: ni un movimiento residual
                this.setDeltaMovement(net.minecraft.world.phys.Vec3.ZERO);
                this.getNavigation().stop();
            }
            if (this.miradaTicks > 0) { // mimetismo humano: mirar a los ojos del jugador
                this.miradaTicks--;
                Player mirado = this.getCobaltOwner();
                if (mirado != null && !this.enCombate() && !this.congelado) this.getLookControl().setLookAt(mirado, 30.0F, 30.0F);
            }
            if (this.tickCount % 5 == 0) this.leerComandosDePython();
            this.actualizarDescenso();
            this.tareas.tick(this);
            if (this.tickCount % 2 == 0) this.reflejoCaidaLibre();
            if (this.tickCount % 5 == 0) this.reflejoPeligroTerreno();
            if (this.combateSuprimidoTicks > 0) this.combateSuprimidoTicks--;

            if (this.tickCount % 10 == 0) {
                this.actualizarModoJefe();
                this.supervivenciaVital();
                this.antiAtasco();
                this.empAutomatico();
                this.limpiarObjetivoObsoleto();
                this.soltarObjetivoSiNoAmenaza();
                this.autoAdquirirObjetivo();
                this.evaluarModoMovimiento();
                this.escanearMaquinaria();
                this.actualizarGPS();
                NoxSensorWriter.actualizarSensorTerreno(this.level(), this, this.isFlying);
                NoxSensorWriter.actualizarRadarHostiles(this.level(), this);
                if (NoxConfig.activo("sensor_entidades")) NoxSensorWriter.actualizarEntidades(this.level(), this, this.getCobaltOwner());
                this.mantenerGuardia();
                NoxSensorWriter.escribirEstado(true, false, 0, this, this.getModoMovimiento(), this.datosDeEstado());
            }
        }
    }

    @Override
    public void remove(RemovalReason reason) {
        if (!this.level().isClientSide() && this.level() instanceof ServerLevel serverLevel) {
            NoxChunkLoader.soltar(serverLevel, this.chunksMantenidos);
            this.chunksMantenidos = java.util.List.of();
            if (reason != RemovalReason.CHANGED_DIMENSION) {
                NoxSensorWriter.escribirEstadoChip(this.muerteReal, this.muerteReal ? 15 : 0);
                NoxSensorWriter.limpiarSensores();
            }
            this.tareas.limpiar(this);
        }
        super.remove(reason);
    }

    private String getModoMovimiento() {
        if (this.isFlying) return "fly";
        return this.navigation instanceof WaterBoundPathNavigation ? "swim" : "walk";
    }

    private static final double DIST_ATERRIZAJE = 5.0D;   // <= 5 bloques del jugador: desciende de fly a walk
    private static final double DIST_DESPEGUE = 10.0D;    // > 10 bloques del jugador (siguiéndolo): sube a fly
    private static final int MAX_TICKS_ATERRIZAJE = 200;  // si no toca suelo en 10 s, se apaga el vuelo igualmente

    private boolean aterrizando = false;
    private int ticksAterrizando = 0;
    private int ticksFueraDelAgua = 0;

    boolean enCombate() {
        LivingEntity t = this.getTarget();
        return t != null && t.isAlive();
    }

    @Override
    public void setTarget(LivingEntity objetivo) {
        if (objetivo instanceof Player) return;
        super.setTarget(objetivo);
    }

    @Override
    public boolean canBreatheUnderwater() {
        return true;
    }

    private void limpiarObjetivoObsoleto() {
        LivingEntity t = this.getTarget();
        if (t == null) return;
        Player owner = this.duenoSiSigue();
        boolean lejosDeMi = this.distanceToSqr(t) > 40.0D * 40.0D;
        boolean lejosDelDueno = owner != null && t.distanceToSqr(owner) > RADIO_SOLTAR_DUENO * RADIO_SOLTAR_DUENO;
        if (!t.isAlive() || lejosDeMi || lejosDelDueno) {
            this.setTarget(null);
        }
    }

    private Player duenoSiSigue() {
        return this.isFollowingOwner && !this.tareas.ocupado() ? this.getCobaltOwner() : null;
    }

    private void haltAll() {
        this.tareas.limpiar(this);
        this.retirarDrones(); // OMEGA: también los drones
        this.isFollowingOwner = false;
        this.guardia = null;
        this.huyendo = false;
        this.aterrizando = false;
        this.destinoAterrizaje = null;
        this.setTarget(null);
        this.getNavigation().stop();
        this.getMoveControl().setWantedPosition(this.getX(), this.getY(), this.getZ(), 0.0D);
        this.setDeltaMovement(net.minecraft.world.phys.Vec3.ZERO);
        this.setNoGravity(true);
        this.setNoAi(true);
        this.congelado = true;
        LOGGER.warn("[Cobalt] PROTOCOLO OMEGA: cuerpo congelado en {}.", this.blockPosition());
        this.avisarAlDueno("§c[Cobalt]: PROTOCOLO OMEGA. Detenido por completo; ordena 'resume' para reanudar.");
    }

    private void reanudar() {
        boolean estabaCongelado = this.congelado || this.isNoAi();
        this.congelado = false;
        if (this.isNoAi()) this.setNoAi(false);
        this.setNoGravity(this.isFlying);
        if (estabaCongelado) this.avisarAlDueno("§a[Cobalt]: Reanudo la actividad.");
    }

    private void fijarGuardia(JsonObject t) {
        Integer px = entero(t, "x"), py = entero(t, "y"), pz = entero(t, "z");
        this.guardia = (px != null && py != null && pz != null) ? new BlockPos(px, py, pz) : this.blockPosition();
        Integer r = entero(t, "radius");
        this.guardiaRadio = Math.max(4, Math.min(32, r == null ? 12 : r));
        this.isFollowingOwner = false;
        LOGGER.info("[Cobalt] En guardia en {} (radio {}).", this.guardia, this.guardiaRadio);
    }

    private void mantenerGuardia() {
        if (this.guardia == null || this.congelado || this.tareas.ocupado() || this.enCombate()) return;
        if (this.distanceToSqr(this.guardia.getX() + 0.5D, this.guardia.getY() + 0.5D, this.guardia.getZ() + 0.5D) > 9.0D) {
            CobaltTareas.acercarse(this, this.guardia.getX() + 0.5D, this.guardia.getY() + 0.5D, this.guardia.getZ() + 0.5D, 1.3D);
        }
    }

    private void soltarItems(JsonObject t) {
        String material = texto(t, "material");
        int quedan = Math.max(1, cantidadDe(t, 64));
        int soltados = 0;
        if (!material.isEmpty() && !NoxMinado.esGenerico(material)) {
            for (int i = 0; i < this.inventory.getContainerSize() && quedan > 0; i++) {
                ItemStack pila = this.inventory.getItem(i);
                if (!NoxMinado.itemCoincide(pila, material) || NoxTools.tipoDeHerramienta(pila) != null) continue;
                int n = Math.min(quedan, pila.getCount());
                ItemStack parte = pila.split(n);
                net.minecraft.world.entity.item.ItemEntity suelto = this.spawnAtLocation(parte);
                if (suelto != null) suelto.setPickUpDelay(60);
                quedan -= n;
                soltados += n;
            }
            this.inventory.setChanged();
        }
        JsonObject extra = new JsonObject();
        extra.addProperty("dropped", soltados);
        extra.addProperty("material", material);
        CobaltTareas.feedback("drop_feedback.json", soltados > 0 ? "success" : "failed", null, extra);
    }

    private void usarItem(JsonObject t) {
        String efecto = texto(t, "effect").toLowerCase(Locale.ROOT).replace("minecraft:", "");
        String material = texto(t, "material");
        boolean hecho = false;
        for (int i = 0; i < this.inventory.getContainerSize() && !hecho; i++) {
            ItemStack pila = this.inventory.getItem(i);
            if (pila.isEmpty()) continue;
            boolean pocion = pila.getItem() instanceof net.minecraft.world.item.PotionItem
                    && !(pila.getItem() instanceof net.minecraft.world.item.ThrowablePotionItem);
            boolean leche = pila.is(net.minecraft.world.item.Items.MILK_BUCKET);
            if (!pocion && !leche) continue;
            boolean elegida = !efecto.isEmpty()
                    ? pocion && net.minecraft.world.item.alchemy.PotionUtils.getMobEffects(pila).stream()
                            .anyMatch(e -> net.minecraft.core.registries.BuiltInRegistries.MOB_EFFECT.getKey(e.getEffect()).getPath().equals(efecto))
                    : NoxMinado.itemCoincide(pila, material);
            if (!elegida) continue;
            ItemStack resto = pocion ? new ItemStack(net.minecraft.world.item.Items.GLASS_BOTTLE) : pila.getCraftingRemainingItem();
            pila.getItem().finishUsingItem(pila.copyWithCount(1), this.level(), this); // aplica los efectos (o los quita, si es leche)
            pila.shrink(1);
            if (!resto.isEmpty()) this.inventory.addItem(resto);
            hecho = true;
        }
        this.inventory.setChanged();
        JsonObject extra = new JsonObject();
        extra.addProperty("effect", efecto);
        extra.addProperty("material", material);
        CobaltTareas.feedback("use_feedback.json", hecho ? "success" : "failed", hecho ? null : "no tengo esa poción o leche", extra);
    }

    private LivingEntity objetivoPorId(JsonObject t) {
        Integer id = entero(t, "target_id");
        if (id == null) return null;
        net.minecraft.world.entity.Entity e = this.level().getEntity(id);
        if (!(e instanceof LivingEntity vivo) || !vivo.isAlive() || vivo == this || vivo instanceof Player || NoxSensorWriter.esAliado(vivo)) return null;
        return this.distanceToSqr(vivo) <= 40.0D * 40.0D ? vivo : null;
    }

    private boolean jugadorEnLaTrayectoria(LivingEntity target, double apuntarX, double apuntarZ) {
        double ox = this.getX(), oy = this.getY() + this.getEyeHeight(), oz = this.getZ();
        double ty = target.getY(0.5D);
        double largo = Math.sqrt((apuntarX - ox) * (apuntarX - ox) + (ty - oy) * (ty - oy) + (apuntarZ - oz) * (apuntarZ - oz));
        if (largo <= 2.5D) return false;
        double f = (largo - 2.0D) / largo;
        double bx = ox + (apuntarX - ox) * f, by = oy + (ty - oy) * f, bz = oz + (apuntarZ - oz) * f;
        for (Player p : this.level().players()) {
            if (!p.isAlive() || p.isSpectator() || p.distanceToSqr(this) > 64.0D * 64.0D) continue;
            if (NoxCuerpo.jugadorEnLineaDeTiro(ox, oy, oz, bx, by, bz, p.getX(), p.getY(0.5D), p.getZ(), 1.6D)) return true;
        }
        return false;
    }

    public boolean desplegarDrones() {
        if (!(this.level() instanceof ServerLevel nivel)) return false;
        String estado = null;
        String detalle = null;
        if (!NoxConfig.activo("enjambre_drones")) {
            estado = "disabled";
            detalle = "enjambre_drones=false en cobalt_config.json";
        } else if (this.congelado) {
            estado = "blocked";
            detalle = "Cobalt está congelado (OMEGA)";
        } else if (this.dronesCooldownTicks > 0) {
            estado = "cooldown";
            detalle = "en enfriamiento: " + NoxDrones.segundosRestantes(this.dronesCooldownTicks) + " s";
        }
        if (estado != null) {
            JsonObject extra = new JsonObject();
            extra.addProperty("cooldown_s", NoxDrones.segundosRestantes(this.dronesCooldownTicks));
            CobaltTareas.feedback("drones_feedback.json", estado, detalle, extra);
            if (estado.equals("cooldown")) this.avisarAlDueno("§e[Cobalt]: Enjambre " + detalle + ".");
            return false;
        }

        int cantidad = NoxDrones.cantidad(NoxConfig.numero("drones_cantidad", NoxDrones.CANTIDAD));
        int vida = NoxDrones.duracionTicks(NoxConfig.numero("drones_duracion_s", NoxDrones.DURACION_S));
        float escala = NoxDrones.escalaDano(NoxConfig.numero("drones_dano_pct", NoxDrones.DANO_PCT));
        this.retirarDrones(); // por si quedara alguno de un despliegue anterior
        this.triggerAnim("attackController", "cast_spell");
        for (int i = 0; i < cantidad; i++) {
            CobaltDroneEntity dron = new CobaltDroneEntity(com.example.cobaltbot.registry.ModEntities.DRONE.get(), nivel);
            double[] pos = NoxDrones.posicionEnAnillo(i, cantidad, 0L, 1.6D, 1.2D);
            dron.setPos(this.getX() + pos[0], this.getY() + pos[1], this.getZ() + pos[2]);
            dron.iniciar(this, i, cantidad, vida, escala);
            nivel.addFreshEntity(dron);
        }
        nivel.sendParticles(net.minecraft.core.particles.ParticleTypes.END_ROD, this.getX(), this.getY() + 1.0D, this.getZ(), 30, 0.8D, 0.6D, 0.8D, 0.05D);
        nivel.playSound(null, this.getX(), this.getY(), this.getZ(), net.minecraft.sounds.SoundEvents.BEACON_ACTIVATE, net.minecraft.sounds.SoundSource.NEUTRAL, 1.0F, 1.6F);
        this.dronesRestantesTicks = vida;
        this.dronesCooldownTicks = NoxDrones.cooldownTicks(NoxConfig.numero("drones_cooldown_s", NoxDrones.COOLDOWN_S));
        JsonObject extra = new JsonObject();
        extra.addProperty("drones", cantidad);
        extra.addProperty("duration_s", vida / 20);
        extra.addProperty("cooldown_s", NoxDrones.segundosRestantes(this.dronesCooldownTicks));
        CobaltTareas.feedback("drones_feedback.json", "success", null, extra);
        this.avisarAlDueno("§b[Cobalt]: ¡Enjambre desplegado! " + cantidad + " drones de apoyo durante " + (vida / 20) + " s.");
        return true;
    }

    public void retirarDrones() {
        if (!(this.level() instanceof ServerLevel nivel)) return;
        for (CobaltDroneEntity dron : nivel.getEntitiesOfClass(CobaltDroneEntity.class, this.getBoundingBox().inflate(96.0D),
                d -> this.getUUID().equals(d.getDuenoId()))) {
            dron.retirarse(nivel);
        }
        this.dronesRestantesTicks = 0;
    }

    private Player duenoEnCualquierDimension() {
        Player p = this.getCobaltOwner();
        if (p != null) return p;
        if (this.ownerUUID != null && this.level().getServer() != null) return this.level().getServer().getPlayerList().getPlayer(this.ownerUUID);
        return null;
    }

    private void avanzarHaciaVen() {
        this.venTicks -= 5;
        net.minecraft.world.phys.Vec3 d = this.venDestino;
        if (d == null) return;
        double dist = this.position().distanceTo(d);
        if (this.venTicks <= 0 || dist <= this.venLlegada || this.congelado) {
            this.venDestino = null;
            this.getNavigation().stop();
            if (this.venReanudaSeguimiento && !this.congelado) this.isFollowingOwner = true; // terminó el desvío: vuelve a seguirte
            this.venReanudaSeguimiento = false;
            return;
        }
        if (NoxMovimiento.sinAcercarse(this.venMejorDist, dist, 1.5D)) {
            this.venSinProgreso += 5;
        } else {
            this.venMejorDist = dist;
            this.venSinProgreso = 0;
        }
        if (this.venSinProgreso >= 240 && dist > 6.0D && this.venEsDueno && this.tpCuantico(this.getCobaltOwner(), "no encontró camino hasta ti")) {
            this.venDestino = null;
            return;
        }
        if (dist > DIST_DESPEGUE && !this.isFlying && !(this.navigation instanceof WaterBoundPathNavigation)) this.setModoVuelo(true);
        double vel = this.isFlying ? NoxCuerpo.velocidadSeguimientoVuelo(dist, NoxConfig.numero("seguir_vuelo_max", 3.0D)) : 1.3D;
        double[] meta = NoxMovimiento.puntoIntermedio(this.getX(), this.getY(), this.getZ(), d.x, d.y, d.z, NoxMovimiento.PASO_MAX, this.isFlying);
        if (!this.getNavigation().moveTo(meta[0], meta[1], meta[2], vel)) this.getMoveControl().setWantedPosition(meta[0], meta[1], meta[2], vel);
    }

    private boolean tpCuantico(Player dueno, String motivo) {
        if (this.autoTpCooldown > 0 || dueno == null || dueno.level() != this.level() || !NoxConfig.activo("tp_cuantico")) return false;
        this.teleportTo(dueno.getX(), dueno.getY(), dueno.getZ());
        this.getNavigation().stop();
        this.venDestino = null;
        this.level().playSound(null, this.blockPosition(), net.minecraft.sounds.SoundEvents.ENDERMAN_TELEPORT, net.minecraft.sounds.SoundSource.NEUTRAL, 1.0F, 1.0F);
        this.autoTpCooldown = Math.max(20, (int) (NoxConfig.numero("tp_cuantico_enfriamiento_s", 120.0D) * 20.0D));
        dueno.sendSystemMessage(Component.literal("§e[Sistema]: Cobalt " + motivo + " y utilizó su TP cuántico. (Enfriamiento: " + (this.autoTpCooldown / 20) + " s)"));
        return true;
    }

    private void mantenerChunks(ServerLevel nivel) {
        Player dueno = this.getCobaltOwner();
        double distDueno = dueno != null && dueno.level() == this.level() ? this.distanceTo(dueno) : Double.MAX_VALUE; // sin dueño cerca cuenta como lejos
        boolean trabajoLejos = this.tareas.ocupado() && distDueno > 48.0D;
        int radio = (int) NoxConfig.numero("chunks_alrededor_de_cobalt", 1.0D);
        double dirX = 0.0D, dirZ = 0.0D;
        if (this.venDestino != null) {
            dirX = this.venDestino.x - this.getX();
            dirZ = this.venDestino.z - this.getZ();
        } else if (this.isFollowingOwner && dueno != null && dueno.level() == this.level() && distDueno > 24.0D) {
            dirX = dueno.getX() - this.getX();
            dirZ = dueno.getZ() - this.getZ();
        }
        int adelante = (int) NoxConfig.numero("chunks_adelante", 3.0D);
        int hastaDestino = (int) (Math.sqrt(dirX * dirX + dirZ * dirZ) / 16.0D) - Math.max(0, radio);
        adelante = Math.min(adelante, Math.max(0, hastaDestino));
        this.chunksMantenidos = NoxCarga.chunks(this.blockPosition().getX() >> 4, this.blockPosition().getZ() >> 4, radio, trabajoLejos,
                (int) NoxConfig.numero("chunks_radio_trabajo", 2.0D), dirX, dirZ, adelante, (int) NoxConfig.numero("chunks_max", NoxCarga.TOPE_POR_DEFECTO));
        NoxChunkLoader.mantener(nivel, this.chunksMantenidos);
    }

    private void copiarInventarioAlChip() {
        if (!NoxConfig.activo("copia_inventario_chip") || this.isPerformingDeathAnim || this.ownerUUID == null || this.level().getServer() == null) return;
        int huella = NoxChip.huella(this.inventory);
        if (huella == this.huellaCopiaChip) return;
        net.minecraft.server.level.ServerPlayer dueno = this.level().getServer().getPlayerList().getPlayer(this.ownerUUID);
        if (dueno == null) return;
        ItemStack chip = NoxChip.buscarChip(dueno);
        if (chip.isEmpty() || chip == dueno.getMainHandItem() || chip == dueno.getOffhandItem()) return; // en la mano no: cambiar su NBT reanima el ítem
        NoxChip.guardarInventario(chip, this.inventory);
        this.huellaCopiaChip = huella;
    }

    private void autoAdquirirObjetivo() {
        if (!NoxConfig.activo("autoataque_java") || this.congelado || this.getTarget() != null || this.combateSuprimidoTicks > 0 || this.vidaCriticaActiva) return;
        LivingEntity amenaza = this.buscarAmenazaMasCercana();
        if (amenaza != null) this.setTarget(amenaza);
    }

    private void desbordeCofreMuerte(ServerLevel nivel, BlockPos pos, ItemStack pila) {
        BlockPos arriba = pos.above();
        if (nivel.getBlockState(arriba).isAir()) nivel.setBlock(arriba, net.minecraft.world.level.block.Blocks.CHEST.defaultBlockState(), 3);
        if (nivel.getBlockEntity(arriba) instanceof net.minecraft.world.level.block.entity.ChestBlockEntity segundo) {
            ItemStack resto = pila;
            for (int j = 0; j < segundo.getContainerSize() && !resto.isEmpty(); j++) {
                if (segundo.getItem(j).isEmpty()) {
                    segundo.setItem(j, resto);
                    resto = ItemStack.EMPTY;
                }
            }
            segundo.setChanged();
            if (!resto.isEmpty()) net.minecraft.world.level.block.Block.popResource(nivel, pos, resto);
        } else {
            net.minecraft.world.level.block.Block.popResource(nivel, pos, pila);
        }
    }

    private int tickDueno = -1000;       // tickCount de la última vez que vio al dueño en esta dimensión
    private double distDueno = 1.0E9D;   // y a qué distancia estaba entonces

    public boolean puedeSeguirEntreDimensiones() {
        return this.isAlive() && !this.isPerformingDeathAnim
                && NoxDimension.debeSeguir(this.isFollowingOwner, this.tareas.ocupado(), this.congelado, this.tickCount - this.tickDueno, this.distDueno);
    }

    public boolean cruzarDimension(net.minecraft.server.level.ServerPlayer jugador) {
        if (!(this.level() instanceof ServerLevel origen) || !(jugador.level() instanceof ServerLevel destino) || origen == destino || !this.isAlive()) return false;
        String nombreDestino = destino.dimension().location().getPath();
        NoxDimension.Llegada llegada = NoxDimension.buscarLlegada(destino, jugador.blockPosition());
        if (llegada == null) {
            this.avisarAlDueno("§e[Cobalt]: No encuentro un sitio seguro cerca de ti en " + nombreDestino + ": me quedo aquí. Guárdame en el chip y sácalo allí.");
            return false;
        }
        this.retirarDrones();
        this.getNavigation().stop();
        final net.minecraft.world.phys.Vec3 punto = new net.minecraft.world.phys.Vec3(llegada.x(), llegada.y(), llegada.z());
        final float giro = this.getYRot();
        net.minecraftforge.common.util.ITeleporter destinoSeguro = new net.minecraftforge.common.util.ITeleporter() {
            @Override
            public net.minecraft.world.level.portal.PortalInfo getPortalInfo(net.minecraft.world.entity.Entity entidad, ServerLevel mundo,
                                                                             java.util.function.Function<ServerLevel, net.minecraft.world.level.portal.PortalInfo> porDefecto) {
                return new net.minecraft.world.level.portal.PortalInfo(punto, net.minecraft.world.phys.Vec3.ZERO, giro, 0.0F); // NO se busca un portal: ese sitio exacto
            }
        };
        net.minecraft.world.entity.Entity nuevo = this.changeDimension(destino, destinoSeguro);
        if (nuevo instanceof CobaltEntity copia) {
            copia.recibirTrasCruce(this.inventory, llegada.vuelo(), nombreDestino);
            return true;
        }
        return false;
    }

    private void recibirTrasCruce(net.minecraft.world.SimpleContainer origen, boolean vuelo, String nombreDimension) {
        for (int i = 0; i < this.inventory.getContainerSize() && i < origen.getContainerSize(); i++) {
            this.inventory.setItem(i, origen.getItem(i).copy());
        }
        this.inventory.setChanged();
        this.setPortalCooldown(); // aunque quedara cerca de un portal, no lo cruza de nuevo durante 15 s
        this.fallDistance = 0.0F;
        this.setDeltaMovement(net.minecraft.world.phys.Vec3.ZERO);
        this.getNavigation().stop();
        this.isFollowingOwner = true;
        this.tickDueno = this.tickCount;
        this.distDueno = 0.0D;
        if (vuelo) {
            this.setModoVuelo(true);
        } else {
            this.setModoVuelo(false);
            this.setNoGravity(false); // el NBT trae 'NoGravity' de cuando volaba en la otra dimensión
        }
        this.avisarAlDueno("§b[Cobalt]: Te sigo a " + nombreDimension + (vuelo ? " (aquí no hay suelo firme: me quedo en vuelo)." : "."));
    }

    private void datosDelServidor(JsonObject extra) {
        if (!NoxConfig.activo("monitor_servidor")) return;
        try { // dentro del tick: nada de lo que falle aquí debe tumbar el juego
            net.minecraft.server.MinecraftServer servidor = this.level().getServer();
            if (servidor != null) {
                double mspt = servidor.getAverageTickTime();
                extra.addProperty("server_mspt", Math.round(mspt * 10.0D) / 10.0D);
                extra.addProperty("server_tps", Math.round(NoxServidor.tpsDesdeMspt(mspt) * 10.0D) / 10.0D);
                extra.addProperty("players_online", servidor.getPlayerCount());
            }
            int sueltos = 0, viejos = 0;
            for (net.minecraft.world.entity.item.ItemEntity e : this.level().getEntitiesOfClass(net.minecraft.world.entity.item.ItemEntity.class,
                    this.getBoundingBox().inflate(32.0D), it -> it.isAlive())) {
                sueltos++;
                if (e.getAge() >= 2400) viejos++;
            }
            extra.addProperty("items_near", sueltos);
            extra.addProperty("items_old_near", viejos);
        } catch (Exception e) {
            LOGGER.warn("[Cobalt] No se pudo leer el estado del servidor: {}", e.toString());
        }
    }

    private void escribirLibro(JsonObject t) {
        if (!NoxConfig.activo("bardo_libros")) {
            CobaltTareas.feedback("book_feedback.json", "disabled", "bardo_libros=false en cobalt_config.json", null);
            return;
        }
        List<String> paginas = new ArrayList<>();
        JsonElement el = t.get("pages");
        if (el != null && el.isJsonArray()) {
            for (JsonElement p : el.getAsJsonArray()) {
                if (p.isJsonPrimitive()) paginas.add(p.getAsString());
            }
        }
        NoxServidor.Libro libro = NoxServidor.limitarLibro(texto(t, "title"), paginas);
        if (libro.paginas().isEmpty()) {
            CobaltTareas.feedback("book_feedback.json", "failed", "el libro no tiene páginas", null);
            return;
        }
        ItemStack item = new ItemStack(net.minecraft.world.item.Items.WRITTEN_BOOK);
        net.minecraft.nbt.CompoundTag tag = item.getOrCreateTag();
        tag.putString("title", libro.titulo());
        tag.putString("author", "Cobalt");
        net.minecraft.nbt.ListTag hojas = new net.minecraft.nbt.ListTag();
        for (String pagina : libro.paginas()) {
            hojas.add(net.minecraft.nbt.StringTag.valueOf(net.minecraft.network.chat.Component.Serializer.toJson(net.minecraft.network.chat.Component.literal(pagina))));
        }
        tag.put("pages", hojas);
        tag.putBoolean("resolved", true);
        ItemStack sobrante = this.inventory.addItem(item);
        if (!sobrante.isEmpty()) this.spawnAtLocation(sobrante); // sin hueco: cae al suelo
        this.inventory.setChanged();
        JsonObject extra = new JsonObject();
        extra.addProperty("title", libro.titulo());
        extra.addProperty("pages", libro.paginas().size());
        CobaltTareas.feedback("book_feedback.json", "success", null, extra);
        if (!texto(t, "give").equalsIgnoreCase("false") && sobrante.isEmpty()) {
            JsonObject soltar = new JsonObject();
            soltar.addProperty("material", "written_book");
            soltar.addProperty("amount", 1);
            this.soltarItems(soltar);
        }
        this.avisarAlDueno("§a[Cobalt]: Escribí el libro '" + libro.titulo() + "' (" + libro.paginas().size() + " página(s)).");
    }

    private void feedbackTerreno(String estado, String detalle, JsonObject extra) {
        CobaltTareas.feedback("terraform_feedback.json", estado, detalle, extra);
    }

    private void planificarAplanado(JsonObject t) {
        if (!(this.level() instanceof ServerLevel nivel)) return;
        if (!NoxConfig.activo("aplanado_terreno")) {
            this.feedbackTerreno("disabled", "aplanado_terreno=false en cobalt_config.json", null);
            return;
        }
        Integer x1 = entero(t, "x1"), z1 = entero(t, "z1"), x2 = entero(t, "x2"), z2 = entero(t, "z2"), y = entero(t, "y");
        if (x1 == null || z1 == null || x2 == null || z2 == null || y == null) {
            this.feedbackTerreno("failed", "faltan coordenadas x1,z1,x2,z2,y", null);
            return;
        }
        long columnas = (Math.abs((long) x2 - x1) + 1L) * (Math.abs((long) z2 - z1) + 1L);
        if (columnas > NoxTerreno.MAX_COLUMNAS_ESCANEO) {
            this.feedbackTerreno("failed", "la zona es demasiado grande (máximo " + NoxTerreno.MAX_COLUMNAS_ESCANEO + " columnas, 64 x 64)", null);
            return;
        }
        NoxTerreno.PlanAplanado plan = NoxTerreno.planAplanado(nivel, x1, z1, x2, z2, y, NoxMinado.leerBase(), NoxMinado.RADIO_BASE_LIMPIEZA,
                nivel::hasChunkAt, NoxTerreno.MAX_BLOQUES_OBRA);
        if (plan.cavar().isEmpty() && plan.rellenar().isEmpty()) {
            JsonObject extra = new JsonObject();
            extra.addProperty("blocked_columns", plan.columnasBloqueadas());
            extra.addProperty("columns", plan.columnas());
            this.feedbackTerreno("success", plan.columnasBloqueadas() == plan.columnas() ? "todas las columnas están bloqueadas (agua, construcciones, base o chunks sin cargar)" : "ya está a nivel", extra);
            this.avisarAlDueno("§e[Cobalt]: No hay nada que aplanar (" + plan.columnasBloqueadas() + " de " + plan.columnas() + " columnas bloqueadas).");
            return;
        }
        this.avisarAlDueno("§b[Cobalt]: Aplanado a y=" + y + ": cavar " + plan.cavar().size() + ", rellenar " + plan.rellenar().size()
                + (plan.columnasBloqueadas() > 0 ? ", " + plan.columnasBloqueadas() + " columna(s) sin tocar" : "") + (plan.truncado() ? " (recortado al tope de " + NoxTerreno.MAX_BLOQUES_OBRA + ")" : "") + ".");
        this.tareas.encolar(new CobaltTareas.TareaTerraformar("flatten", plan.cavar(), plan.rellenar(), false, false, plan.columnasBloqueadas()));
    }

    private void planificarRelleno(JsonObject t) {
        if (!(this.level() instanceof ServerLevel nivel)) return;
        if (!NoxConfig.activo("relleno_fluidos")) {
            this.feedbackTerreno("disabled", "relleno_fluidos=false en cobalt_config.json", null);
            return;
        }
        Integer x = entero(t, "x"), y = entero(t, "y"), z = entero(t, "z"), r = entero(t, "radius");
        BlockPos centro = (x != null && y != null && z != null) ? new BlockPos(x, y, z) : this.blockPosition();
        int radio = Math.max(2, Math.min(16, r == null ? 8 : r));
        boolean lava = !texto(t, "fluid").equalsIgnoreCase("water");
        List<BlockPos> celdas = NoxTerreno.buscarFluido(nivel, centro, radio, lava, NoxTerreno.MAX_BLOQUES_OBRA);
        if (celdas.isEmpty()) {
            this.feedbackTerreno("success", "no hay " + (lava ? "lava" : "agua") + " en " + radio + " bloques", null);
            this.avisarAlDueno("§e[Cobalt]: No veo " + (lava ? "lava" : "agua") + " en " + radio + " bloques.");
            return;
        }
        this.avisarAlDueno("§b[Cobalt]: Relleno " + celdas.size() + " celda(s) de " + (lava ? "lava" : "agua") + " con ripio, de arriba abajo.");
        this.tareas.encolar(new CobaltTareas.TareaTerraformar(lava ? "fill_lava" : "fill_water", new ArrayList<>(), celdas, true, lava, 0));
    }

    private void escanearRelieve(JsonObject t) {
        if (!(this.level() instanceof ServerLevel nivel)) return;
        String motivo = null;
        Integer x1 = entero(t, "x1"), z1 = entero(t, "z1"), x2 = entero(t, "x2"), z2 = entero(t, "z2");
        if (!NoxConfig.activo("escaneo_terreno")) motivo = "escaneo_terreno=false en cobalt_config.json";
        else if (x1 == null || z1 == null || x2 == null || z2 == null) motivo = "faltan coordenadas x1,z1,x2,z2";
        else if ((Math.abs((long) x2 - x1) + 1L) * (Math.abs((long) z2 - z1) + 1L) > NoxTerreno.MAX_COLUMNAS_ESCANEO) motivo = "zona demasiado grande (máx. 64 x 64)";
        if (motivo != null) {
            NoxSensorWriter.escribirAtomico("terrain_map.json", "{\"status\":\"failed\",\"detalle\":\"" + motivo + "\"}");
            return;
        }
        int xa = Math.min(x1, x2), xb = Math.max(x1, x2), za = Math.min(z1, z2), zb = Math.max(z1, z2);
        Integer ymaxP = entero(t, "ymax"), yminP = entero(t, "ymin");
        int yMax = Math.min(nivel.getMaxBuildHeight() - 1, ymaxP != null ? ymaxP : this.getBlockY() + 40);
        int yMin = Math.max(nivel.getMinBuildHeight(), yminP != null ? yminP : this.getBlockY() - 40);
        com.google.gson.JsonArray filasY = new com.google.gson.JsonArray(), filasT = new com.google.gson.JsonArray();
        int sinCargar = 0;
        for (int z = za; z <= zb; z++) {
            com.google.gson.JsonArray fy = new com.google.gson.JsonArray(), ft = new com.google.gson.JsonArray();
            for (int x = xa; x <= xb; x++) {
                if (!nivel.hasChunkAt(new BlockPos(x, yMin, z))) {
                    fy.add(yMin - 1);
                    ft.add(NoxTerreno.DESCONOCIDO);
                    sinCargar++;
                    continue;
                }
                int[] sup = NoxTerreno.superficie(nivel, x, z, yMax, yMin);
                fy.add(sup[0]);
                ft.add(sup[1]);
            }
            filasY.add(fy);
            filasT.add(ft);
        }
        JsonObject raiz = new JsonObject();
        raiz.addProperty("status", "success");
        raiz.addProperty("bot_id", NoxCuerpo.BOT_ID);
        raiz.addProperty("updated_ms", System.currentTimeMillis());
        raiz.addProperty("x1", xa);
        raiz.addProperty("z1", za);
        raiz.addProperty("x2", xb);
        raiz.addProperty("z2", zb);
        raiz.addProperty("y_max", yMax);
        raiz.addProperty("y_min", yMin);
        raiz.addProperty("unloaded", sinCargar);
        raiz.add("y", filasY);
        raiz.add("t", filasT);
        NoxSensorWriter.escribirAtomico("terrain_map.json", raiz.toString());
    }

    private void escanearBloques(JsonObject t) {
        if (!(this.level() instanceof ServerLevel nivel)) return;
        Integer x1 = entero(t, "x1"), y1 = entero(t, "y1"), z1 = entero(t, "z1"), x2 = entero(t, "x2"), y2 = entero(t, "y2"), z2 = entero(t, "z2");
        String motivo = null;
        if (!NoxConfig.activo("escaneo_terreno")) motivo = "escaneo_terreno=false en cobalt_config.json";
        else if (x1 == null || y1 == null || z1 == null || x2 == null || y2 == null || z2 == null) motivo = "faltan coordenadas x1,y1,z1,x2,y2,z2";
        else if (NoxMinado.volumenCaja(x1, y1, z1, x2, y2, z2) > NoxTerreno.MAX_VOLUMEN_BLOQUES) motivo = "caja demasiado grande (máx. " + NoxTerreno.MAX_VOLUMEN_BLOQUES + " celdas)";
        if (motivo != null) {
            NoxSensorWriter.escribirAtomico("scan_blocks.json", "{\"status\":\"failed\",\"detalle\":\"" + motivo + "\"}");
            return;
        }
        int xa = Math.min(x1, x2), ya = Math.min(y1, y2), za = Math.min(z1, z2);
        int w = Math.abs(x2 - x1) + 1, h = Math.abs(y2 - y1) + 1, l = Math.abs(z2 - z1) + 1;
        java.util.Map<String, Integer> paleta = new java.util.LinkedHashMap<>();
        com.google.gson.JsonArray bloques = new com.google.gson.JsonArray();
        int sinCargar = 0;
        boolean truncado = false;
        for (int dy = 0; dy < h && !truncado; dy++) {
            for (int dz = 0; dz < l && !truncado; dz++) {
                for (int dx = 0; dx < w; dx++) {
                    BlockPos p = new BlockPos(xa + dx, ya + dy, za + dz);
                    if (!nivel.hasChunkAt(p)) {
                        sinCargar++;
                        continue;
                    }
                    BlockState e = nivel.getBlockState(p);
                    if (e.isAir() || !NoxTerreno.debeRevelar(nivel, p, e)) continue; // las menas enterradas no se delatan
                    if (bloques.size() >= 8000) {
                        truncado = true;
                        break;
                    }
                    int idx = paleta.computeIfAbsent(NoxTerreno.idDe(e), k -> paleta.size());
                    com.google.gson.JsonArray b = new com.google.gson.JsonArray();
                    b.add(dx);
                    b.add(dy);
                    b.add(dz);
                    b.add(idx);
                    bloques.add(b);
                }
            }
        }
        com.google.gson.JsonArray jsonPaleta = new com.google.gson.JsonArray();
        paleta.keySet().forEach(jsonPaleta::add);
        JsonObject raiz = new JsonObject();
        raiz.addProperty("status", "success");
        raiz.addProperty("bot_id", NoxCuerpo.BOT_ID);
        raiz.addProperty("updated_ms", System.currentTimeMillis());
        raiz.addProperty("x0", xa);
        raiz.addProperty("y0", ya);
        raiz.addProperty("z0", za);
        raiz.addProperty("w", w);
        raiz.addProperty("h", h);
        raiz.addProperty("l", l);
        raiz.addProperty("truncated", truncado);
        raiz.addProperty("unloaded", sinCargar);
        raiz.add("palette", jsonPaleta);
        raiz.add("blocks", bloques);
        NoxSensorWriter.escribirAtomico("scan_blocks.json", raiz.toString());
    }

    private void evaluarModoMovimiento() {
        Player owner = this.getCobaltOwner();
        boolean duenoNadando = owner != null && owner.isInWater();
        boolean sumergido = this.isEyeInFluid(FluidTags.WATER);
        boolean nadando = this.navigation instanceof WaterBoundPathNavigation;

        if (owner != null && this.isFollowingOwner && (this.isFlying || nadando) && NoxConfig.activo("nado_automatico") && owner.isInWater()
                && owner.getFluidHeight(FluidTags.WATER) > owner.getBbHeight() * 0.5D && this.distanceToSqr(owner) < 1600.0D) {
            this.ticksFueraDelAgua = 0;
            this.aterrizando = false;
            if (!nadando) this.setModoNado(true);
            return;
        }

        if (sumergido || (this.isInWater() && duenoNadando && !this.onGround())) {
            this.ticksFueraDelAgua = 0;
            this.aterrizando = false;
            if (!nadando) this.setModoNado(true); // también apaga el vuelo
            return;
        }
        if (nadando) {
            if (++this.ticksFueraDelAgua >= 2) { // 1 s fuera del agua => volver a tierra
                this.ticksFueraDelAgua = 0;
                this.setModoNado(false);
            }
            return;
        }
        this.ticksFueraDelAgua = 0;

        if (this.modoJefe) {
            this.aterrizando = false;
            return;
        }
        if (this.enCombate()) {
            this.aterrizando = false;
            return;
        }
        if (this.destinoAterrizaje != null) {
            this.gestionarAterrizajeSeguro();
            return;
        }
        if (owner == null) return;
        double dist = this.distanceTo(owner);

        if (this.isFlying) {
            if (this.aterrizando && !this.aterrizajeForzado) {
                int suelo = this.sueloBajo();
                if (dist > DIST_ATERRIZAJE + 3.0D || suelo == SUELO_NO || (suelo == SUELO_AGUA && !duenoNadando)) {
                    this.aterrizando = false; // el jugador se alejó o debajo hay lava/vacío
                }
            } else if (dist <= DIST_ATERRIZAJE) {
                int suelo = this.sueloBajo();
                if (suelo == SUELO_FIRME) {
                    this.aterrizando = true;
                    this.ticksAterrizando = 0;
                    this.getNavigation().stop();
                } else if (suelo == SUELO_AGUA && duenoNadando) {
                    this.setModoNado(true);
                }
            }
        } else if (this.isFollowingOwner && dist > DIST_DESPEGUE) {
            this.setModoVuelo(true);
        }
    }

    private void reflejoCaidaLibre() {
        if (this.isFlying || this.onGround() || this.isInWater() || this.isInLava()
                || this.navigation instanceof WaterBoundPathNavigation) return;
        double vy = this.getDeltaMovement().y;
        if (vy > NoxSensorWriter.VEL_CAIDA_LIBRE) return; // barato: la mayoría de los ticks termina aquí

        int caida = NoxSensorWriter.distanciaAlSuelo(this.level(), this.blockPosition(), 32);
        boolean sueloNoSeguro = this.sueloBajo() == SUELO_NO;
        if (!NoxSensorWriter.debeVolarPorCaida(vy, caida, sueloNoSeguro)) return;

        LOGGER.info("[Cobalt] Caída libre (vy={}, suelo a {} bloques, suelo no seguro={}): vuelo de emergencia.",
                String.format(Locale.ROOT, "%.2f", vy), caida, sueloNoSeguro);
        this.aterrizando = false;
        this.setModoVuelo(true);
        Vec3 v = this.getDeltaMovement();
        this.setDeltaMovement(v.x * 0.3D, 0.1D, v.z * 0.3D); // setModoVuelo solo suma +0.5: no basta contra una caída a -1.5
    }

    private boolean vidaCriticaActiva = false;
    private boolean avisadoFalloMundo = false; // H3: el fallo al leer hora/clima se avisa una sola vez en el log
    private boolean modsExportados = false;    // H6: mods.json se escribe una vez por entidad
    private boolean avisadoFalloJugador = false;
    private boolean huyendo = false;
    private int huidaMinimaTicks = 0;
    private net.minecraft.world.phys.Vec3 venDestino = null; // 'ven': ir a un punto UNA vez (no es 'seguir')
    private int venTicks = 0;
    private double venLlegada = 2.5D;
    private int huellaCopiaChip = -1;
    private int ticksSinCombate = 0;
    private int comerEnfriamiento = 0;
    private BlockPos destinoAterrizaje = null;
    private int ticksDestinoAterrizaje = 0;
    private boolean aterrizajeForzado = false;
    private int vueloTemporalTicks = 0;
    private int retrocesoTicks = 0;   // Bloque C: retirada forzada tras un pulso EMP
    private boolean modoJefe = false; // Bloque D: protocolo de jefe activo
    // Bloque F: primitivas de control (las decide Python)
    private boolean congelado = false;
    private boolean jefeExtremo = false;   // jefe con >= 300 de vida
    private BlockPos guardia = null;       // punto que Cobalt defiende sin seguir al jugador
    private double guardiaRadio = 12.0D;
    private int miradaTicks = 0;           // mira al jugador unos instantes
    private String nombreJefe = null;
    private long ultimoRegistroJefeMs = 0L;

    private final CobaltTareas tareas = new CobaltTareas();

    boolean tareasPausadas() {
        return this.enCombate() || this.vidaCriticaActiva || this.modoJefe;
    }
    private final NoxSupervivencia.AtascoDetector atasco = new NoxSupervivencia.AtascoDetector();

    void avisarAlDueno(String mensaje) {
        if (this.level().getServer() != null) {
            this.level().getServer().getPlayerList().broadcastSystemMessage(Component.literal(mensaje), false);
        }
    }

    private void supervivenciaVital() {
        float vida = this.getHealth();
        float vidaMax = this.getMaxHealth();
        boolean huidaActiva = NoxConfig.activo("huida_vida_critica");

        if (this.enCombate()) this.ticksSinCombate = 0; else this.ticksSinCombate += 10;
        if (this.comerEnfriamiento > 0) this.comerEnfriamiento -= 10;
        if (this.huidaMinimaTicks > 0) this.huidaMinimaTicks -= 10;

        if (!this.vidaCriticaActiva && NoxSupervivencia.vidaCritica(vida, vidaMax, NoxConfig.numero("vida_critica_pct", 30))) {
            this.vidaCriticaActiva = true;
            this.huidaMinimaTicks = huidaActiva ? (int) (NoxConfig.numero("huida_minima_s", 4.0D) * 20.0D) : 0;
            if (huidaActiva) {
                this.setTarget(null);
                this.avisarAlDueno("§c[Cobalt]: ¡Vida crítica (" + Math.round(100.0F * vida / vidaMax) + "%)! Dejo de atacar y me repliego.");
            }
        } else if (this.vidaCriticaActiva && NoxSupervivencia.puedeVolverAlCombate(vida, vidaMax, NoxConfig.numero("vida_recuperada_pct", 50), this.huidaMinimaTicks)) {
            this.vidaCriticaActiva = false;
            this.huyendo = false;
            this.avisarAlDueno("§a[Cobalt]: Vida recuperada. Retomo el combate.");
        }

        if (this.vidaCriticaActiva) {
            if (NoxConfig.activo("autocuracion") && this.comerEnfriamiento <= 0) this.comerParaCurarse();
            if (huidaActiva) this.huirDeAmenazas(); else this.huyendo = false;
        } else {
            this.huyendo = false;
        }

        if (NoxConfig.activo("regeneracion_pasiva") && vida < vidaMax && this.ticksSinCombate >= 100) {
            this.heal(0.5F);
        }
    }

    private void comerParaCurarse() {
        int hueco = NoxSupervivencia.mejorComida(this.inventory, this);
        if (hueco < 0) return;

        ItemStack pila = this.inventory.getItem(hueco);
        net.minecraft.world.food.FoodProperties comida = pila.getItem().getFoodProperties(pila, this);
        if (comida == null) return;

        this.heal(NoxSupervivencia.curacionPorNutricion(comida.getNutrition()));
        for (com.mojang.datafixers.util.Pair<net.minecraft.world.effect.MobEffectInstance, Float> efecto : comida.getEffects()) {
            if (this.random.nextFloat() < efecto.getSecond()) {
                this.addEffect(new net.minecraft.world.effect.MobEffectInstance(efecto.getFirst()));
            }
        }
        String nombre = pila.getHoverName().getString();
        pila.shrink(1);
        this.inventory.setChanged();
        this.comerEnfriamiento = 40; // 2 s entre bocados
        this.level().playSound(null, this.blockPosition(), net.minecraft.sounds.SoundEvents.GENERIC_EAT,
                net.minecraft.sounds.SoundSource.NEUTRAL, 1.0F, 1.0F);
        this.avisarAlDueno("§a[Cobalt]: Consumí " + nombre + " para recuperarme (vida " + Math.round(this.getHealth()) + "/" + Math.round(this.getMaxHealth()) + ").");
    }

    private void huirDeAmenazas() {
        List<LivingEntity> cercanos = NoxSensorWriter.hostilesEnRadio(this.level(), this, 16.0D);
        if (cercanos.isEmpty()) {
            this.huyendo = false;
            return;
        }
        LivingEntity peor = cercanos.get(0);
        for (LivingEntity e : cercanos) {
            if (NoxSensorWriter.esJefe(e)) {
                this.registrarEncuentroJefe(e, "huida"); // huir de un jefe también es una lección
                break;
            }
        }
        this.huyendo = true;
        this.aterrizando = false;
        if (!this.isFlying && !(this.navigation instanceof WaterBoundPathNavigation)) this.setModoVuelo(true);
        double[] punto = NoxSupervivencia.puntoDeHuida(this.getX(), this.getZ(), peor.getX(), peor.getZ(), 14.0D);
        double y = Math.max(this.getY(), peor.getY()) + 4.0D;
        if (!this.getNavigation().moveTo(punto[0], y, punto[1], 1.6D)) {
            this.getMoveControl().setWantedPosition(punto[0], y, punto[1], 1.6D);
        }
    }

    private void reflejoPeligroTerreno() {
        boolean reflejo = NoxConfig.activo("reflejo_lava_java");
        boolean aterrizaje = NoxConfig.activo("aterrizaje_seguro");
        if (!reflejo && !aterrizaje) return;

        boolean peligro = this.isInLava() || this.isOnFire()
                || NoxSensorWriter.clasificarTerreno(this.level(), this.blockPosition()) == NoxSensorWriter.TERRENO_PELIGRO;
        if (!peligro) return;

        if (reflejo && !this.isFlying) {
            LOGGER.info("[Cobalt] Peligro de lava/fuego en {}: vuelo de emergencia (Java).", this.blockPosition());
            this.aterrizando = false;
            this.setModoVuelo(true);
        }
        if (aterrizaje && this.destinoAterrizaje == null && !this.enCombate()) {
            BlockPos sitio = NoxSupervivencia.buscarSitioSeguro(this.level(), this.blockPosition(), 10);
            if (sitio != null) {
                LOGGER.info("[Cobalt] Sitio seguro para aterrizar: {}", sitio);
                this.destinoAterrizaje = sitio;
                this.ticksDestinoAterrizaje = 0;
            }
        }
    }

    private void gestionarAterrizajeSeguro() {
        if (this.enCombate() || !this.isFlying || !NoxConfig.activo("aterrizaje_seguro") || ++this.ticksDestinoAterrizaje > 30) {
            this.destinoAterrizaje = null;
            return;
        }
        double dx = this.destinoAterrizaje.getX() + 0.5D - this.getX();
        double dz = this.destinoAterrizaje.getZ() + 0.5D - this.getZ();
        if (Math.sqrt(dx * dx + dz * dz) < 1.5D) {
            this.aterrizando = true;
            this.aterrizajeForzado = true;
            this.ticksAterrizando = 0;
            this.getNavigation().stop();
            this.destinoAterrizaje = null;
            return;
        }
        double y = this.destinoAterrizaje.getY() + 2.0D;
        if (!this.getNavigation().moveTo(this.destinoAterrizaje.getX() + 0.5D, y, this.destinoAterrizaje.getZ() + 0.5D, 1.4D)) {
            this.getMoveControl().setWantedPosition(this.destinoAterrizaje.getX() + 0.5D, y, this.destinoAterrizaje.getZ() + 0.5D, 1.4D);
        }
    }

    private void antiAtasco() {
        if (!NoxConfig.activo("anti_atasco") || this.aterrizando || this.navigation instanceof WaterBoundPathNavigation) {
            this.atasco.reiniciar();
            return;
        }
        if (this.vueloTemporalTicks > 0) {
            this.vueloTemporalTicks -= 10;
            if (this.vueloTemporalTicks <= 0 && this.isFlying && !this.enCombate() && this.sueloBajo() == SUELO_FIRME) {
                this.aterrizando = true; // fin del vuelo temporal: baja suave
                this.ticksAterrizando = 0;
            }
        }
        boolean quiereMoverse = !this.getNavigation().isDone() || this.getMoveControl().hasWanted();
        switch (this.atasco.actualizar(this.getX(), this.getY(), this.getZ(), quiereMoverse, 10)) {
            case SALTAR -> {
                LOGGER.info("[Cobalt] Atascado 3 s en {}: salto.", this.blockPosition());
                if (this.isFlying) {
                    this.setDeltaMovement(this.getDeltaMovement().x, 0.4D, this.getDeltaMovement().z);
                } else {
                    this.getJumpControl().jump();
                }
            }
            case VOLAR -> {
                LOGGER.info("[Cobalt] Atascado 6 s en {}: vuelo temporal.", this.blockPosition());
                if (!this.isFlying) {
                    this.setModoVuelo(true);
                    this.vueloTemporalTicks = 80;
                } else {
                    this.setDeltaMovement(this.getDeltaMovement().x, 0.4D, this.getDeltaMovement().z);
                }
            }
            default -> { }
        }
    }

    private void actualizarModoJefe() {
        LivingEntity jefe = null;
        if (NoxConfig.activo("modo_jefe")) {
            for (LivingEntity e : NoxSensorWriter.hostilesEnRadio(this.level(), this, NoxSensorWriter.RADIO_RADAR)) {
                if (NoxSensorWriter.esJefe(e)) {
                    jefe = e;
                    break;
                }
            }
        }
        boolean activo = jefe != null;
        if (activo && !this.modoJefe) {
            String nombre = jefe.getName().getString();
            LOGGER.info("[Cobalt] Protocolo de jefe ACTIVADO ante {}.", nombre);
            this.avisarAlDueno("§6[Cobalt]: ¡JEFE detectado: " + nombre + "! Protocolo de jefe: vuelo total, distancia máxima y solo plasma.");
        } else if (!activo && this.modoJefe) {
            LOGGER.info("[Cobalt] Protocolo de jefe desactivado.");
            this.avisarAlDueno("§a[Cobalt]: Jefe fuera de alcance o derrotado. Vuelvo al combate normal.");
        }
        this.modoJefe = activo;
        this.nombreJefe = activo ? jefe.getName().getString() : null;
        boolean extremo = activo && NoxConfig.activo("jefe_fase_extrema") && NoxCuerpo.esMegaJefe(jefe.getMaxHealth());
        if (extremo && !this.jefeExtremo) {
            LOGGER.info("[Cobalt] FASE EXTREMA ante {} ({} de vida).", this.nombreJefe, jefe.getMaxHealth());
            this.avisarAlDueno("§4[Cobalt]: ¡MEGA-JEFE (" + Math.round(jefe.getMaxHealth()) + " de vida)! Fase Extrema: distancia máxima.");
        }
        this.jefeExtremo = extremo;

        if (activo) {
            this.aterrizando = false;
            if (!this.isFlying && !(this.navigation instanceof WaterBoundPathNavigation)) {
                this.setModoVuelo(true);
            }
        }
    }

    private void registrarEncuentroJefe(LivingEntity enemigo, String motivo) {
        if (!NoxConfig.activo("registro_derrotas_jefe")) return;
        long ahora = System.currentTimeMillis();
        if ("huida".equals(motivo)) {
            if (!NoxJefes.puedeRegistrar(ahora, this.ultimoRegistroJefeMs, 120_000L)) return;
            this.ultimoRegistroJefeMs = ahora;
        }
        String id = net.minecraft.core.registries.BuiltInRegistries.ENTITY_TYPE.getKey(enemigo.getType()).toString();
        NoxSensorWriter.escribirAtomico("derrota_jefe.json",
                NoxJefes.jsonEncuentro(enemigo.getName().getString(), id, NoxSensorWriter.esJefe(enemigo), motivo, ahora));
    }

    private void actualizarDescenso() {
        if (!this.aterrizando) return;

        if (!this.isFlying || this.enCombate() || this.isInWater()) {
            this.aterrizando = false;
            this.aterrizajeForzado = false;
            return;
        }
        if (this.onGround() || ++this.ticksAterrizando > MAX_TICKS_ATERRIZAJE) {
            this.aterrizando = false;
            this.aterrizajeForzado = false;
            this.setModoVuelo(false);
            return;
        }
        Vec3 v = this.getDeltaMovement();
        this.setDeltaMovement(v.x, -0.12D, v.z); // ~2.4 bloques/s
    }

    private static final int SUELO_NO = 0;     // vacío, lava o fuego cerca, o demasiado alto
    private static final int SUELO_FIRME = 1;  // suelo sólido seguro
    private static final int SUELO_AGUA = 2;   // agua

    private int sueloBajo() {
        BlockPos base = this.blockPosition();
        for (int i = 1; i <= 24; i++) {
            BlockPos abajo = base.below(i);
            BlockState estado = this.level().getBlockState(abajo);
            if (estado.isAir()) continue;
            if (!estado.getFluidState().isEmpty()) {
                return estado.getFluidState().is(FluidTags.WATER) ? SUELO_AGUA : SUELO_NO; // lava: jamás
            }
            if (!estado.blocksMotion()) continue;                // hierba, antorchas...: sigue bajando
            boolean peligro = NoxSensorWriter.clasificarTerreno(this.level(), abajo.above()) == NoxSensorWriter.TERRENO_PELIGRO;
            return peligro ? SUELO_NO : SUELO_FIRME;
        }
        return SUELO_NO; // vacío o demasiado alto: mejor seguir volando
    }

    private void leerComandosDePython() {
        if (this.level().isClientSide()) return;

        File file = com.example.cobaltbot.util.NoxRutas.archivo("command.json");
        if (!file.exists()) return;

        List<JsonObject> tareas = new ArrayList<>();
        try {
            String content = Files.readString(file.toPath(), StandardCharsets.UTF_8);
            if (content.isBlank()) {
                throw new IllegalStateException("command.json vacío (escritura en curso)");
            }

            if (NoxCuerpo.contieneHaltAll(content)) {
                try { Files.deleteIfExists(file.toPath()); } catch (Exception ignored) {}
                this.haltAll();
                return;
            }
            JsonElement raiz = JsonParser.parseString(content);
            if (raiz.isJsonArray()) {
                for (JsonElement el : raiz.getAsJsonArray()) {
                    if (el.isJsonObject()) tareas.add(el.getAsJsonObject());
                }
            } else if (raiz.isJsonObject()) {
                tareas.add(raiz.getAsJsonObject());
            } else {
                throw new IllegalStateException("command.json no es un objeto ni un array JSON");
            }
        } catch (Exception e) {
            if (++this.lecturasCorruptas >= 10) {
                LOGGER.warn("[Cobalt] command.json ilegible, se descarta: {}", e.toString());
                file.delete();
                this.lecturasCorruptas = 0;
            }
            return;
        }

        this.lecturasCorruptas = 0;
        if (!file.delete()) {
            try {
                Files.writeString(file.toPath(), "", StandardCharsets.UTF_8);
            } catch (Exception ignored) {}
        }

        try {
            this.ejecutarTareas(tareas);
        } catch (Exception e) {
            LOGGER.error("[Cobalt] Error ejecutando órdenes de Python", e);
        }
    }

    private static final Set<String> ACCIONES_DE_COMBATE = Set.of("defend", "attack", "shoot_plasma", "special_power");

    private void ejecutarTareas(List<JsonObject> tareas) {
        tareas.removeIf(t -> !NoxCuerpo.aceptaOrden(texto(t, "bot_id"))); // solo las órdenes de este cuerpo
        if (this.congelado) { // Protocolo OMEGA: solo 'resume' y 'halt_all' se obedecen
            tareas.removeIf(t -> {
                String a = texto(t, "action").toLowerCase(Locale.ROOT);
                return !a.equals("resume") && !a.equals("halt_all");
            });
        }
        for (JsonObject t : tareas) {
            try {
                this.ejecutarAccion(t);
            } catch (Exception e) {
                LOGGER.error("[Cobalt] Fallo en la acción '{}'", texto(t, "action"), e);
            }
            this.enviarChatDeTarea(t);
        }

        boolean enCombate = this.enCombate();
        boolean fly = false, swim = false, walk = false;
        for (JsonObject t : tareas) {
            String accion = texto(t, "action").toLowerCase(Locale.ROOT);
            if (!enCombate && ACCIONES_DE_COMBATE.contains(accion)) continue;
            String modo = texto(t, "movement_mode").toLowerCase(Locale.ROOT);
            if (modo.equals("fly")) fly = true;
            else if (modo.equals("swim")) swim = true;
            else if (modo.equals("walk")) walk = true;
        }
        if (fly) {
            this.setModoVuelo(true);
        } else if (swim) {
            this.setModoNado(true);
        } else if (walk) {
            this.setModoVuelo(false);
            this.setModoNado(false);
        }
    }

    private void priorizarLlegada() {
        this.setTarget(null);
        this.combateSuprimidoTicks = 160; // 8 s
    }

    private static List<String> listaMateriales(JsonObject t) {
        String m = texto(t, "material");
        List<String> lista = new ArrayList<>();
        if (m.isEmpty() || NoxMinado.esGenerico(m)) return lista;
        for (String p : m.split(",")) if (!p.isBlank()) lista.add(p.trim());
        return lista;
    }

    private void ejecutarAccion(JsonObject t) {
        String accion = texto(t, "action").toLowerCase(Locale.ROOT);

        switch (accion) {
            case "stop" -> {
                this.venDestino = null;
                this.venReanudaSeguimiento = false;
                this.isFollowingOwner = false;
                this.guardia = null;
                this.tareas.limpiar(this);
                this.getNavigation().stop();
                this.setTarget(null);
            }
            case "follow" -> {
                this.venDestino = null;
                this.venReanudaSeguimiento = false;
                this.isFollowingOwner = true;
                this.guardia = null;
                this.priorizarLlegada();
            }
            case "ven" -> {
                this.isFollowingOwner = false;
                this.venReanudaSeguimiento = false;
                this.guardia = null;
                this.priorizarLlegada();
                Player owner = this.getCobaltOwner();
                if (owner != null) {
                    this.tareas.limpiar(this); // 'ven' es "ven YA": interrumpe lo que hacía
                    this.venDestino = owner.position();
                    this.venTicks = NoxMovimiento.ticksParaLlegar(this.distanceTo(owner));
                    this.venLlegada = 2.5D;
                    this.venEsDueno = true;
                    this.venMejorDist = 1.0E9D;
                    this.venSinProgreso = 0;
                    boolean hasPath = this.getNavigation().moveTo(owner, 1.3D);
                    if (!hasPath) {
                        this.getMoveControl().setWantedPosition(owner.getX(), owner.getY(), owner.getZ(), 1.3D);
                    }
                }
            }
            case "defend", "attack" -> {
                LivingEntity objetivo = this.objetivoPorId(t); // Python puede señalar QUÉ enemigo atacar
                if (objetivo != null) this.objetivoExplicitoHasta = this.tickCount + 200; // y se respeta 10 s aunque haya tarea en curso
                if (objetivo == null) objetivo = this.buscarAmenazaMasCercana();
                if (objetivo != null) this.setTarget(objetivo);
            }
            case "flee" -> this.setTarget(null);
            case "special_power" -> {
                if (!this.modoJefe) this.ejecutarPulsoEMP(); // protocolo de jefe: uso exclusivo de plasma
            }
            case "shoot_plasma" -> {
                LivingEntity objetivo = this.objetivoPorId(t);
                if (objetivo != null) this.setTarget(objetivo);
                if (objetivo == null) objetivo = this.getTarget();
                if (objetivo == null || !objetivo.isAlive()) {
                    objetivo = this.buscarAmenazaMasCercana();
                    if (objetivo != null) this.setTarget(objetivo);
                }
                if (objetivo != null && this.hasLineOfSight(objetivo)) this.dispararPlasma(objetivo);
            }
            case "harvest" -> { // cosecha los cultivos maduros de alrededor y los replanta
                if (!NoxConfig.activo("granjeo_autonomo")) {
                    CobaltTareas.feedback("harvest_feedback.json", "disabled", "granjeo_autonomo=false en cobalt_config.json", null);
                } else {
                    Integer radioCosecha = entero(t, "radius");
                    this.tareas.encolar(new CobaltTareas.TareaCosechar(radioCosecha == null ? 12 : radioCosecha));
                }
            }
            case "flatten_area" -> this.planificarAplanado(t);
            case "fill_fluid" -> this.planificarRelleno(t);
            case "scan_terrain" -> this.escanearRelieve(t);
            case "scan_blocks" -> this.escanearBloques(t);
            case "pickup" -> {
                Integer radio = entero(t, "radius");
                Integer edad = entero(t, "min_age_ticks"); // limpieza por lag: solo lo que lleva ese tiempo en el suelo
                this.tareas.encolar(new CobaltTareas.TareaRecoger(entero(t, "entity_id"), texto(t, "material"), radio == null ? 12 : radio, edad == null ? 0 : edad));
            }
            case "write_book" -> this.escribirLibro(t);
            case "tend_furnaces" -> {
                if (!NoxConfig.activo("atender_hornos")) {
                    CobaltTareas.feedback("furnace_feedback.json", "disabled", "atender_hornos=false en cobalt_config.json", null);
                } else {
                    Integer radioHornos = entero(t, "radius");
                    this.tareas.encolar(new CobaltTareas.TareaHornos(radioHornos == null ? 10 : radioHornos));
                }
            }
            case "look_at" -> { // mirada al jugador (3 s por defecto, máx. 10)
                Integer seg = entero(t, "seconds");
                this.miradaTicks = 20 * Math.max(1, Math.min(10, seg == null ? 3 : seg));
            }
            case "hop" -> { // saltito espontáneo (solo caminando y en el suelo)
                if (this.onGround() && !this.isFlying && !this.enCombate() && !this.congelado) this.getJumpControl().jump();
            }
            case "deploy_drones" -> this.desplegarDrones();
            case "recall_drones" -> this.retirarDrones();
            case "halt_all" -> this.haltAll();
            case "resume" -> this.reanudar();
            case "flush" -> {
                this.tareas.limpiar(this);
                this.getNavigation().stop();
            }
            case "sneak" -> this.setShiftKeyDown(!texto(t, "on").equalsIgnoreCase("false"));
            case "stand_ground" -> this.fijarGuardia(t);
            case "drop" -> this.soltarItems(t);
            case "use_item" -> this.usarItem(t);
            case "store" -> {
                if (NoxConfig.activo("logistica_base")) {
                    this.tareas.encolar(new CobaltTareas.TareaGuardar(null, listaMateriales(t)));
                } else {
                    this.depositarEnCofreCercano(); // comportamiento anterior
                }
            }
            case "store_at" -> {
                Integer px = entero(t, "x");
                Integer py = entero(t, "y");
                Integer pz = entero(t, "z");
                if (!NoxConfig.activo("logistica_base")) {
                    LOGGER.warn("[Cobalt] store_at desactivado en cobalt_config.json (logistica_base=false)");
                } else if (px != null && py != null && pz != null) {
                    this.tareas.encolar(new CobaltTareas.TareaGuardar(new BlockPos(px, py, pz), listaMateriales(t)));
                } else {
                    LOGGER.warn("[Cobalt] store_at sin coordenadas x/y/z v\u00e1lidas: {}", t);
                }
            }
            case "clear_area" -> {
                Integer x1 = entero(t, "x1"), y1 = entero(t, "y1"), z1 = entero(t, "z1");
                Integer x2 = entero(t, "x2"), y2 = entero(t, "y2"), z2 = entero(t, "z2");
                if (!NoxConfig.activo("construccion_limpieza")) {
                    CobaltTareas.feedback("clear_feedback.json", "disabled", "construccion_limpieza=false en cobalt_config.json", null);
                } else if (x1 == null || y1 == null || z1 == null || x2 == null || y2 == null || z2 == null) {
                    CobaltTareas.feedback("clear_feedback.json", "failed", "faltan coordenadas x1,y1,z1,x2,y2,z2", null);
                } else {
                    this.tareas.encolar(new CobaltTareas.TareaLimpiar(new BlockPos(x1, y1, z1), new BlockPos(x2, y2, z2)));
                }
            }
            case "restock" -> {
                if (NoxConfig.activo("logistica_base")) {
                    this.tareas.encolar(new CobaltTareas.TareaRestock(texto(t, "material"), cantidadDe(t, 16)));
                } else {
                    CobaltTareas.feedback("logistica_feedback.json", "disabled", "logistica_base=false en cobalt_config.json", null);
                    if (this.accionesAvisadas.add("restock")) LOGGER.warn("[Cobalt] restock desactivado en cobalt_config.json (logistica_base=false)");
                }
            }
            case "mine" -> {
                if (NoxConfig.activo("mineria_real")) {
                    Integer minutos = entero(t, "minutes"); // plazo opcional en minutos
                    this.tareas.encolar(new CobaltTareas.TareaMinar(texto(t, "material"), cantidadDe(t, 16), minutos == null ? 0 : minutos));
                } else {
                    this.escribirFeedbackHerramienta("pickaxe"); // comportamiento anterior: solo comprobar que hay pico
                }
            }
            case "give" -> {
                if (NoxConfig.activo("logistica_base")) {
                    this.tareas.encolar(new CobaltTareas.TareaDar(texto(t, "material"), cantidadDe(t, 0)));
                } else if (this.accionesAvisadas.add("give")) {
                    LOGGER.warn("[Cobalt] give desactivado en cobalt_config.json (logistica_base=false)");
                }
            }
            case "craft" -> {
                if (NoxConfig.activo("crafteo")) {
                    this.tareas.encolar(new CobaltTareas.TareaCraftear(texto(t, "material"), cantidadDe(t, 1)));
                } else {
                    CobaltTareas.feedback("craft_feedback.json", "disabled", "crafteo=false en cobalt_config.json", null);
                }
            }
            case "fish" -> {
                if (NoxConfig.activo("pesca")) {
                    Integer radioPesca = entero(t, "radius"), minutosPesca = entero(t, "minutes");
                    this.tareas.encolar(new CobaltTareas.TareaPescar(cantidadDe(t, 8), radioPesca == null ? 16 : radioPesca, minutosPesca == null ? 0 : minutosPesca));
                } else {
                    CobaltTareas.feedback("fish_feedback.json", "disabled", "pesca=false en cobalt_config.json", null);
                }
            }
            case "chop_wood" -> {
                this.escribirFeedbackHerramienta("axe"); // si hay un hacha en un cofre cercano, la toma
                if (NoxConfig.activo("tala")) {
                    Integer radioTala = entero(t, "radius");
                    this.tareas.encolar(new CobaltTareas.TareaTalar(radioTala == null ? 16 : radioTala, cantidadDe(t, 16)));
                }
            }
            case "place_block" -> this.colocarBloqueDesdeOrden(t);
            case "place_blocks" -> this.colocarLoteDesdeOrden(t);
            case "go_to" -> {
                Integer px = entero(t, "x");
                Integer py = entero(t, "y");
                Integer pz = entero(t, "z");
                if (px != null && py != null && pz != null) {
                    boolean teSeguia = this.isFollowingOwner;
                    this.isFollowingOwner = false;
                    this.priorizarLlegada();
                    this.venDestino = new net.minecraft.world.phys.Vec3(px + 0.5D, py, pz + 0.5D);
                    this.venReanudaSeguimiento = teSeguia && this.position().distanceTo(this.venDestino) < 24.0D;
                    this.venTicks = NoxMovimiento.ticksParaLlegar(this.position().distanceTo(this.venDestino));
                    this.venLlegada = 1.5D;
                    this.venEsDueno = false;
                    this.venMejorDist = 1.0E9D;
                    this.venSinProgreso = 0;
                    if (!this.getNavigation().moveTo(px + 0.5D, py, pz + 0.5D, 1.3D)) this.getMoveControl().setWantedPosition(px + 0.5D, py, pz + 0.5D, 1.3D);
                } else {
                    LOGGER.warn("[Cobalt] go_to sin coordenadas x/y/z válidas: {}", t);
                }
            }
            default -> {
                if (!ACCIONES_SIN_EFECTO.contains(accion) && this.accionesAvisadas.add(accion)) {
                    LOGGER.warn("[Cobalt] Acción '{}' recibida de Python pero NO implementada en Java", accion);
                }
            }
        }
    }

    private void enviarChatDeTarea(JsonObject t) {
        String mensaje = texto(t, "chat_message");
        if (mensaje.isEmpty() || this.level().getServer() == null) return;

        this.level().getServer().getPlayerList().broadcastSystemMessage(
                Component.literal("§3Cobalt: §f" + mensaje), false
        );
        try {
            com.example.cobaltbot.client.gui.NoxInteractScreen.registrarMensajeDiscoLocal("Cobalt", mensaje);
        } catch (Exception | NoClassDefFoundError ignored) {
            // Clase de cliente: en un servidor dedicado no existe
        }
    }

    private void escribirFeedbackHerramienta(String herramienta) {
        boolean exito = this.equiparHerramientaDeCofre(herramienta);
        NoxSensorWriter.escribirAtomico("tool_feedback.json",
                "{\"status\": \"" + (exito ? "success" : "failed") + "\", \"tool\": \"" + herramienta + "\"}");
    }

    private void colocarLoteDesdeOrden(JsonObject t) {
        NoxLotes.Parseado lote = NoxLotes.parsear(t.get("blocks"));
        List<NoxLotes.Fallo> fallos = new ArrayList<>(lote.fallos());
        int colocados = 0;
        boolean conEstados = NoxConfig.activo("schematics_estados", false);
        boolean primero = true;
        for (NoxLotes.Bloque b : lote.bloques()) {
            boolean ok = false;
            String motivo = "error";
            try {
                if (primero) {
                    this.getLookControl().setLookAt(b.x() + 0.5D, b.y() + 0.5D, b.z() + 0.5D, 30.0F, 30.0F);
                    primero = false;
                }
                ok = this.colocarBloque(new BlockPos(b.x(), b.y(), b.z()), b.block(), conEstados ? b.state() : "", false);
                if (!ok && !this.motivoFalloColocacion.isEmpty()) motivo = this.motivoFalloColocacion;
            } catch (Exception e) { // p. ej. un id de bloque mal escrito: solo ese bloque falla
                motivo = "bloque_invalido";
                LOGGER.warn("[Cobalt] place_blocks: el bloque {} ('{}') falló: {}", b.i(), b.block(), e.toString());
            }
            if (ok) colocados++;
            else fallos.add(new NoxLotes.Fallo(b.i(), motivo));
        }
        fallos.sort(java.util.Comparator.comparingInt(NoxLotes.Fallo::i));
        NoxSensorWriter.escribirAtomico("build_feedback.json", NoxLotes.resumen(lote.total(), colocados, fallos, lote.ignorados()));
    }

    private void colocarBloqueDesdeOrden(JsonObject t) {
        boolean exito = false;
        try {
            Integer px = entero(t, "x");
            Integer py = entero(t, "y");
            Integer pz = entero(t, "z");
            String blockId = texto(t, "block");
            if (blockId.isEmpty()) blockId = "minecraft:stone";

            String propiedades = NoxConfig.activo("schematics_estados", false) ? texto(t, "state") : "";
            if (px != null && py != null && pz != null) {
                this.getLookControl().setLookAt(px + 0.5D, py + 0.5D, pz + 0.5D, 30.0F, 30.0F);
                exito = this.colocarBloqueEnMundo(new BlockPos(px, py, pz), blockId, propiedades);
            }
        } catch (Exception e) {
            LOGGER.warn("[Cobalt] place_block falló: {}", e.toString());
        }
        NoxSensorWriter.escribirAtomico("build_feedback.json",
                "{\"status\": \"" + (exito ? "success" : "failed") + "\""
                        + (exito || this.motivoFalloColocacion.isEmpty() ? "" : ", \"reason\": \"" + this.motivoFalloColocacion + "\"") + "}");
    }

    private LivingEntity buscarAmenazaMasCercana() {
        if (this.combateSuprimidoTicks > 0) return null;
        if (this.vidaCriticaActiva && NoxConfig.activo("huida_vida_critica")) return null; // en vida crítica no se ataca
        Player owner = this.duenoSiSigue();
        boolean selectiva = this.defensaSelectiva();
        List<LivingEntity> amenazas = new ArrayList<>();
        for (LivingEntity e : NoxSensorWriter.hostilesEnRadio(this.level(), this, NoxSensorWriter.RADIO_COMBATE)) {
            if (selectiva && !this.amenazaReal(e)) continue; // con una tarea en curso no se persigue a quien no ataca
            if (owner != null && e.distanceToSqr(owner) > RADIO_DEFENSA_DUENO * RADIO_DEFENSA_DUENO) continue;
            if (this.guardia != null && e.distanceToSqr(this.guardia.getX() + 0.5D, this.guardia.getY() + 0.5D, this.guardia.getZ() + 0.5D)
                    > this.guardiaRadio * this.guardiaRadio) continue; // en guardia solo se combate dentro del radio
            if (NoxSensorWriter.esAmenaza(this, e)) amenazas.add(e);
        }
        if (amenazas.isEmpty()) return null;
        if (!NoxConfig.activo("priorizacion_objetivos")) return amenazas.get(0); // el más cercano (la lista llega ordenada)

        List<NoxCombate.Candidato> candidatos = new ArrayList<>();
        for (LivingEntity e : amenazas) candidatos.add(this.comoCandidato(e));
        return amenazas.get(NoxCombate.elegir(candidatos));
    }

    private boolean defensaSelectiva() {
        return this.tareas.ocupado() && NoxConfig.activo("defensa_selectiva_en_tareas");
    }

    private boolean amenazaReal(LivingEntity e) {
        if (e instanceof net.minecraft.world.entity.Mob mob) {
            LivingEntity objetivo = mob.getTarget();
            if (objetivo == this || objetivo instanceof Player) return true;
        }
        if (this.distanceToSqr(e) <= 25.0D) return true;
        if (NoxSensorWriter.esJefe(e) || this.getLastHurtByMob() == e) return true;
        return atacaADistancia(e) && this.hasLineOfSight(e);
    }

    private void soltarObjetivoSiNoAmenaza() {
        LivingEntity t = this.getTarget();
        if (t == null || !this.defensaSelectiva() || this.tickCount < this.objetivoExplicitoHasta) return;
        if (!this.amenazaReal(t)) this.setTarget(null);
    }

    private static boolean atacaADistancia(LivingEntity e) {
        return e instanceof RangedAttackMob
                || e instanceof net.minecraft.world.entity.monster.CrossbowAttackMob
                || e instanceof net.minecraft.world.entity.monster.Blaze
                || e instanceof net.minecraft.world.entity.monster.Ghast
                || e instanceof net.minecraft.world.entity.monster.Shulker
                || e instanceof net.minecraft.world.entity.monster.Guardian;
    }

    private NoxCombate.Candidato comoCandidato(LivingEntity e) {
        double vidaPct = e.getMaxHealth() > 0 ? 100.0D * e.getHealth() / e.getMaxHealth() : 100.0D;
        return new NoxCombate.Candidato(this.distanceTo(e), atacaADistancia(e), vidaPct,
                e instanceof net.minecraft.world.entity.monster.Creeper,
                e instanceof net.minecraft.world.entity.monster.Witch,
                NoxSensorWriter.esJefe(e));
    }

    private boolean evaluarCuerpoACuerpo(LivingEntity objetivo) {
        if (!NoxConfig.activo("melee_condicional") || this.modoJefe) return false;
        int cercanos = NoxSensorWriter.hostilesEnRadio(this.level(), this, 12.0D).size();
        double vidaPropia = 100.0D * this.getHealth() / this.getMaxHealth();
        return NoxCombate.debeCuerpoACuerpo(objetivo.getMaxHealth(), objetivo.getHealth(), cercanos, vidaPropia,
                objetivo instanceof net.minecraft.world.entity.monster.Creeper, NoxSensorWriter.esJefe(objetivo));
    }

    private void empAutomatico() {
        if (!NoxConfig.activo("emp_automatico") || this.empCooldownTicks > 0 || this.modoJefe) return;
        if (NoxSensorWriter.hostilesEnRadio(this.level(), this, 5.0D).size() >= 4) {
            this.ejecutarPulsoEMP();
        }
    }

    private static String texto(JsonObject t, String clave) {
        JsonElement el = t.get(clave);
        return (el != null && el.isJsonPrimitive()) ? el.getAsString().trim() : "";
    }

    private static int cantidadDe(JsonObject t, int defecto) {
        Integer n = entero(t, "amount");
        return n == null ? defecto : n;
    }

    private static Integer entero(JsonObject t, String clave) {
        try {
            JsonElement el = t.get(clave);
            if (el != null && el.isJsonPrimitive()) return (int) Math.floor(el.getAsDouble());
        } catch (Exception ignored) {}
        return null;
    }

    public void setModoVuelo(boolean activarVuelo) {
        if (this.isFlying == activarVuelo && (this.navigation instanceof FlyingPathNavigation) == activarVuelo) return;

        this.isFlying = activarVuelo;
        this.entityData.set(IS_FLYING, activarVuelo);
        this.setNoGravity(activarVuelo);
        this.fallDistance = 0.0F;

        if (this.navigation != null) { this.navigation.stop(); }

        if (activarVuelo) {
            this.moveControl = new CobaltFlyMoveControl(this);
            FlyingPathNavigation navVoladora = new FlyingPathNavigation(this, this.level());
            navVoladora.setCanOpenDoors(false);
            navVoladora.setCanFloat(true);
            navVoladora.setCanPassDoors(true);
            this.navigation = navVoladora;
            this.setDeltaMovement(this.getDeltaMovement().add(0.0, 0.5, 0.0));
        } else {
            this.moveControl = new MoveControl(this);
            GroundPathNavigation navTerrestre = new GroundPathNavigation(this, this.level());
            navTerrestre.setCanOpenDoors(true);
            navTerrestre.setCanFloat(true);
            this.navigation = navTerrestre;
        }
    }

    public void setModoNado(boolean activarNado) {
        boolean currentIsSwim = this.navigation instanceof WaterBoundPathNavigation;
        if (currentIsSwim == activarNado) return;

        this.isFlying = false;
        this.entityData.set(IS_FLYING, false);
        this.setNoGravity(false);
        this.fallDistance = 0.0F;

        if (this.navigation != null) { this.navigation.stop(); }

        if (activarNado) {
            this.moveControl = new CobaltSwimMoveControl(this); // el MoveControl base no sabe moverse en vertical
            this.navigation = new WaterBoundPathNavigation(this, this.level());
        } else {
            this.moveControl = new MoveControl(this);
            GroundPathNavigation navTerrestre = new GroundPathNavigation(this, this.level());
            navTerrestre.setCanOpenDoors(true);
            navTerrestre.setCanFloat(true);
            this.navigation = navTerrestre;
        }
    }

    @Override
    public boolean causeFallDamage(float fallDistance, float multiplier, DamageSource source) {
        if (this.isFlying) return false;
        if (fallDistance > 3.0F) {
            this.fallDistance = 0.0F;
            return false;
        }
        return super.causeFallDamage(fallDistance, multiplier, source);
    }

    @Override
    protected void checkFallDamage(double y, boolean onGround, BlockState state, BlockPos pos) {
        if (this.isFlying) return;
        super.checkFallDamage(y, onGround, state, pos);
    }

    private void escanearMaquinaria() {
        if (this.level().isClientSide()) return;

        BlockPos currentPos = this.blockPosition();
        StringBuilder reporteTecnico = new StringBuilder("Reporte Técnico de Maquinaria Cercana: ");
        boolean detectoMaquinas = false;

        for (int x = -3; x <= 3; x++) {
            for (int y = -2; y <= 2; y++) {
                for (int z = -3; z <= 3; z++) {
                    BlockPos checkPos = currentPos.offset(x, y, z);
                    net.minecraft.world.level.block.entity.BlockEntity be = this.level().getBlockEntity(checkPos);

                    if (be != null) {
                        String blockName = this.level().getBlockState(checkPos).getBlock().getName().getString();

                        be.getCapability(net.minecraftforge.common.capabilities.ForgeCapabilities.ENERGY, null).ifPresent(energy -> {
                            int stored = energy.getEnergyStored();
                            int max = energy.getMaxEnergyStored();
                            reporteTecnico.append(String.format("[%s - Energía: %d/%d FE] ", blockName, stored, max));
                        });

                        be.getCapability(net.minecraftforge.common.capabilities.ForgeCapabilities.FLUID_HANDLER, null).ifPresent(fluid -> {
                            if (fluid.getTanks() > 0) {
                                int stored = fluid.getFluidInTank(0).getAmount();
                                int max = fluid.getTankCapacity(0);
                                String fluidName = fluid.getFluidInTank(0).getTranslationKey().replace("fluid.", "").replace("block.", "");
                                if (stored > 0) {
                                    reporteTecnico.append(String.format("[%s - Tanque (%s): %d/%d mB] ", blockName, fluidName, stored, max));
                                }
                            }
                        });
                        detectoMaquinas = true;
                    }
                }
            }
        }

        String resultadoFinal = detectoMaquinas ? reporteTecnico.toString() : "No hay maquinaria, reactores ni tanques en el radio cercano.";

        NoxSensorWriter.escribirAtomico("tech_sensor.json", resultadoFinal);
    }

    public void depositarEnCofreCercano() {
        if (this.level().isClientSide()) return;

        BlockPos currentPos = this.blockPosition();
        boolean transferenciaExitosa = false;

        for (int x = -4; x <= 4; x++) {
            for (int y = -3; y <= 3; y++) {
                for (int z = -4; z <= 4; z++) {
                    BlockPos checkPos = currentPos.offset(x, y, z);
                    net.minecraft.world.level.block.entity.BlockEntity be = this.level().getBlockEntity(checkPos);

                    if (be != null) {
                        var handlerOpt = be.getCapability(net.minecraftforge.common.capabilities.ForgeCapabilities.ITEM_HANDLER, null);

                        if (handlerOpt.isPresent()) {
                            var chestHandler = handlerOpt.resolve().get();

                            for (int slot = 0; slot < this.inventory.getContainerSize(); slot++) {
                                ItemStack stackEnCobalt = this.inventory.getItem(slot);

                                if (!stackEnCobalt.isEmpty()) {
                                    ItemStack sobrante = net.minecraftforge.items.ItemHandlerHelper.insertItem(chestHandler, stackEnCobalt, false);
                                    this.inventory.setItem(slot, sobrante);
                                    transferenciaExitosa = true;
                                }
                            }
                        }
                    }
                }
            }
        }

        try {
            File dir = com.example.cobaltbot.util.NoxRutas.dir();
            if (!dir.exists()) dir.mkdirs();
            try (FileWriter writer = new FileWriter(new File(dir, "inventory_sensor.json"))) {
                writer.write(transferenciaExitosa ? "Inventario depositado con éxito en el contenedor cercano." : "No se encontró ningún contenedor válido al alcance.");
            }
        } catch (Exception e) {}
    }

    public boolean equiparHerramientaDeCofre(String tipoHerramienta) {
        if (this.level().isClientSide()) return false;

        for (int i = 0; i < this.inventory.getContainerSize(); i++) {
            ItemStack stack = this.inventory.getItem(i);
            if (!stack.isEmpty()) {
                if (NoxTools.esHerramienta(stack, tipoHerramienta)) { // antes contains(): "axe" coincidía con "pickaxe"
                    return true;
                }
            }
        }

        BlockPos currentPos = this.blockPosition();

        for (int x = -4; x <= 4; x++) {
            for (int y = -3; y <= 3; y++) {
                for (int z = -4; z <= 4; z++) {
                    BlockPos checkPos = currentPos.offset(x, y, z);
                    net.minecraft.world.level.block.entity.BlockEntity be = this.level().getBlockEntity(checkPos);

                    if (be != null) {
                        var handlerOpt = be.getCapability(net.minecraftforge.common.capabilities.ForgeCapabilities.ITEM_HANDLER, null);

                        if (handlerOpt.isPresent()) {
                            var chestHandler = handlerOpt.resolve().get();

                            for (int i = 0; i < chestHandler.getSlots(); i++) {
                                ItemStack stackEnCofre = chestHandler.getStackInSlot(i);

                                if (!stackEnCofre.isEmpty()) {
                                    if (NoxTools.esHerramienta(stackEnCofre, tipoHerramienta)) {
                                        ItemStack herramientaExtraida = chestHandler.extractItem(i, 1, false);

                                        if (!herramientaExtraida.isEmpty()) {
                                            this.inventory.addItem(herramientaExtraida);
                                            this.level().getServer().getPlayerList().broadcastSystemMessage(
                                                    Component.literal("§b[Logística]: Cobalt ha extraído un/a " + tipoHerramienta + " del cofre cercano para iniciar la tarea."), false
                                            );
                                            return true;
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        return false;
    }

    public boolean fundirMaterialDeEmergencia(String tipoMineral, net.minecraft.world.item.Item itemResultado) {
        if (this.level().isClientSide()) return false;

        boolean tieneMineral = false;
        boolean tieneCombustible = false;
        int slotMineral = -1;
        int slotCombustible = -1;

        for (int i = 0; i < this.inventory.getContainerSize(); i++) {
            ItemStack stack = this.inventory.getItem(i);
            String nombreItem = stack.getItem().getDescriptionId().toLowerCase();

            if (!tieneMineral && NoxMinado.esMineralDeFundicion(stack, tipoMineral)) {
                tieneMineral = true;
                slotMineral = i;
            }
            if (!tieneCombustible && (nombreItem.contains("coal") || nombreItem.contains("charcoal"))) {
                tieneCombustible = true;
                slotCombustible = i;
            }
        }

        if (tieneMineral && tieneCombustible) {
            this.inventory.removeItem(slotMineral, 1);
            this.inventory.removeItem(slotCombustible, 1);

            ItemStack lingoteFinal = new ItemStack(itemResultado, 1);
            this.inventory.addItem(lingoteFinal);

            this.level().getServer().getPlayerList().broadcastSystemMessage(
                    Component.literal("§6[Autosuficiencia]: Cobalt ha fundido un mineral en su horno interno para fabricar herramientas de emergencia."), false
            );
            return true;
        }

        return false;
    }

    public boolean extraerMaterialDeCofre(String idMaterialBuscado, int cantidadNecesaria) {
        if (this.level().isClientSide()) return false;

        BlockPos currentPos = this.blockPosition();
        boolean extraccionExitosa = false;

        for (int x = -4; x <= 4; x++) {
            for (int y = -3; y <= 3; y++) {
                for (int z = -4; z <= 4; z++) {
                    BlockPos checkPos = currentPos.offset(x, y, z);
                    net.minecraft.world.level.block.entity.BlockEntity be = this.level().getBlockEntity(checkPos);

                    if (be != null && NoxMinado.esAlmacen(net.minecraft.core.registries.BuiltInRegistries.BLOCK.getKey(be.getBlockState().getBlock()).getPath())) {
                        var handlerOpt = be.getCapability(net.minecraftforge.common.capabilities.ForgeCapabilities.ITEM_HANDLER, null);

                        if (handlerOpt.isPresent()) {
                            var chestHandler = handlerOpt.resolve().get();

                            for (int i = 0; i < chestHandler.getSlots(); i++) {
                                ItemStack stackEnCofre = chestHandler.getStackInSlot(i);

                                if (!stackEnCofre.isEmpty() && NoxMinado.itemCoincide(stackEnCofre, idMaterialBuscado)) {
                                    int aExtraer = Math.min(cantidadNecesaria, stackEnCofre.getCount());
                                    ItemStack extraido = chestHandler.extractItem(i, aExtraer, false);

                                    if (!extraido.isEmpty()) {
                                        this.inventory.addItem(extraido);
                                        cantidadNecesaria -= extraido.getCount();
                                        extraccionExitosa = true;

                                        if (cantidadNecesaria <= 0) {
                                            return true;
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        return extraccionExitosa;
    }

    private String motivoFalloColocacion = "";

    public boolean colocarBloqueEnMundo(BlockPos targetPos, String blockIdString) {
        return this.colocarBloqueEnMundo(targetPos, blockIdString, "");
    }

    public boolean colocarBloqueEnMundo(BlockPos targetPos, String blockIdString, String propiedades) {
        return this.colocarBloque(targetPos, blockIdString, propiedades, true);
    }

    private boolean colocarBloque(BlockPos targetPos, String blockIdString, String propiedades, boolean sonido) {
        this.motivoFalloColocacion = "";
        if (this.level().isClientSide()) return false;

        int slotConItem = -1;
        ItemStack stackParaColocar = ItemStack.EMPTY;
        String idItemDelBloque = NoxConfig.activo("schematics_estados", false)
                ? NoxBloques.idDe(NoxBloques.itemDe(NoxBloques.bloqueDe(blockIdString))) : "";

        for (int i = 0; i < this.inventory.getContainerSize(); i++) {
            ItemStack stack = this.inventory.getItem(i);
            if (!stack.isEmpty()) {
                String registryName = net.minecraft.core.registries.BuiltInRegistries.ITEM.getKey(stack.getItem()).toString();
                if (registryName.equals(blockIdString) || stack.getItem().getDescriptionId().contains(blockIdString)
                        || (!idItemDelBloque.isEmpty() && registryName.equals(idItemDelBloque))) {
                    slotConItem = i;
                    stackParaColocar = stack;
                    break;
                }
            }
        }

        if (slotConItem == -1 || stackParaColocar.isEmpty()) {
            this.motivoFalloColocacion = "no_material";
            return false;
        }

        net.minecraft.world.level.block.Block block = net.minecraft.core.registries.BuiltInRegistries.BLOCK.get(
                new net.minecraft.resources.ResourceLocation(blockIdString)
        );

        if (block == net.minecraft.world.level.block.Blocks.AIR) {
            this.motivoFalloColocacion = "bloque_invalido";
            return false;
        }

        if (this.level().getBlockState(targetPos).isAir() || this.level().getBlockState(targetPos).canBeReplaced()) {
            net.minecraft.world.level.block.state.BlockState estado = block.defaultBlockState();
            if (propiedades != null && !propiedades.isEmpty()) {
                NoxBloques.Resultado res = NoxBloques.aplicarPropiedades(estado, propiedades);
                estado = res.estado();
                if (res.ignoradas() > 0 && this.accionesAvisadas.add("estado:" + blockIdString)) { // una vez por tipo de bloque, no por bloque
                    LOGGER.warn("[Cobalt] {}: {} propiedad(es) de '{}' no existen para ese bloque y se ignoraron", blockIdString, res.ignoradas(), propiedades);
                }
            }
            this.level().setBlock(targetPos, estado, 3);

            if (sonido) {
                this.level().playSound(null, targetPos, estado.getSoundType().getPlaceSound(),
                        net.minecraft.sounds.SoundSource.BLOCKS, 1.0F, 1.0F);
            }

            this.inventory.removeItem(slotConItem, 1);
            return true;
        }

        this.motivoFalloColocacion = "ocupado";
        return false;
    }

    private void exportarModsUnaVez() {
        if (this.modsExportados) return;
        this.modsExportados = true;
        try {
            List<String[]> mods = new ArrayList<>();
            for (net.minecraftforge.forgespi.language.IModInfo m : net.minecraftforge.fml.ModList.get().getMods()) {
                mods.add(new String[] {m.getModId(), String.valueOf(m.getVersion())});
            }
            NoxSensorWriter.escribirAtomico("mods.json", NoxMods.aJson(net.minecraft.SharedConstants.getCurrentVersion().getName(), mods));
        } catch (Exception e) {
            LOGGER.warn("[Cobalt] No se pudo exportar la lista de mods: {}", e.toString());
        }
    }

    private void actualizarGPS() {
        if (this.level().isClientSide()) return;
        this.exportarModsUnaVez();

        JsonObject gps = new JsonObject();
        gps.addProperty("x", this.getBlockX());
        gps.addProperty("y", this.getBlockY());
        gps.addProperty("z", this.getBlockZ());
        gps.addProperty("bot_id", NoxCuerpo.BOT_ID);
        gps.addProperty("dimension", this.level().dimension().location().toString());
        gps.addProperty("biome", this.level().getBiome(this.blockPosition()).unwrapKey()
                .map(clave -> clave.location().toString()).orElse("desconocido"));
        try {
            JsonObject mundo = new JsonObject();
            mundo.addProperty("day_time", this.level().getDayTime() % 24000L);
            mundo.addProperty("raining", this.level().isRaining());
            mundo.addProperty("thundering", this.level().isThundering());
            mundo.addProperty("has_skylight", this.level().dimensionType().hasSkyLight());
            mundo.addProperty("sky", this.level().canSeeSky(this.blockPosition()));
            mundo.addProperty("light", this.level().getMaxLocalRawBrightness(this.blockPosition()));
            gps.add("mundo", mundo);
        } catch (Exception e) {
            if (!this.avisadoFalloMundo) {
                this.avisadoFalloMundo = true;
                LOGGER.warn("[Cobalt] No se pudo leer la hora y el clima del mundo: {}", e.toString());
            }
        }

        Player owner = this.getCobaltOwner();
        if (owner != null) {
            JsonObject posJugador = new JsonObject();
            posJugador.addProperty("x", owner.getBlockX());
            posJugador.addProperty("y", owner.getBlockY());
            posJugador.addProperty("z", owner.getBlockZ());
            posJugador.addProperty("hp", Math.round(owner.getHealth() * 10.0F) / 10.0F); // vida del jugador
            posJugador.addProperty("max_hp", owner.getMaxHealth());
            posJugador.addProperty("alive", owner.isAlive());
            posJugador.addProperty("name", owner.getGameProfile().getName());
            try {
                posJugador.addProperty("food", owner.getFoodData().getFoodLevel());
                posJugador.addProperty("saturation", Math.round(owner.getFoodData().getSaturationLevel() * 10.0F) / 10.0F);
                posJugador.addProperty("armor", owner.getArmorValue());
                posJugador.addProperty("air", owner.getAirSupply());
                posJugador.addProperty("max_air", owner.getMaxAirSupply());
                posJugador.addProperty("on_fire", owner.isOnFire());
                int libres = 0;
                for (ItemStack hueco : owner.getInventory().items) if (hueco.isEmpty()) libres++;
                posJugador.addProperty("free_slots", libres);
            } catch (Exception e) {
                if (!this.avisadoFalloJugador) {
                    this.avisadoFalloJugador = true;
                    LOGGER.warn("[Cobalt] No se pudo leer el estado del jugador (hambre, aire...): {}", e.toString());
                }
            }
            gps.add("owner", posJugador);
        } else {
            Player remoto = this.duenoEnCualquierDimension();
            if (remoto != null) {
                JsonObject otra = new JsonObject();
                otra.addProperty("x", remoto.getBlockX());
                otra.addProperty("y", remoto.getBlockY());
                otra.addProperty("z", remoto.getBlockZ());
                otra.addProperty("dimension", remoto.level().dimension().location().toString());
                gps.add("owner_remote", otra);
            }
        }
        NoxSensorWriter.escribirAtomico("gps.json", gps.toString());
    }

    private JsonObject datosDeEstado() {
        JsonObject extra = new JsonObject();
        try {
            extra.add("inventory", NoxSensorWriter.resumirInventario(this.inventory));
        } catch (Exception e) {
            LOGGER.warn("[Cobalt] No se pudo resumir el inventario: {}", e.toString());
        }
        extra.addProperty("following", this.isFollowingOwner);
        extra.addProperty("in_combat", this.enCombate());
        LivingEntity objetivo = this.getTarget();
        extra.addProperty("target", objetivo != null && objetivo.isAlive() ? objetivo.getName().getString() : null);
        extra.addProperty("on_ground", this.onGround());
        extra.addProperty("in_water", this.isInWater());
        extra.addProperty("critical_hp", this.vidaCriticaActiva);
        extra.addProperty("fleeing", this.huyendo);
        extra.addProperty("emp_ready", this.empCooldownTicks <= 0);
        extra.addProperty("emp_cooldown_s", (int) Math.ceil(this.empCooldownTicks / 20.0D));
        extra.addProperty("drones_ready", this.dronesCooldownTicks <= 0 && NoxConfig.activo("enjambre_drones"));
        extra.addProperty("drones_cooldown_s", NoxDrones.segundosRestantes(this.dronesCooldownTicks));
        extra.addProperty("drones_active", this.dronesRestantesTicks > 0);
        extra.addProperty("drones_left_s", NoxDrones.segundosRestantes(this.dronesRestantesTicks));
        extra.addProperty("boss_mode", this.modoJefe);
        extra.addProperty("boss_name", this.nombreJefe);
        extra.addProperty("task", this.tareas.descripcion());
        extra.addProperty("queue", this.tareas.pendientes());
        extra.addProperty("frozen", this.congelado);
        extra.addProperty("sneaking", this.isShiftKeyDown());
        extra.addProperty("guarding", this.guardia != null);
        extra.addProperty("boss_extreme", this.jefeExtremo);
        com.google.gson.JsonObject danio = NoxSensorWriter.datosDeDanio(this);
        if (danio != null) extra.add("last_damage", danio);
        this.datosDelServidor(extra);
        return extra;
    }

    private void registrarWaypoint(String prefijo, BlockPos pos) {
        try {
            File wpFile = com.example.cobaltbot.util.NoxRutas.archivo("waypoints.json");
            JsonObject waypoints = new JsonObject();
            if (wpFile.exists()) {
                String contenido = Files.readString(wpFile.toPath(), StandardCharsets.UTF_8);
                if (!contenido.isBlank()) {
                    waypoints = JsonParser.parseString(contenido).getAsJsonObject(); // lanza si está corrupto: no se pisa
                }
            }
            JsonObject coords = new JsonObject();
            coords.addProperty("x", pos.getX());
            coords.addProperty("y", pos.getY());
            coords.addProperty("z", pos.getZ());
            waypoints.add(prefijo + System.currentTimeMillis(), coords);
            NoxSensorWriter.escribirAtomico("waypoints.json", waypoints.toString());
        } catch (Exception e) {
            LOGGER.warn("[Cobalt] No se registró el waypoint '{}': {}", prefijo, e.toString());
        }
    }

    public void ejecutarPulsoEMP() {
        if (this.level().isClientSide()) return;

        if (this.empCooldownTicks > 0) {
            return;
        }

        this.isPerformingEMP = true;
        this.empAnimationTicks = 20;
        this.triggerAnim("attackController", "emp");
        if (this.level() instanceof ServerLevel nivelOnda) {
            EmpWaveEntity onda = new EmpWaveEntity(com.example.cobaltbot.registry.ModEntities.EMP_WAVE.get(), nivelOnda);
            onda.setPos(this.getX(), this.getY() + 0.05D, this.getZ());
            nivelOnda.addFreshEntity(onda);
        }

        ServerLevel serverLevel = (ServerLevel) this.level();
        double radius = 7.0D;

        serverLevel.sendParticles(net.minecraft.core.particles.ParticleTypes.END_ROD, this.getX(), this.getY() + 1.0D, this.getZ(), 40, 1.2D, 0.5D, 1.2D, 0.12D); // chispas arcanas (antes: una explosión de TNT)
        serverLevel.playSound(null, this.blockPosition(), net.minecraft.sounds.SoundEvents.LIGHTNING_BOLT_THUNDER, net.minecraft.sounds.SoundSource.NEUTRAL, 1.5F, 2.0F);

        net.minecraft.world.phys.AABB areaEfecto = this.getBoundingBox().inflate(radius);
        java.util.List<net.minecraft.world.entity.LivingEntity> enemigosCercanos = this.level().getEntitiesOfClass(
                net.minecraft.world.entity.LivingEntity.class, areaEfecto,
                e -> e != this && e instanceof net.minecraft.world.entity.monster.Enemy
                        && !(e instanceof Player) && e.distanceToSqr(this) <= radius * radius
        );

        if (!enemigosCercanos.isEmpty()) {
            for (net.minecraft.world.entity.LivingEntity enemigo : enemigosCercanos) {
                enemigo.hurt(this.damageSources().indirectMagic(this, this), 12.0F);

                double deltaX = enemigo.getX() - this.getX();
                double deltaZ = enemigo.getZ() - this.getZ();
                enemigo.knockback(2.0D, -deltaX, -deltaZ);

                enemigo.addEffect(new net.minecraft.world.effect.MobEffectInstance(
                        net.minecraft.world.effect.MobEffects.MOVEMENT_SLOWDOWN, 60, 4, false, false
                ));

                serverLevel.sendParticles(net.minecraft.core.particles.ParticleTypes.ELECTRIC_SPARK, enemigo.getX(), enemigo.getY() + 1.0D, enemigo.getZ(), 20, 0.5D, 0.5D, 0.5D, 0.2D);
            }

            this.empCooldownTicks = 1200;
            if (NoxConfig.activo("retroceso_post_emp")) this.retrocesoTicks = 40; // 2 s de retirada (el kiting la aplica)

            this.level().getServer().getPlayerList().broadcastSystemMessage(
                    Component.literal("§b⚡ ¡Pulso EMP desplegado! Onda de choque, daño masivo y aturdimiento."), false
            );
        }
    }

    /** Combate a distancia con KITING: mantiene ~10-15 bloques del objetivo, dispara plasma con. */
    private class CobaltKitingGoal extends Goal {
        private static final double DIST_RETROCESO = 9.0D;   // más cerca que esto: retrocede y despega
        private static final double DIST_IDEAL = 12.0D;      // centro de la banda de kiting (10-15)
        private static final double DIST_MAX = 16.0D;        // más lejos (o sin visión): se acerca
        private static final double DIST_MELEE = 2.5D;       // último recurso
        private static final int REPATH_TICKS = 5;

        private final CobaltEntity mob;
        private final double speedModifier;
        private final int attackInterval;
        private int attackTime = -1;
        private int seeTime;
        private int repathTicks;
        private int strafeTicks;
        private int strafeDir = 1;
        private int meleeCooldown;
        private boolean modoMelee;
        private int reevaluarTicks;
        private double anclaY; // altura de referencia si no hay dueño cerca

        public CobaltKitingGoal(CobaltEntity mob, double speedModifier, int attackInterval) {
            this.mob = mob;
            this.speedModifier = speedModifier;
            this.attackInterval = attackInterval;
            this.setFlags(EnumSet.of(Flag.MOVE, Flag.LOOK));
        }

        @Override
        public boolean canUse() {
            LivingEntity target = this.mob.getTarget();
            return target != null && target.isAlive() && !(target instanceof Player)
                    && !(this.mob.vidaCriticaActiva && NoxConfig.activo("huida_vida_critica"));
        }

        @Override
        public boolean canContinueToUse() {
            return this.canUse();
        }

        @Override
        public void start() {
            super.start();
            this.mob.setAggressive(true);
            this.repathTicks = 0;
            this.strafeTicks = 0;
            this.anclaY = this.mob.getY();
        }

        @Override
        public void stop() {
            super.stop();
            this.mob.setAggressive(false);
            this.mob.getNavigation().stop();
            this.seeTime = 0;
            this.attackTime = -1;
        }

        @Override
        public boolean requiresUpdateEveryTick() {
            return true;
        }

        @Override
        public void tick() {
            LivingEntity target = this.mob.getTarget();
            if (target == null) return;
            NoxJefes.ParametrosKiting pk = NoxJefes.parametros(this.mob.modoJefe, this.mob.jefeExtremo); // con jefe: más lejos y solo plasma
            double distRetroceso = pk.retroceso(), distIdeal = pk.ideal(), distMax = pk.max();

            double dx = this.mob.getX() - target.getX();
            double dz = this.mob.getZ() - target.getZ();
            double distH = Math.max(1.0E-3D, Math.sqrt(dx * dx + dz * dz));
            double dist = this.mob.distanceTo(target);
            boolean canSee = this.mob.getSensing().hasLineOfSight(target);
            this.seeTime = canSee ? this.seeTime + 1 : 0;

            this.mob.getLookControl().setLookAt(target, 30.0F, 30.0F);
            if (this.meleeCooldown > 0) this.meleeCooldown--;
            if (this.mob.retrocesoTicks > 0) this.mob.retrocesoTicks--;
            if (--this.reevaluarTicks <= 0) { // cada segundo: ¿melee o kiting?
                this.reevaluarTicks = 20;
                this.modoMelee = this.mob.evaluarCuerpoACuerpo(target);
            }

            // Si el enemigo acorta distancia, despega (salvo que esté nadando)
            if (dist < distRetroceso && !this.modoMelee && !this.mob.isFlying && !(this.mob.getNavigation() instanceof WaterBoundPathNavigation)) {
                this.mob.setModoVuelo(true);
            }

            // Movimiento: se recalcula cada pocos ticks, no cada tick
            if (--this.repathTicks <= 0) {
                this.repathTicks = REPATH_TICKS;
                double ux = dx / distH;
                double uz = dz / distH;

                if (this.modoMelee) {
                    this.moverA(target.getX(), target.getY(), target.getZ());
                } else if (dist < distRetroceso || this.mob.retrocesoTicks > 0) {
                    double ty = this.mob.modoJefe ? NoxJefes.alturaEvasion(target.getY() + 3.0D, this.mob.tickCount) // evasión en 3D
                            : (this.mob.isFlying ? Math.max(this.mob.getY(), target.getY() + 2.0D) : this.mob.getY());
                    this.moverA(this.mob.getX() + ux * 6.0D, ty, this.mob.getZ() + uz * 6.0D);
                } else if (dist > distMax || !canSee) {
                    this.moverA(target.getX(), target.getY(), target.getZ());
                } else {
                    // Strafe lateral con corrección radial hacia la distancia ideal
                    this.strafeTicks -= REPATH_TICKS;
                    if (this.strafeTicks <= 0) {
                        this.strafeDir = this.mob.getRandom().nextBoolean() ? 1 : -1;
                        this.strafeTicks = 30 + this.mob.getRandom().nextInt(40);
                    }
                    double radial = Math.max(-4.0D, Math.min(4.0D, (distIdeal - distH) * 0.5D));
                    double tx = this.mob.getX() + ux * radial + (-uz) * this.strafeDir * 4.0D;
                    double tz = this.mob.getZ() + uz * radial + ux * this.strafeDir * 4.0D;
                    double ty = this.mob.modoJefe ? NoxJefes.alturaEvasion(target.getY() + 3.0D, this.mob.tickCount) // evasión en 3D
                            : (this.mob.isFlying ? Math.max(this.mob.getY(), target.getY() + 2.0D) : this.mob.getY());
                    this.moverA(tx, ty, tz);
                }
            }

            // Disparo de plasma
            if (--this.attackTime <= 0 && canSee && dist <= distMax) {
                this.mob.performRangedAttack(target, 1.0F);
                this.attackTime = this.attackInterval;
            }

            // Último recurso: enemigo pegado
            if (pk.permiteMelee() && dist <= DIST_MELEE && this.meleeCooldown <= 0) {
                this.mob.swing(InteractionHand.MAIN_HAND);
                this.mob.doHurtTarget(target);
                this.meleeCooldown = 20;
            }
        }

        private void moverA(double x, double y, double z) {
            if (this.mob.guardia != null) {
                double[] xz = NoxCuerpo.limitarAGuardia(x, z, this.mob.guardia.getX() + 0.5D, this.mob.guardia.getZ() + 0.5D, this.mob.guardiaRadio);
                x = xz[0];
                z = xz[1];
            }
            Player dueno = this.mob.getCobaltOwner();
            if (this.mob.modoJefe && dueno != null && this.mob.duenoSiSigue() != null) { // correa: contra un jefe no se aleja más de N bloques del dueño
                double[] xz = NoxCuerpo.limitarAGuardia(x, z, dueno.getX(), dueno.getZ(), NoxConfig.numero("jefe_correa", 32.0D));
                x = xz[0];
                z = xz[1];
            }
            if (this.mob.isFlying) {
                double ancla = (dueno != null && this.mob.distanceTo(dueno) <= 48.0F) ? dueno.getY() : this.anclaY; // lejos del dueño (minando, en una cueva): su propia altura
                y = NoxJefes.limitarAltura(y, ancla, NoxConfig.numero("jefe_altura_max", 14.0D), 4.0D);
            }
            if (!this.mob.getNavigation().moveTo(x, y, z, this.speedModifier)) {
                this.mob.getMoveControl().setWantedPosition(x, y, z, this.speedModifier);
            }
        }
    }

    /** FloatGoal de vanilla, salvo en modo nado: hacía saltar a Cobalt el 80 % de los ticks y jamás le dejaba bucear. */
    private class CobaltFloatGoal extends FloatGoal {
        public CobaltFloatGoal(CobaltEntity mob) {
            super(mob);
        }

        @Override
        public boolean canUse() {
            return !(CobaltEntity.this.getNavigation() instanceof WaterBoundPathNavigation) && super.canUse();
        }
    }

    /** Control de vuelo. */
    private static class CobaltFlyMoveControl extends FlyingMoveControl {
        private static final double UMBRAL_RAPIDO = 1.29D;
        private static final int TICKS_MANTENER_DESTINO = 12;
        private int ticksSinOrden = 0;

        public CobaltFlyMoveControl(CobaltEntity mob) {
            super(mob, 30, true);
        }

        @Override
        public void setWantedPosition(double x, double y, double z, double velocidad) {
            super.setWantedPosition(x, y, z, velocidad);
            this.ticksSinOrden = 0;
        }

        @Override
        public void tick() {
            if (this.speedModifier < UMBRAL_RAPIDO || this.operation != Operation.MOVE_TO) {
                super.tick();
                return;
            }
            if (++this.ticksSinOrden > TICKS_MANTENER_DESTINO) { // nadie repuso la orden: se da por terminada
                this.operation = Operation.WAIT;
                return;
            }
            this.mob.setNoGravity(true);
            Vec3 hacia = new Vec3(this.wantedX - this.mob.getX(), this.wantedY - this.mob.getY(), this.wantedZ - this.mob.getZ());
            double dist = hacia.length();
            Vec3 actual = this.mob.getDeltaMovement();
            if (dist < 0.6D) { // llegó
                this.operation = Operation.WAIT;
                this.mob.setDeltaMovement(actual.scale(0.5D));
                return;
            }
            double v = NoxCuerpo.velocidadObjetivoVuelo(dist, this.speedModifier);
            Vec3 objetivo = hacia.scale(v / dist);
            if (this.mob.horizontalCollision || this.mob.verticalCollisionBelow) { // choca con un muro o el suelo: sube para salvarlo en vez de empujar
                objetivo = objetivo.add(0.0D, 0.18D, 0.0D);
            }
            this.mob.setDeltaMovement(actual.add(objetivo.subtract(actual).scale(0.3D))); // aceleración suave
            float giro = (float) (Mth.atan2(hacia.z, hacia.x) * (180.0D / Math.PI)) - 90.0F;
            this.mob.setYRot(this.rotlerp(this.mob.getYRot(), giro, 30.0F));
            this.mob.yBodyRot = this.mob.getYRot();
        }
    }

    private static class CobaltSwimMoveControl extends MoveControl {
        public CobaltSwimMoveControl(CobaltEntity mob) {
            super(mob);
        }

        @Override
        public void tick() {
            if (!this.mob.isInWater()) {
                super.tick();
                return;
            }
            this.mob.setDeltaMovement(this.mob.getDeltaMovement().add(0.0D, 0.005D, 0.0D)); // flotabilidad neutra
            if (this.operation != Operation.MOVE_TO) return;
            if (this.mob.horizontalCollision) {
                Vec3 v = this.mob.getDeltaMovement();
                this.mob.setDeltaMovement(v.x, Math.max(v.y, 0.25D), v.z);
            }

            Vec3 hacia = new Vec3(this.wantedX - this.mob.getX(), this.wantedY - this.mob.getY(), this.wantedZ - this.mob.getZ());
            double dist = hacia.length();
            if (dist < 0.5D) {
                this.operation = Operation.WAIT;
                this.mob.setDeltaMovement(this.mob.getDeltaMovement().scale(0.5D));
                return;
            }
            this.mob.setDeltaMovement(this.mob.getDeltaMovement().add(hacia.scale(this.speedModifier * 0.02D / dist)));

            float yaw = (float) (Mth.atan2(hacia.z, hacia.x) * (180.0D / Math.PI)) - 90.0F;
            this.mob.setYRot(this.rotlerp(this.mob.getYRot(), yaw, 30.0F));
            this.mob.yBodyRot = this.mob.getYRot();
        }
    }
}
