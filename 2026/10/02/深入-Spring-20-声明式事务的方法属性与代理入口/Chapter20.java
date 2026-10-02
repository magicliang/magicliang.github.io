package blog.spring;

import static blog.spring.Checks.check;
import com.zaxxer.hikari.HikariDataSource;
import javax.sql.DataSource;
import org.springframework.aop.support.AopUtils;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.context.annotation.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.transaction.annotation.*;
import org.springframework.transaction.interceptor.TransactionAttributeSource;
import org.springframework.transaction.support.TransactionSynchronizationManager;

public class Chapter20 {
    public interface Api { boolean defaults(); boolean override(); }
    @Transactional(transactionManager = "primaryTx", readOnly = true, timeout = 9)
    public static class Service implements Api {
        private final DataSource primary;
        private final DataSource secondary;
        Service(DataSource primary, DataSource secondary) { this.primary = primary; this.secondary = secondary; }
        public boolean defaults() {
            TxChapterSupport.identity(new JdbcTemplate(primary), "primary/class");
            return TransactionSynchronizationManager.isCurrentTransactionReadOnly()
                    && TransactionSynchronizationManager.hasResource(primary)
                    && !TransactionSynchronizationManager.hasResource(secondary);
        }
        @Transactional(transactionManager = "secondaryTx")
        public boolean override() {
            var jdbc = new JdbcTemplate(secondary);
            TxChapterSupport.identity(jdbc, "secondary/method");
            jdbc.update("insert into spring_ch20_rows values ('method')");
            return !TransactionSynchronizationManager.isCurrentTransactionReadOnly()
                    && TransactionSynchronizationManager.hasResource(secondary)
                    && !TransactionSynchronizationManager.hasResource(primary);
        }
    }
    public static class Visibility {
        @Transactional("primaryTx") public boolean external() { return active(); }
        public boolean self() { return external(); }
        @Transactional("primaryTx") protected boolean protectedCall() { return active(); }
        @Transactional("primaryTx") boolean packageCall() { return active(); }
        @Transactional("primaryTx") private boolean privateCall() { return active(); }
        public boolean reachPrivate() { return privateCall(); }
        static boolean active() { return TransactionSynchronizationManager.isActualTransactionActive(); }
    }
    @Configuration(proxyBeanMethods = false)
    static class Beans {
        @Bean(destroyMethod = "close") HikariDataSource primary() { return LabDatabase.pool("ch20-primary", 2); }
        @Bean(destroyMethod = "close") HikariDataSource secondary() { return LabDatabase.pool("ch20-secondary", 2); }
        @Bean DataSourceTransactionManager primaryTx(@Qualifier("primary") DataSource ds) { return new DataSourceTransactionManager(ds); }
        @Bean DataSourceTransactionManager secondaryTx(@Qualifier("secondary") DataSource ds) { return new DataSourceTransactionManager(ds); }
        @Bean Service service(@Qualifier("primary") DataSource a, @Qualifier("secondary") DataSource b) { return new Service(a, b); }
        @Bean Visibility visibility() { return new Visibility(); }
    }
    @Configuration(proxyBeanMethods = false) @Import(Beans.class)
    @EnableTransactionManagement(proxyTargetClass = true)
    static class ClassConfig {}
    @Configuration(proxyBeanMethods = false) @Import(Beans.class)
    @EnableTransactionManagement(proxyTargetClass = false)
    static class JdkConfig {}
    public static void main(String[] args) throws Exception {
        TxChapterSupport.sql("create table if not exists spring_ch20_rows(label text)");
        TxChapterSupport.sql("truncate spring_ch20_rows");
        try {
            for (Class<?> config : new Class<?>[] {ClassConfig.class, JdkConfig.class}) {
                try (var context = new AnnotationConfigApplicationContext(config)) {
                    var service = context.getBean(Api.class);
                    boolean classProxy = config == ClassConfig.class;
                    check(classProxy ? AopUtils.isCglibProxy(service) : AopUtils.isJdkDynamicProxy(service), "proxy kind " + config.getSimpleName());
                    check(service.defaults(), "class metadata selects primary read-only transaction");
                    check(service.override(), "method metadata selects secondary read-write transaction");
                    var source = context.getBean(TransactionAttributeSource.class);
                    var defaults = source.getTransactionAttribute(Api.class.getMethod("defaults"), Service.class);
                    var override = source.getTransactionAttribute(Api.class.getMethod("override"), Service.class);
                    System.out.println("ATTRIBUTE defaults=" + defaults + " override=" + override);
                    check(defaults.getTimeout() == 9 && override.getTimeout() == -1, "method annotation replaces class attributes instead of field-wise merge");
                    var visibility = context.getBean(Visibility.class);
                    check(visibility.external(), "external public call enters transaction");
                    check(!visibility.self(), "this call bypasses transaction interceptor");
                    check(visibility.protectedCall(), "protected method on class proxy is transactional");
                    check(visibility.packageCall(), "same-package method on class proxy is transactional");
                    check(!visibility.reachPrivate(), "private this call is not transactional");
                    check(AopUtils.isCglibProxy(visibility), "interface-free bean still uses class proxy");
                    check(!Visibility.active(), "caller thread transaction state cleaned");
                }
            }
            check(TxChapterSupport.rows("spring_ch20_rows").size() == 2, "independent observer sees both committed method writes");
        } finally { TxChapterSupport.sql("drop table if exists spring_ch20_rows"); }
    }
}
