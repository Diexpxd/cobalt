package com.example.cobaltbot.util;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.mojang.logging.LogUtils;
import org.slf4j.Logger;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;

/** INTERRUPTORES DE SEGURIDAD: lee cobalt_config.json de la carpeta de intercambio y se relee solo cada 5 s, así. */
public final class NoxConfig {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final File ARCHIVO = com.example.cobaltbot.util.NoxRutas.archivo("cobalt_config.json");
    private static final long RELEER_CADA_MS = 5000L;

    private static volatile JsonObject datos = new JsonObject();
    private static volatile long ultimaLectura = 0L;
    private static volatile long ultimaModificacion = -1L;
    private static volatile boolean fijadoParaPruebas = false;

    private NoxConfig() {}

    public static boolean activo(String clave) {
        return activo(clave, true);
    }

    public static boolean activo(String clave, boolean defecto) {
        recargarSiHaceFalta();
        try {
            JsonElement el = datos.get(clave);
            if (el != null && el.isJsonPrimitive() && el.getAsJsonPrimitive().isBoolean()) {
                return el.getAsBoolean();
            }
        } catch (Exception ignorada) {
            // valor inválido: se usa el defecto
        }
        return defecto;
    }

    public static double numero(String clave, double defecto) {
        recargarSiHaceFalta();
        try {
            JsonElement el = datos.get(clave);
            if (el != null && el.isJsonPrimitive() && el.getAsJsonPrimitive().isNumber()) {
                return el.getAsDouble();
            }
        } catch (Exception ignorada) {
            // valor inválido: se usa el defecto
        }
        return defecto;
    }

    private static void recargarSiHaceFalta() {
        if (fijadoParaPruebas) return;
        long ahora = System.currentTimeMillis();
        if (ahora - ultimaLectura < RELEER_CADA_MS) return;
        ultimaLectura = ahora;
        try {
            if (!ARCHIVO.exists()) {
                datos = new JsonObject();
                return;
            }
            long modificado = ARCHIVO.lastModified();
            if (modificado == ultimaModificacion) return; // sin cambios: no se vuelve a parsear
            JsonElement raiz = JsonParser.parseString(Files.readString(ARCHIVO.toPath(), StandardCharsets.UTF_8));
            if (raiz.isJsonObject()) {
                datos = raiz.getAsJsonObject();
                ultimaModificacion = modificado;
            }
        } catch (Exception e) {
            // Archivo a medio guardar o roto: se conservan los últimos valores buenos
            LOGGER.warn("[NoxConfig] cobalt_config.json ilegible, se conservan los valores anteriores: {}", e.toString());
        }
    }

    public static void fijarParaPruebas(String json) {
        datos = JsonParser.parseString(json).getAsJsonObject();
        fijadoParaPruebas = true;
    }
}
