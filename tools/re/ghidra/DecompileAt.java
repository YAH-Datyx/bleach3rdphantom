// Decompiliert die Funktionen, die die angegebenen Adressen enthalten.
// Headless: analyzeHeadless ... -postScript DecompileAt.java <out.c> <addr> [addr ...]
// Findet Ghidra an einer Adresse keine Funktion, wird rückwärts nach dem
// ARM-Prolog (stmdb sp!, {..., lr}) gesucht und dort eine Funktion angelegt.
//@category Bleach3P
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.*;
import java.io.*;
import java.util.*;

public class DecompileAt extends GhidraScript {
    private Function findOrCreate(Address a) throws Exception {
        Function f = getFunctionContaining(a);
        if (f != null) return f;
        Address p = a;
        for (int i = 0; i < 4096; i++, p = p.subtract(4)) {
            int w = getInt(p);
            // STMDB SP!, {..., LR}  (cond=AL): 0xE92D4xxx
            if ((w & 0xFFFF4000) == 0xE92D4000) {
                disassemble(p);
                f = createFunction(p, null);
                if (f != null) return f;
                break;
            }
        }
        return null;
    }

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        PrintWriter out = new PrintWriter(new FileWriter(args[0]));
        DecompInterface di = new DecompInterface();
        di.openProgram(currentProgram);
        Set<Function> done = new HashSet<>();
        for (int i = 1; i < args.length; i++) {
            Address a = toAddr(args[i]);
            Function f = findOrCreate(a);
            if (f == null) { out.println("// " + args[i] + ": keine Funktion gefunden\n"); continue; }
            if (!done.add(f)) { out.println("// " + args[i] + ": in " + f.getName() + " (s. o.)\n"); continue; }
            DecompileResults r = di.decompileFunction(f, 120, monitor);
            out.println("// ==== " + args[i] + " in " + f.getName() + " @ " + f.getEntryPoint() + " ====");
            out.println(r.decompileCompleted() ? r.getDecompiledFunction().getC() : "// Fehler: " + r.getErrorMessage());
        }
        out.close();
    }
}
