// ExportAll.java — decompila TUTTE le funzioni del programma in un unico file C + indice (uso personale, output NON versionato).
// Uso: analyzeHeadless out/ghidra AC2 -process overlay0.bin -noanalysis -scriptPath pipeline/ghidra \
//        -postScript ExportAll.java out/codice/overlay0
// Scrive OUT.c (una sezione per funzione con intestazione "==== FUN @ indirizzo size=N chiamanti=[...] chiama=[...]") e OUT.idx.tsv.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import java.io.PrintWriter;
import java.util.Set;
import java.util.stream.Collectors;

public class ExportAll extends GhidraScript {
    @Override
    protected void run() throws Exception {
        String base = getScriptArgs()[0];
        new java.io.File(base).getParentFile().mkdirs();
        DecompInterface di = new DecompInterface();
        di.openProgram(currentProgram);
        int n = 0, bad = 0;
        try (PrintWriter c = new PrintWriter(base + ".c"); PrintWriter ix = new PrintWriter(base + ".idx.tsv")) {
            ix.println("indirizzo\tnome\tbyte\tchiamanti\tchiamati");
            FunctionIterator it = currentProgram.getFunctionManager().getFunctions(true);
            while (it.hasNext() && !monitor.isCancelled()) {
                Function f = it.next();
                Set<Function> callers = f.getCallingFunctions(monitor);
                Set<Function> callees = f.getCalledFunctions(monitor);
                String cl = callers.stream().map(Function::getName).sorted().collect(Collectors.joining(","));
                String ce = callees.stream().map(Function::getName).sorted().collect(Collectors.joining(","));
                long size = f.getBody().getNumAddresses();
                ix.println(f.getEntryPoint() + "\t" + f.getName() + "\t" + size + "\t" + callers.size() + "\t" + callees.size());
                c.println("// ==== " + f.getName() + " @ " + f.getEntryPoint() + " size=" + size + " chiamanti=[" + cl + "] chiama=[" + ce + "]");
                DecompileResults r = di.decompileFunction(f, 60, monitor);
                if (r.decompileCompleted()) c.println(r.getDecompiledFunction().getC());
                else { c.println("// decompilazione fallita: " + r.getErrorMessage()); bad++; }
                n++;
            }
        }
        println("ExportAll: " + n + " funzioni, " + bad + " fallite -> " + base);
    }
}
