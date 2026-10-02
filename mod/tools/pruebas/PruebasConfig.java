import com.example.cobaltbot.util.NoxConfig;

/** Pruebas de los interruptores de seguridad (NoxConfig) sin abrir Minecraft. */
public class PruebasConfig {
    static int fallos = 0;

    static void check(String nombre, boolean ok) {
        System.out.println((ok ? "OK   " : "FAIL ") + nombre);
        if (!ok) fallos++;
    }

    public static void main(String[] args) {
        NoxConfig.fijarParaPruebas("{\"autocuracion\": false, \"modo_jefe\": true, \"mineria_real\": \"no\", "
                + "\"vida_critica_pct\": 25, \"raro\": 3, \"_comentario\": \"texto\"}");

        check("false apaga la función", !NoxConfig.activo("autocuracion"));
        check("true la mantiene", NoxConfig.activo("modo_jefe"));
        check("clave ausente -> ENCENDIDA por defecto", NoxConfig.activo("prediccion_disparo"));
        check("valor no booleano ('no') se ignora -> encendida", NoxConfig.activo("mineria_real"));
        check("un número no cuenta como booleano -> encendida", NoxConfig.activo("raro"));
        check("con defecto explícito: clave ausente -> el defecto (false para lo experimental, true para lo normal)",
                !NoxConfig.activo("schematics_estados", false) && NoxConfig.activo("schematics_estados", true));
        check("con defecto explícito: un valor válido manda sobre el defecto", !NoxConfig.activo("autocuracion", true) && NoxConfig.activo("modo_jefe", false));
        check("con defecto explícito: un valor no booleano ('no', 3) cae al defecto", !NoxConfig.activo("mineria_real", false) && NoxConfig.activo("raro", true));
        check("umbral numérico leído", NoxConfig.numero("vida_critica_pct", 30) == 25.0);
        check("umbral ausente -> defecto", NoxConfig.numero("vida_recuperada_pct", 50) == 50.0);
        check("un booleano no cuenta como número -> defecto", NoxConfig.numero("autocuracion", 7) == 7.0);
        check("un texto no cuenta como número -> defecto", NoxConfig.numero("_comentario", 9) == 9.0);

        System.out.println(fallos == 0 ? "\nRESULTADO: TODO OK" : "\nRESULTADO: " + fallos + " FALLOS");
        System.exit(fallos == 0 ? 0 : 1);
    }
}
