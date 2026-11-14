// SetGp.java — imposta il registro gp su tutto il programma (preScript, prima dell'analisi).
// Overlay del gioco: gp = 0x800b74f8 (impostato a 0x8001c140). Loader: gp = 0x801e0108 (a 0x801ccc38).
// Uso: -preScript SetGp.java 800b74f8
import ghidra.app.script.GhidraScript;
import ghidra.program.model.lang.Register;
import ghidra.program.model.address.Address;
import java.math.BigInteger;

public class SetGp extends GhidraScript {
    @Override
    protected void run() throws Exception {
        long gp = Long.parseUnsignedLong(getScriptArgs()[0], 16);
        Register r = currentProgram.getRegister("gp");
        Address lo = currentProgram.getMinAddress(), hi = currentProgram.getMaxAddress();
        currentProgram.getProgramContext().setValue(r, lo, hi, BigInteger.valueOf(gp));
        println("gp = 0x" + Long.toHexString(gp) + " su " + lo + ".." + hi);
    }
}
