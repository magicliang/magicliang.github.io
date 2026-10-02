package blog.spring;

import static blog.spring.Checks.*;
import com.zaxxer.hikari.HikariDataSource;
import java.util.List;
import org.springframework.context.annotation.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.transaction.UnexpectedRollbackException;
import org.springframework.transaction.annotation.*;
import org.springframework.transaction.interceptor.TransactionAspectSupport;
import org.springframework.transaction.support.TransactionSynchronizationManager;

public class Chapter22 {
    static class BusinessException extends Exception {}
    static class BusinessRuntime extends RuntimeException {}
    public static class Inner {
        private final JdbcTemplate jdbc;
        Inner(JdbcTemplate jdbc) { this.jdbc = jdbc; }
        @Transactional public void fail() {
            jdbc.update("insert into spring_ch22_rows values ('inner')");
            throw new BusinessRuntime();
        }
    }
    public static class Service {
        private final JdbcTemplate jdbc;
        private final Inner inner;
        Service(JdbcTemplate jdbc, Inner inner) { this.jdbc = jdbc; this.inner = inner; }
        void put(String label) {
            TxChapterSupport.identity(jdbc, label);
            jdbc.update("insert into spring_ch22_rows values (?)", label);
        }
        @Transactional public void runtime() { put("runtime"); throw new BusinessRuntime(); }
        @Transactional public void checked() throws BusinessException { put("checked"); throw new BusinessException(); }
        @Transactional(rollbackFor = BusinessException.class)
        public void explicitChecked() throws BusinessException { put("explicitChecked"); throw new BusinessException(); }
        @Transactional(noRollbackFor = BusinessRuntime.class)
        public void noRuntime() { put("noRuntime"); throw new BusinessRuntime(); }
        @Transactional(rollbackFor = Exception.class, noRollbackFor = BusinessException.class)
        public void specificNo() throws BusinessException { put("specificNo"); throw new BusinessException(); }
        @Transactional public void caughtLocal() {
            put("caughtLocal");
            try { throw new BusinessRuntime(); }
            catch (BusinessRuntime expected) { System.out.println("CAUGHT before transaction interceptor"); }
        }
        @Transactional public void caughtInner() {
            put("outer");
            try { inner.fail(); }
            catch (BusinessRuntime expected) { System.out.println("CAUGHT after inner transaction interceptor"); }
            check(TransactionAspectSupport.currentTransactionStatus().isRollbackOnly(), "inner REQUIRED has already marked shared transaction rollback-only");
        }
        @Transactional public void localRollbackOnly() {
            put("localRollbackOnly");
            TransactionAspectSupport.currentTransactionStatus().setRollbackOnly();
        }
    }
    @Configuration(proxyBeanMethods = false)
    static class Beans {
        @Bean(destroyMethod = "close") HikariDataSource dataSource() { return LabDatabase.pool("ch22", 2); }
        @Bean DataSourceTransactionManager transactionManager(HikariDataSource dataSource) { return new DataSourceTransactionManager(dataSource); }
        @Bean JdbcTemplate jdbc(HikariDataSource dataSource) { return new JdbcTemplate(dataSource); }
        @Bean Inner inner(JdbcTemplate jdbc) { return new Inner(jdbc); }
        @Bean Service service(JdbcTemplate jdbc, Inner inner) { return new Service(jdbc, inner); }
    }
    @Configuration(proxyBeanMethods = false) @Import(Beans.class) @EnableTransactionManagement
    static class DefaultConfig {}
    @Configuration(proxyBeanMethods = false) @Import(Beans.class)
    @EnableTransactionManagement(rollbackOn = RollbackOn.ALL_EXCEPTIONS)
    static class AllConfig {}
    @FunctionalInterface interface CheckedAction { void run() throws BusinessException; }
    static void checkedFailure(CheckedAction action) {
        try { action.run(); throw new AssertionError("expected BusinessException"); }
        catch (BusinessException expected) { check(true, "checked exception escapes proxy"); }
    }
    static void terminal(List<String> expected) {
        check(TxChapterSupport.rows("spring_ch22_rows").equals(expected), "independent observer expected rows " + expected);
        check(!TransactionSynchronizationManager.isActualTransactionActive(), "caller transaction state cleaned");
    }
    public static void main(String[] args) {
        TxChapterSupport.sql("create table if not exists spring_ch22_rows(label text primary key)");
        TxChapterSupport.sql("truncate spring_ch22_rows");
        try {
            try (var context = new AnnotationConfigApplicationContext(DefaultConfig.class)) {
                var service = context.getBean(Service.class);
                fails(BusinessRuntime.class, service::runtime, "default RuntimeException rolls back"); terminal(List.of());
                checkedFailure(service::checked); terminal(List.of("checked"));
                checkedFailure(service::explicitChecked); terminal(List.of("checked"));
                fails(BusinessRuntime.class, service::noRuntime, "explicit noRollbackFor commits despite exception"); terminal(List.of("checked", "noRuntime"));
                checkedFailure(service::specificNo); terminal(List.of("checked", "noRuntime", "specificNo"));
                service.caughtLocal(); terminal(List.of("caughtLocal", "checked", "noRuntime", "specificNo"));
                fails(UnexpectedRollbackException.class, service::caughtInner, "catching inner exception cannot clear rollback-only"); terminal(List.of("caughtLocal", "checked", "noRuntime", "specificNo"));
                service.localRollbackOnly(); terminal(List.of("caughtLocal", "checked", "noRuntime", "specificNo"));
                check(context.getBean(HikariDataSource.class).getHikariPoolMXBean().getActiveConnections() == 0, "default scenarios return all pooled connections");
            }
            TxChapterSupport.sql("truncate spring_ch22_rows");
            try (var context = new AnnotationConfigApplicationContext(AllConfig.class)) {
                var service = context.getBean(Service.class);
                checkedFailure(service::checked); terminal(List.of());
                checkedFailure(service::specificNo); terminal(List.of("specificNo"));
                check(context.getBean(HikariDataSource.class).getHikariPoolMXBean().getActiveConnections() == 0, "ALL_EXCEPTIONS scenarios return all pooled connections");
            }
        } finally { TxChapterSupport.sql("drop table if exists spring_ch22_rows"); }
    }
}
