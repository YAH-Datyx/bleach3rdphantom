// Decompiliert ALLE Funktionen in einem Adressbereich und schreibt sie blockweise als C.
// Headless: analyzeHeadless ... -postScript DecompileAll.java <out-dir> <prefix> <von> <bis> [names.txt]
//   <out-dir>/<prefix>_<block>.c   je 64 KiB Adressraum eine Datei
//   <out-dir>/<prefix>_index.tsv   Adresse, Name, Groesse, Aufrufer, Signatur
// names.txt: Zeilen "0xADRESSE Name" (eigene Benennungen, werden vorher gesetzt;
// liegt an der Adresse keine Funktion, wird ein Label gesetzt).
//@category Bleach3P
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.SourceType;
import java.io.*;
import java.nio.file.*;
import java.util.*;

public class DecompileAll extends GhidraScript {
    private void applyNames(String path) throws Exception {
        for (String line : Files.readAllLines(Paths.get(path))) {
            line = line.trim();
            if (line.isEmpty() || line.startsWith("#")) continue;
            String[] p = line.split("\\s+");
            Address a = toAddr(p[0]);
            if (!currentProgram.getMemory().contains(a)) continue;
            Function f = getFunctionAt(a);
            if (f == null && p.length > 2 && p[2].equals("func")) {
                disassemble(a);
                f = createFunction(a, null);
            }
            if (f != null) f.setName(p[1], SourceType.USER_DEFINED);
            else createLabel(a, p[1], true, SourceType.USER_DEFINED);
        }
    }

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        File dir = new File(args[0]);
        dir.mkdirs();
        String prefix = args[1];
        long lo = Long.decode(args[2]), hi = Long.decode(args[3]);
        if (args.length > 4) applyNames(args[4]);
        DecompInterface di = new DecompInterface();
        di.openProgram(currentProgram);
        PrintWriter idx = new PrintWriter(new FileWriter(new File(dir, prefix + "_index.tsv")));
        idx.println("adresse\tname\tbytes\taufrufer\tsignatur");
        Map<Long, PrintWriter> blocks = new TreeMap<>();
        int n = 0, fail = 0;
        for (Function f : currentProgram.getFunctionManager().getFunctions(true)) {
            long e = f.getEntryPoint().getOffset();
            if (e < lo || e >= hi) continue;
            if (monitor.isCancelled()) break;
            long blk = e & ~0xFFFFL;
            PrintWriter out = blocks.get(blk);
            if (out == null) {
                out = new PrintWriter(new FileWriter(new File(dir, String.format("%s_%08X.c", prefix, blk))));
                blocks.put(blk, out);
            }
            DecompileResults r = di.decompileFunction(f, 60, monitor);
            out.println("// ==== " + f.getName() + " @ " + f.getEntryPoint() + " ====");
            if (r.decompileCompleted()) out.println(r.getDecompiledFunction().getC());
            else { out.println("// Fehler: " + r.getErrorMessage() + "\n"); fail++; }
            int callers = f.getCallingFunctions(monitor).size();
            idx.printf("%08X\t%s\t%d\t%d\t%s%n", e, f.getName(), f.getBody().getNumAddresses(), callers,
                       f.getPrototypeString(false, false));
            if (++n % 500 == 0) println("DecompileAll " + prefix + ": " + n);
        }
        for (PrintWriter w : blocks.values()) w.close();
        idx.close();
        println("DecompileAll " + prefix + ": " + n + " Funktionen, " + fail + " Fehler");
    }
}
