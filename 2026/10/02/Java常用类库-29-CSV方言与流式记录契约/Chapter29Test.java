package blog.libraries;

import java.io.ByteArrayInputStream;
import java.io.InputStreamReader;
import java.io.Reader;
import java.io.StringReader;
import java.io.StringWriter;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.Iterator;
import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVParser;
import org.apache.commons.csv.CSVPrinter;
import org.apache.commons.csv.CSVRecord;
import org.apache.commons.csv.DuplicateHeaderMode;
import org.apache.commons.io.input.BOMInputStream;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class Chapter29Test {
    private static CSVFormat format() {
        return CSVFormat.RFC4180.builder().setHeader().setSkipHeaderRecord(true)
                .setAllowMissingColumnNames(false).setDuplicateHeaderMode(DuplicateHeaderMode.DISALLOW).get();
    }

    @Test
    void streamingRoundTripPreservesFieldsNotSourceBytes() throws Exception {
        String input = "sku,label,note\r\nA,\"sale,new\",\"line1\nline2\"\r\nB,\"quote\"\"inside\",\r\n";
        StringWriter output = new StringWriter();
        try (CSVParser parser = format().parse(new StringReader(input));
             CSVPrinter printer = new CSVPrinter(output, CSVFormat.RFC4180.builder().setHeader("sku", "label", "note").get())) {
            int count = 0;
            for (CSVRecord record : parser) {
                assertTrue(record.isConsistent());
                printer.printRecord(record);
                count++;
            }
            assertEquals(2, count);
        }
        try (CSVParser parser = format().parse(new StringReader(output.toString()))) {
            Iterator<CSVRecord> records = parser.iterator();
            CSVRecord first = records.next();
            assertEquals("sale,new", first.get("label"));
            assertEquals("line1\nline2", first.get("note"));
            CSVRecord second = records.next();
            assertEquals("quote\"inside", second.get("label"));
            assertEquals("", second.get("note"));
            assertFalse(records.hasNext());
        }
    }

    @Test
    void bomAndHeaderPolicyAreExplicit() throws Exception {
        byte[] bytes = "\ufeffsku,price\r\nA,100\r\n".getBytes(StandardCharsets.UTF_8);
        try (Reader reader = new InputStreamReader(BOMInputStream.builder()
                .setInputStream(new ByteArrayInputStream(bytes)).get(), StandardCharsets.UTF_8);
             CSVParser parser = format().parse(reader)) {
            assertEquals(Arrays.asList("sku", "price"), parser.getHeaderNames());
            assertEquals("100", parser.iterator().next().get("price"));
        }
        assertThrows(IllegalArgumentException.class, () -> format().parse(new StringReader("sku,sku\nA,B\n")));
        assertThrows(IllegalArgumentException.class, () -> format().parse(new StringReader("sku,\nA,B\n")));
    }

    @Test
    void unevenRowsAndUnclosedQuotesHaveDifferentDiagnostics() throws Exception {
        try (CSVParser parser = format().parse(new StringReader("sku,price\nA\n"))) {
            CSVRecord record = parser.iterator().next();
            assertFalse(record.isConsistent());
            assertEquals(1, record.getRecordNumber());
            assertThrows(IllegalArgumentException.class, () -> record.get("price"));
        }
        try (CSVParser parser = format().parse(new StringReader("sku,price\nA,\"unfinished\n"))) {
            RuntimeException failure = assertThrows(RuntimeException.class, () -> parser.iterator().hasNext());
            assertTrue(failure.getMessage().contains("line"));
            System.out.println("29 malformed CSV: " + failure.getMessage());
        }
    }

    @Test
    void csvQuotingDoesNotNeutralizeSpreadsheetFormula() throws Exception {
        StringWriter raw = new StringWriter();
        try (CSVPrinter printer = new CSVPrinter(raw, CSVFormat.RFC4180)) {
            printer.printRecord("=1+1");
        }
        assertTrue(raw.toString().startsWith("=1+1"));
        assertEquals("'=1+1", spreadsheetText("=1+1"));
        assertEquals("'-1", spreadsheetText("-1"));
        assertEquals("SKU-1", spreadsheetText("SKU-1"));
    }

    private static String spreadsheetText(String value) {
        return !value.isEmpty() && "=+-@\t\r\n".indexOf(value.charAt(0)) >= 0 ? "'" + value : value;
    }
}
