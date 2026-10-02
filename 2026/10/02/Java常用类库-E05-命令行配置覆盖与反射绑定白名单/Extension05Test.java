package blog.libraries;

import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import org.apache.commons.beanutils.BeanUtilsBean;
import org.apache.commons.beanutils.ConvertUtilsBean;
import org.apache.commons.beanutils.ConversionException;
import org.apache.commons.beanutils.converters.IntegerConverter;
import org.apache.commons.cli.CommandLine;
import org.apache.commons.cli.DefaultParser;
import org.apache.commons.cli.MissingOptionException;
import org.apache.commons.cli.Option;
import org.apache.commons.cli.Options;
import org.apache.commons.cli.UnrecognizedOptionException;
import org.apache.commons.configuration2.BaseConfiguration;
import org.apache.commons.configuration2.CompositeConfiguration;
import org.apache.commons.configuration2.convert.DefaultListDelimiterHandler;
import org.apache.commons.configuration2.interpol.ConfigurationInterpolator;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class Extension05Test {
    public static class ImportConfig {
        private int count;
        private boolean admin;
        public int getCount() { return count; }
        public void setCount(int count) { this.count = count; }
        public boolean isAdmin() { return admin; }
        public void setAdmin(boolean admin) { this.admin = admin; }
    }

    @Test
    void tokensAreAlreadySeparatedAndUnknownOrMissingOptionsFail() throws Exception {
        Options options = new Options().addOption(Option.builder().longOpt("count").hasArg().required().get())
                .addOption(Option.builder().longOpt("name").hasArg().get());
        DefaultParser parser = DefaultParser.builder().setAllowPartialMatching(false).setStripLeadingAndTrailingQuotes(false).get();
        CommandLine line = parser.parse(options, new String[] {"--count", "7", "--name", "two words"});
        assertEquals("two words", line.getOptionValue("name"));
        assertEquals("'two words'", parser.parse(options, new String[] {"--count", "7", "--name", "'two words'"}).getOptionValue("name"));
        assertEquals("\"two words\"", parser.parse(options, new String[] {"--count=7", "--name=\"two words\""}).getOptionValue("name"));
        assertThrows(MissingOptionException.class, () -> parser.parse(options, new String[] {"--name", "x"}));
        assertThrows(UnrecognizedOptionException.class, () -> parser.parse(options, new String[] {"--count", "7", "--admin"}));
        assertThrows(UnrecognizedOptionException.class, () -> parser.parse(options, new String[] {"--cou", "7"}));
        assertEquals(Arrays.asList("literal", "--admin"), parser.parse(options, new String[] {"--count", "7", "--", "literal", "--admin"}).getArgList());
    }

    @Test
    void precedenceSplittingAndInterpolationAreIndependentPolicies() {
        BaseConfiguration defaults = new BaseConfiguration(); defaults.setProperty("count", "1");
        BaseConfiguration file = new BaseConfiguration(); file.setProperty("count", "2");
        BaseConfiguration cli = new BaseConfiguration(); cli.setProperty("count", "3");
        CompositeConfiguration merged = new CompositeConfiguration();
        merged.addConfiguration(cli); merged.addConfiguration(file); merged.addConfiguration(defaults);
        assertEquals(3, merged.getInt("count")); cli.clearProperty("count"); assertEquals(2, merged.getInt("count"));
        BaseConfiguration lists = new BaseConfiguration();
        lists.setListDelimiterHandler(new DefaultListDelimiterHandler(','));
        lists.addProperty("tags", "a,b\\,c");
        assertEquals(Arrays.asList("a", "b,c"), lists.getList("tags"));
        Map<String, String> allowed = Collections.singletonMap("host", "example.invalid");
        ConfigurationInterpolator resolver = new ConfigurationInterpolator(); resolver.registerLookup("cfg", allowed::get);
        file.setInterpolator(resolver); file.setProperty("url", "https://${cfg:host}");
        assertEquals("https://example.invalid", file.getString("url"));
        file.setProperty("missing", "${cfg:absent}"); file.setProperty("external", "${env:SYNTHETIC_ONLY}");
        assertThrows(IllegalArgumentException.class, () -> resolved(file, "missing"));
        assertThrows(IllegalArgumentException.class, () -> resolved(file, "external"));
    }

    private static String resolved(BaseConfiguration config, String key) {
        String value = config.getString(key);
        if (value == null || value.contains("${")) { throw new IllegalArgumentException("unresolved configuration"); }
        return value;
    }

    private static ImportConfig bind(Map<String, String> external) throws Exception {
        if (!Collections.singleton("count").containsAll(external.keySet())) { throw new IllegalArgumentException("unknown property"); }
        ConvertUtilsBean conversion = new ConvertUtilsBean(); conversion.register(new IntegerConverter(), Integer.TYPE);
        BeanUtilsBean binder = new BeanUtilsBean(conversion);
        ImportConfig candidate = new ImportConfig(); binder.populate(candidate, external);
        if (candidate.getCount() <= 0 || candidate.getCount() > 1000) { throw new IllegalArgumentException("count outside domain"); }
        return candidate;
    }

    @Test
    void whiteListPrecedesReflectionAndConversionDoesNotValidateDomain() throws Exception {
        assertEquals(7, bind(Collections.singletonMap("count", "7")).getCount());
        for (String forbidden : Arrays.asList("admin", "class", "classLoader", "class.classLoader", "count[0]", "admin(value)")) {
            Map<String, String> values = new HashMap<>(); values.put("count", "7"); values.put(forbidden, "synthetic");
            assertThrows(IllegalArgumentException.class, () -> bind(values), forbidden);
        }
        assertThrows(ConversionException.class, () -> bind(Collections.singletonMap("count", "not-a-number")));
        assertThrows(IllegalArgumentException.class, () -> bind(Collections.singletonMap("count", "-1")));
        ImportConfig bean = new ImportConfig(); new BeanUtilsBean().setProperty(bean, "count", "not-a-number");
        assertEquals(0, bean.getCount());
        assertNull(new BeanUtilsBean().getPropertyUtils().getPropertyDescriptor(bean, "class"));
        assertFalse(bean.isAdmin());
    }
}
