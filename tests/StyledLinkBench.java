import net.sf.saxon.Version;
import net.sf.saxon.s9api.*;
import javax.xml.transform.stream.StreamSource;
import java.io.File;
import java.io.StringWriter;
import java.lang.management.ManagementFactory;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;

/** Execute generated mapping modes; parsing, compilation and serialization are
 * outside the transform timer. Allocation is transform-thread churn, not heap. */
public class StyledLinkBench {
    static final Processor processor = new Processor(false);
    static final Map<QName, XdmValue> parameters = new HashMap<>();

    static XdmNode transform(XsltExecutable sheet, XdmNode document, String mode) throws Exception {
        XsltTransformer transformer = sheet.load();
        transformer.setInitialContextNode(document);
        transformer.setInitialMode(new QName(mode));
        for (var entry : parameters.entrySet()) {
            transformer.setParameter(entry.getKey(), entry.getValue());
        }
        XdmDestination destination = new XdmDestination();
        destination.setBaseURI(document.getBaseURI());
        transformer.setBaseOutputURI(document.getBaseURI().toString());
        transformer.setDestination(destination);
        transformer.transform();
        return destination.getXdmNode();
    }

    static long allocation() {
        var bean = (com.sun.management.ThreadMXBean) ManagementFactory.getThreadMXBean();
        return bean.getThreadAllocatedBytes(Thread.currentThread().getId());
    }

    static long gcMilliseconds() {
        long total = 0;
        for (var bean : ManagementFactory.getGarbageCollectorMXBeans()) {
            total += bean.getCollectionTime();
        }
        return total;
    }

    static long highWaterRSS() throws Exception {
        for (String line : Files.readAllLines(Path.of("/proc/self/status"))) {
            if (line.startsWith("VmHWM:")) {
                return Long.parseLong(line.replaceAll("[^0-9]", ""));
            }
        }
        return -1;
    }

    public static void main(String[] args) throws Exception {
        System.setProperty("xml.catalog.files", "/opt/transpect/xmlcatalog/catalog.xml");
        var compiler = processor.newXsltCompiler();
        compiler.setURIResolver(new org.xmlresolver.Resolver());
        long compileStart = System.nanoTime();
        var sheet = compiler.compile(new StreamSource(new File(args[0])));
        double compileSeconds = (System.nanoTime() - compileStart) / 1e9;
        var builder = processor.newDocumentBuilder();
        var document = builder.build(new StreamSource(new File(args[1])));
        var xpath = processor.newXPathCompiler();
        xpath.declareNamespace("c", "http://www.w3.org/ns/xproc-step");
        var parameterDocument = builder.build(new StreamSource(new File("/scout/pipeline/params.xml")));
        for (var item : xpath.evaluate("//c:param", parameterDocument)) {
            var node = (XdmNode) item;
            parameters.put(new QName(node.getAttributeValue(new QName("name"))),
                    new XdmAtomicValue(node.getAttributeValue(new QName("value"))));
        }
        String mode = args.length > 4 ? args[4] : "xml2tex";
        if (mode.equals("xml2tex")) {
            document = transform(sheet, document, "escape-bad-chars");
        }
        int repetitions = Integer.parseInt(args[2]);
        for (int run = 0; run < repetitions; run++) {
            long allocationStart = allocation();
            long gcStart = gcMilliseconds();
            long start = System.nanoTime();
            var result = transform(sheet, document, mode);
            double seconds = (System.nanoTime() - start) / 1e9;
            long allocated = allocation() - allocationStart;
            long gcMillis = gcMilliseconds() - gcStart;
            String output = result.getStringValue();
            if (!mode.equals("xml2tex")) {
                StringWriter buffer = new StringWriter();
                Serializer serializer = processor.newSerializer(buffer);
                serializer.setOutputProperty(Serializer.Property.METHOD, "xml");
                serializer.serializeNode(result);
                output = buffer.toString();
            }
            Files.writeString(Path.of(args[3]), output);
            System.out.printf(Locale.ROOT,
                    "{\"engine\":\"%s\",\"run\":%d,\"wall_s\":%.6f,\"thread_alloc_bytes\":%d,"
                    + "\"gc_ms\":%d,\"hwm_kib\":%d,\"compile_s\":%.6f,\"chars\":%d}%n",
                    Version.getProductVersion(), run, seconds, allocated, gcMillis,
                    highWaterRSS(), compileSeconds, output.length());
            System.out.flush();
        }
    }
}
