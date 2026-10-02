package com.example.cobaltbot.item;

import com.example.cobaltbot.entity.CobaltEntity;
import com.example.cobaltbot.registry.ModEntities;
import com.example.cobaltbot.util.NoxChip;
import com.example.cobaltbot.util.NoxSensorWriter;
import net.minecraft.ChatFormatting;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResultHolder;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.Level;
import org.jetbrains.annotations.Nullable;

import java.util.List;
import java.util.UUID;

public class NoxSummonerItem extends Item {
    public NoxSummonerItem(Properties properties) {
        super(properties.stacksTo(1)); // Bloquea a 1 por slot para evitar duplicados
    }

    @Override
    public InteractionResultHolder<ItemStack> use(Level level, Player player, InteractionHand hand) {
        ItemStack stack = player.getItemInHand(hand);

        if (!level.isClientSide()) {
            ServerLevel serverLevel = (ServerLevel) level;
            CompoundTag tag = stack.getOrCreateTag();

            boolean isDeployed = tag.getBoolean("IsDeployed");
            String uuidStr = tag.getString("CobaltUUID");

            if (isDeployed && !uuidStr.isEmpty()) {
                try {
                    UUID uuid = UUID.fromString(uuidStr);
                    net.minecraft.world.entity.Entity entity = null; // se busca en TODAS las dimensiones (Cobalt puede haberse quedado en otra)
                    for (ServerLevel nivelBuscado : serverLevel.getServer().getAllLevels()) {
                        entity = nivelBuscado.getEntity(uuid);
                        if (entity != null) break;
                    }

                    if (entity != null) {
                        if (!entity.isAlive()) {
                            // La entidad murió oficialmente
                            tag.putBoolean("IsDeployed", false);
                            tag.remove("CobaltUUID");
                            isDeployed = false;
                        } else {
                            isDeployed = true;
                        }
                    } else {
                        isDeployed = true;
                    }
                } catch (Exception e) {
                    tag.putBoolean("IsDeployed", false);
                    tag.remove("CobaltUUID");
                    isDeployed = false;
                }
            } else {
                isDeployed = false;
                tag.putBoolean("IsDeployed", false);
            }
            if (!isDeployed && serverLevel.getServer() != null) {
                com.example.cobaltbot.entity.CobaltEntity huerfano = NoxChip.buscarUno(serverLevel.getServer(), player.getUUID());
                if (huerfano != null) {
                    tag.putBoolean("IsDeployed", true);
                    tag.putString("CobaltUUID", huerfano.getUUID().toString());
                    isDeployed = true;
                    uuidStr = huerfano.getUUID().toString();
                    player.sendSystemMessage(Component.literal("§e[Sistema]: Ya había un Cobalt tuyo activo en " + huerfano.level().dimension().location().getPath()
                            + ": lo he vuelto a vincular al chip (así no se duplica). Usa 'Al Chip' o Shift + clic para traerlo."));
                }
            }

            // EMERGENCIA (Shift + Clic): Teletransportar a Cobalt a tu posición
            if (player.isShiftKeyDown()) {
                if (isDeployed && !uuidStr.isEmpty()) {
                    boolean found = false;
                    CobaltEntity noxRescate = NoxChip.buscarUno(serverLevel.getServer(), player.getUUID()); // en cualquier dimensión
                    if (noxRescate != null) {
                        if (noxRescate.level() == player.level()) {
                            noxRescate.teleportTo(player.getX(), player.getY(), player.getZ());
                            noxRescate.setDeltaMovement(0, 0, 0);
                            player.sendSystemMessage(Component.literal("§e[Emergencia]: Cobalt ha sido teletransportado a tu posición."));
                            found = true;
                        } else if (player instanceof net.minecraft.server.level.ServerPlayer jugador && noxRescate.cruzarDimension(jugador)) {
                            player.sendSystemMessage(Component.literal("§e[Emergencia]: Cobalt ha cruzado de dimensión hasta ti."));
                            found = true;
                        }
                    }
                    if (!found) {
                        player.sendSystemMessage(Component.literal("§e[Sistema]: Cobalt está en un chunk descargado. Acércate a su zona para traerlo."));
                    }
                } else {
                    player.sendSystemMessage(Component.literal("§c[Sistema]: Cobalt não está activo en el mundo. Invócalo primero."));
                }
                return InteractionResultHolder.sidedSuccess(stack, level.isClientSide());
            }

            // 1. VALIDACIÓN DE LÍMITE: Verificar si ya está desplegado
            if (isDeployed) {
                player.sendSystemMessage(Component.literal("§c[Sistema]: Ya tienes una unidad Cobalt activa en el mundo. Debes regresarla al chip primero."));
                return InteractionResultHolder.fail(stack);
            }

            // 2. VALIDACIÓN DE PENALIZACIÓN POR MUERTE (15 minutos = 18,000 ticks)
            if (tag.contains("IsDead") && tag.getBoolean("IsDead")) {
                float regenTicksLeft = tag.getFloat("RegenTicksLeft");
                int remainingMinutes = (int) Math.ceil(regenTicksLeft / 1200.0f); // 1200 ticks = 1 minuto
                player.sendSystemMessage(Component.literal("§c[Sistema]: Cobalt fue destruido en combate y se está reconstruyendo. Tiempo restante: ~" + remainingMinutes + " min."));
                return InteractionResultHolder.fail(stack);
            }

            // INVOCACIÓN NORMAL
            CobaltEntity nox = ModEntities.COBALT.get().create(serverLevel);
            if (nox != null) {
                nox.setPos(player.getX(), player.getY(), player.getZ());
                nox.setOwnerUUID(player.getUUID());
                serverLevel.addFreshEntity(nox);
                int recuperados = NoxChip.restaurarInventario(stack, nox.getCobaltInventory()); // lo que llevaba al guardarlo en el chip

                tag.putBoolean("IsDeployed", true);
                tag.putBoolean("IsDead", false);
                tag.putString("CobaltUUID", nox.getUUID().toString()); // Guardamos el UUID para sincronización
                player.sendSystemMessage(Component.literal("§a[Sistema]: ¡Cobalt ha sido convocado con éxito!" + (recuperados > 0 ? " Recupera " + recuperados + " objeto(s) de su inventario." : "")));
            }
        }

        return InteractionResultHolder.sidedSuccess(stack, level.isClientSide());
    }

