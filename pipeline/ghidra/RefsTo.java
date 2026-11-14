// RefsTo.java — per ogni indirizzo dato elenca i riferimenti (da dove, in quale funzione).
// Uso: -postScript RefsTo.java 800ad2e8 80018d10
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;

public class RefsTo extends GhidraScript {
    @Override
    protected void run() throws Exception {
        for (String a : getScriptArgs()) {
            Address addr = toAddr(a);
            println("==== riferimenti a " + addr);
            int n = 0;
            for (Reference r : getReferencesTo(addr)) {
                Function f = getFunctionContaining(r.getFromAddress());
                println("   da " + r.getFromAddress() + " " + r.getReferenceType() + "  in " + (f == null ? "?" : f.getName() + " @ " + f.getEntryPoint()));
                n++;
            }
            if (n == 0) println("   (nessuno)");
        }
    }
}
