// DecompileAt.java — script Ghidra (headless): decompila le funzioni agli indirizzi dati e ne elenca i riferimenti.
// Uso: analyzeHeadless out/ghidra AC2 -process overlay0.bin -noanalysis -scriptPath pipeline/ghidra \
//        -postScript DecompileAt.java 8006685c 80067324
// Ogni argomento e' un indirizzo (hex); se cade dentro una funzione si decompila quella.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;

public class DecompileAt extends GhidraScript {
    @Override
    protected void run() throws Exception {
        DecompInterface di = new DecompInterface();
        di.openProgram(currentProgram);
        for (String a : getScriptArgs()) {
            Address addr = toAddr(a);
            Function f = getFunctionContaining(addr);
            println("==== " + a + " -> " + (f == null ? "nessuna funzione" : f.getName() + " @ " + f.getEntryPoint()));
            if (f == null) continue;
            println("-- riferimenti a " + f.getEntryPoint() + ":");
            for (Reference r : getReferencesTo(f.getEntryPoint())) println("   da " + r.getFromAddress() + " (" + r.getReferenceType() + ")");
            DecompileResults res = di.decompileFunction(f, 120, monitor);
            println(res.decompileCompleted() ? res.getDecompiledFunction().getC() : "decompilazione fallita: " + res.getErrorMessage());
        }
    }
}