    @Override
    public void inventoryTick(ItemStack stack, Level level, net.minecraft.world.entity.Entity entity, int slotId, boolean isSelected) {
        super.inventoryTick(stack, level, entity, slotId, isSelected);

        if (!level.isClientSide() && entity instanceof Player player) {
            CompoundTag tag = stack.getOrCreateTag();

            if (tag.contains("IsDead") && tag.getBoolean("IsDead")) {
                float regenTicksLeft = tag.getFloat("RegenTicksLeft");
                if (regenTicksLeft > 0) {
                    regenTicksLeft -= 1.0f;
                    tag.putFloat("RegenTicksLeft", regenTicksLeft);

                    if (regenTicksLeft <= 0) {
                        tag.putBoolean("IsDead", false);
                        tag.remove("RegenTicksLeft");
                        NoxSensorWriter.escribirEstadoChip(false, 0);
                        player.sendSystemMessage(Component.literal("§a[Sistema]: ¡Cobalt se ha reconstruido por completo en la base y está listo para invocarse!"));
                    } else if (player.tickCount % 20 == 0) {
                        NoxSensorWriter.escribirEstadoChip(true, (int) Math.ceil(regenTicksLeft / 1200.0f));
                    }
                }
            }
        }
    }

    @Override
    public boolean isBarVisible(ItemStack stack) {
        CompoundTag tag = stack.getTag();
        if (tag != null && tag.contains("IsDead") && tag.getBoolean("IsDead")) {
            return true; // Muestra barra roja de regeneración por muerte
        }
        return tag != null && tag.getBoolean("IsDeployed");
    }

    @Override
    public int getBarWidth(ItemStack stack) {
        CompoundTag tag = stack.getTag();
        if (tag != null && tag.contains("IsDead") && tag.getBoolean("IsDead")) {
            float totalTicks = 18000.0f; // 15 minutos exactos
            float currentLeft = tag.getFloat("RegenTicksLeft");
            float progress = 1.0f - (currentLeft / totalTicks);
            return Math.round(13.0F * Math.max(0.0f, Math.min(1.0f, progress)));
        }
        if (tag != null && tag.getBoolean("IsDeployed")) {
            return 1; // Casi vacía cuando está desplegado
        }
        return 13;
    }

    @Override
    public int getBarColor(ItemStack stack) {
        return 0xFF5555; // Rojo para indicar estado crítico/espera
    }

    @Override
    public void appendHoverText(ItemStack stack, @Nullable Level level, List<Component> tooltip, TooltipFlag flag) {
        CompoundTag tag = stack.getTag();
        if (tag != null && tag.contains("IsDead") && tag.getBoolean("IsDead")) {
            float regenTicksLeft = tag.getFloat("RegenTicksLeft");
            int remainingMinutes = (int) Math.ceil(regenTicksLeft / 1200.0f);
            tooltip.add(Component.literal("Estado: Reconstruyéndose (" + remainingMinutes + " min restantes)").withStyle(ChatFormatting.RED));
        } else if (tag != null && tag.getBoolean("IsDeployed")) {
            tooltip.add(Component.literal("Estado: Desplegado en el mundo").withStyle(ChatFormatting.YELLOW));
        } else {
            tooltip.add(Component.literal("Estado: Listo para invocar").withStyle(ChatFormatting.GREEN));
        }
        super.appendHoverText(stack, level, tooltip, flag);
    }

    @Override
    public void onCraftedBy(ItemStack stack, Level level, Player player) {
        super.onCraftedBy(stack, level, player);
        if (!level.isClientSide()) {
            CompoundTag tag = stack.getOrCreateTag();
            tag.putBoolean("IsDeployed", false);
            tag.putBoolean("IsDead", false);
            tag.remove("RegenTicksLeft");
            tag.remove("CobaltUUID");
        }
    }
}
