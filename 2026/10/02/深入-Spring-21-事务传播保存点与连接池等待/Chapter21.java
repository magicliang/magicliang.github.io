package blog.spring;

import static blog.spring.Checks.*;
import com.zaxxer.hikari.HikariDataSource;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.transaction.CannotCreateTransactionException;
import org.springframework.transaction.TransactionDefinition;
import org.springframework.transaction.UnexpectedRollbackException;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import org.springframework.transaction.support.TransactionTemplate;

public class Chapter21 {
    static final String TABLE = "spring_ch21_rows";
    static class Abort extends RuntimeException {}
    static TransactionTemplate template(DataSourceTransactionManager manager, int propagation) {
        var template = new TransactionTemplate(manager);
        template.setPropagationBehavior(propagation);
        template.setTimeout(10);
        return template;
    }
    static void put(JdbcTemplate jdbc, String label) {
        jdbc.update("insert into " + TABLE + " values (?)", label);
        System.out.println("INSERT " + label + " thread=" + Thread.currentThread().getName());
    }
    static void await(CountDownLatch latch, String name) {
        try { if (!latch.await(8, TimeUnit.SECONDS)) throw new AssertionError("deadline " + name); }
        catch (InterruptedException failure) { Thread.currentThread().interrupt(); throw new IllegalStateException(failure); }
    }
    static void propagation() {
        try (var pool = LabDatabase.pool("ch21-propagation", 2)) {
            var jdbc = new JdbcTemplate(pool);
            var manager = new DataSourceTransactionManager(pool);
            var required = template(manager, TransactionDefinition.PROPAGATION_REQUIRED);
            var independent = template(manager, TransactionDefinition.PROPAGATION_REQUIRES_NEW);
            var nested = template(manager, TransactionDefinition.PROPAGATION_NESTED);
            fails(UnexpectedRollbackException.class, () -> required.executeWithoutResult(outer -> {
                long[] before = TxChapterSupport.identity(jdbc, "required/outer");
                put(jdbc, "required-outer");
                try { required.executeWithoutResult(inner -> {
                    check(Arrays.equals(before, TxChapterSupport.identity(jdbc, "required/inner")), "REQUIRED shares physical connection and transaction");
                    put(jdbc, "required-inner");
                    throw new Abort();
                }); } catch (Abort expected) { System.out.println("CAUGHT inner REQUIRED"); }
                check(outer.isRollbackOnly(), "inner REQUIRED failure marks outer rollback-only");
            }), "normal outer callback return still causes UnexpectedRollbackException");
            check(TxChapterSupport.rows(TABLE).isEmpty(), "REQUIRED rolls back both rows");

            fails(Abort.class, () -> required.executeWithoutResult(outer -> {
                long[] before = TxChapterSupport.identity(jdbc, "new/outer");
                put(jdbc, "new-outer");
                independent.executeWithoutResult(inner -> {
                    long[] inside = TxChapterSupport.identity(jdbc, "new/inner");
                    check(before[0] != inside[0] && before[1] != inside[1], "REQUIRES_NEW uses independent connection and transaction");
                    put(jdbc, "new-inner");
                });
                check(Arrays.equals(before, TxChapterSupport.identity(jdbc, "new/resumed")), "outer physical transaction resumes unchanged");
                check(TxChapterSupport.rows(TABLE).equals(List.of("new-inner")), "independent observer sees inner commit before outer finishes");
                throw new Abort();
            }), "outer failure after independent inner commit");
            check(TxChapterSupport.rows(TABLE).equals(List.of("new-inner")), "REQUIRES_NEW inner commit survives outer rollback");
            TxChapterSupport.sql("truncate " + TABLE);

            required.executeWithoutResult(outer -> {
                long[] before = TxChapterSupport.identity(jdbc, "nested/outer");
                put(jdbc, "nested-outer");
                try { nested.executeWithoutResult(inner -> {
                    check(inner.hasSavepoint(), "NESTED status owns a savepoint");
                    check(Arrays.equals(before, TxChapterSupport.identity(jdbc, "nested/inner")), "NESTED shares outer physical transaction");
                    put(jdbc, "nested-inner");
                    throw new Abort();
                }); } catch (Abort expected) { System.out.println("CAUGHT inner NESTED"); }
                check(!outer.isRollbackOnly(), "savepoint rollback does not mark outer rollback-only");
                check(TxChapterSupport.rows(TABLE).isEmpty(), "observer sees no uncommitted outer data");
                put(jdbc, "nested-after");
            });
            check(TxChapterSupport.rows(TABLE).equals(List.of("nested-after", "nested-outer")), "NESTED removes inner row and commits outer rows");
            TxChapterSupport.sql("truncate " + TABLE);
            fails(Abort.class, () -> required.executeWithoutResult(outer -> {
                nested.executeWithoutResult(inner -> put(jdbc, "nested-success"));
                throw new Abort();
            }), "outer abort after successful nested scope");
            check(TxChapterSupport.rows(TABLE).isEmpty(), "successful NESTED is not an independent durable commit");
            check(pool.getHikariPoolMXBean().getActiveConnections() == 0, "propagation pool returned all connections");
            check(!TransactionSynchronizationManager.isActualTransactionActive(), "propagation thread state cleared");
        }
    }
    static void poolCase(int capacity, boolean expectTimeout) throws Exception {
        TxChapterSupport.sql("truncate " + TABLE);
        var ready = new CountDownLatch(2);
        var start = new CountDownLatch(1);
        var attempted = new CountDownLatch(2);
        var release = new CountDownLatch(1);
        var failures = new AtomicInteger();
        var successes = new AtomicInteger();
        ExecutorService workers = Executors.newFixedThreadPool(2);
        try (var pool = LabDatabase.pool("ch21-capacity-" + capacity, capacity)) {
            var jdbc = new JdbcTemplate(pool);
            var manager = new DataSourceTransactionManager(pool);
            var required = template(manager, TransactionDefinition.PROPAGATION_REQUIRED);
            var independent = template(manager, TransactionDefinition.PROPAGATION_REQUIRES_NEW);
            Future<?>[] futures = new Future<?>[2];
            try {
                for (int index = 0; index < 2; index++) {
                    final int id = index;
                    futures[index] = workers.submit(() -> {
                        try {
                            required.executeWithoutResult(outer -> {
                                TxChapterSupport.identity(jdbc, "pool/outer-" + id);
                                put(jdbc, "pool-outer-" + id);
                                ready.countDown();
                                await(start, "start inner");
                                long began = System.nanoTime();
                                try {
                                    independent.executeWithoutResult(inner -> {
                                        TxChapterSupport.identity(jdbc, "pool/inner-" + id);
                                        put(jdbc, "pool-inner-" + id);
                                    });
                                    successes.incrementAndGet();
                                } catch (CannotCreateTransactionException failure) {
                                    failures.incrementAndGet();
                                    System.out.println("ACQUIRE TIMEOUT worker=" + id + " elapsedMs="
                                            + TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - began)
                                            + " cause=" + failure.getMostSpecificCause());
                                } finally { attempted.countDown(); }
                                await(release, "release outer");
                                throw new Abort();
                            });
                        } catch (Abort expected) { System.out.println("OUTER ROLLBACK worker=" + id); }
                        check(!TransactionSynchronizationManager.isActualTransactionActive(), "worker transaction state cleared " + id);
                    });
                }
                await(ready, "both outer connections held");
                check(pool.getHikariPoolMXBean().getActiveConnections() == 2, "two outer transactions hold connections at barrier");
                start.countDown();
                if (expectTimeout) {
                    long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(1);
                    while (pool.getHikariPoolMXBean().getThreadsAwaitingConnection() != 2 && System.nanoTime() < deadline) Thread.sleep(5);
                    System.out.println("POOL capacity=" + capacity + " active=" + pool.getHikariPoolMXBean().getActiveConnections()
                            + " waiting=" + pool.getHikariPoolMXBean().getThreadsAwaitingConnection());
                    check(pool.getHikariPoolMXBean().getThreadsAwaitingConnection() == 2, "both inner transactions wait while outer connections remain borrowed");
                }
                await(attempted, "both inner attempts finish");
                check(failures.get() == (expectTimeout ? 2 : 0), "expected acquisition timeout count capacity=" + capacity);
                check(successes.get() == (expectTimeout ? 0 : 2), "expected inner commit count capacity=" + capacity);
                release.countDown();
                for (var future : futures) future.get(8, TimeUnit.SECONDS);
                check(pool.getHikariPoolMXBean().getActiveConnections() == 0, "pool active connections return to zero capacity=" + capacity);
                check(pool.getHikariPoolMXBean().getThreadsAwaitingConnection() == 0, "pool waiters return to zero capacity=" + capacity);
                check(TxChapterSupport.rows(TABLE).equals(expectTimeout ? List.of() : List.of("pool-inner-0", "pool-inner-1")), "database terminal state capacity=" + capacity);
                required.executeWithoutResult(status -> put(jdbc, "recovery"));
                check(TxChapterSupport.rows(TABLE).contains("recovery"), "pool serves a fresh transaction after scenario capacity=" + capacity);
            } finally {
                start.countDown(); release.countDown();
                for (var future : futures) if (future != null && !future.isDone()) future.cancel(true);
                workers.shutdownNow();
                check(workers.awaitTermination(8, TimeUnit.SECONDS), "worker executor terminated");
            }
        } finally { workers.shutdownNow(); }
    }
    public static void main(String[] args) throws Exception {
        TxChapterSupport.sql("create table if not exists " + TABLE + "(label text primary key)");
        TxChapterSupport.sql("truncate " + TABLE);
        try { propagation(); poolCase(2, true); poolCase(3, false); }
        finally { TxChapterSupport.sql("drop table if exists " + TABLE); }
    }
}
