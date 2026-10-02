package blog.libraries;

import com.google.common.util.concurrent.FutureCallback;
import com.google.common.util.concurrent.Futures;
import com.google.common.util.concurrent.ListenableFuture;
import com.google.common.util.concurrent.ListeningExecutorService;
import com.google.common.util.concurrent.MoreExecutors;
import com.google.common.util.concurrent.SettableFuture;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class Chapter16Test {
    @Test void callbacksAndTransformUseTheChosenExecutor() throws Exception {
        ExecutorService callbacks = Executors.newSingleThreadExecutor(r -> new Thread(r, "catalog-callback"));
        try {
            SettableFuture<String> source = SettableFuture.create();
            AtomicReference<String> thread = new AtomicReference<>();
            ListenableFuture<Integer> transformed = Futures.transform(source, value -> {
                thread.set(Thread.currentThread().getName());
                return value.length();
            }, callbacks);
            source.set("SKU-1");
            assertEquals(5, transformed.get(5, TimeUnit.SECONDS));
            assertEquals("catalog-callback", thread.get());
            CountDownLatch done = new CountDownLatch(1);
            AtomicReference<Throwable> failure = new AtomicReference<>();
            Futures.addCallback(Futures.<String>immediateFailedFuture(new IllegalArgumentException("bad SKU")),
                    new FutureCallback<String>() {
                        public void onSuccess(String value) { done.countDown(); }
                        public void onFailure(Throwable value) { failure.set(value); done.countDown(); }
                    }, callbacks);
            assertTrue(done.await(5, TimeUnit.SECONDS));
            assertEquals("bad SKU", failure.get().getMessage());
            System.out.println("16 transform=5 thread=" + thread.get() + " callback failure=bad SKU");
        } finally { callbacks.shutdownNow(); assertTrue(callbacks.awaitTermination(5, TimeUnit.SECONDS)); }
    }

    @Test void directListenerBlocksTheCompletingThread() throws Exception {
        SettableFuture<String> source = SettableFuture.create();
        CountDownLatch entered = new CountDownLatch(1);
        CountDownLatch release = new CountDownLatch(1);
        CountDownLatch setterReturned = new CountDownLatch(1);
        AtomicReference<String> listenerThread = new AtomicReference<>();
        source.addListener(() -> {
            listenerThread.set(Thread.currentThread().getName());
            entered.countDown();
            try { release.await(); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
        }, MoreExecutors.directExecutor());
        Thread setter = new Thread(() -> { source.set("SKU-1"); setterReturned.countDown(); }, "catalog-setter");
        setter.start();
        try {
            assertTrue(entered.await(5, TimeUnit.SECONDS));
            assertTrue(source.isDone());
            assertEquals(1, setterReturned.getCount());
            assertEquals("catalog-setter", listenerThread.get());
            release.countDown();
            assertTrue(setterReturned.await(5, TimeUnit.SECONDS));
            AtomicReference<String> lateThread = new AtomicReference<>();
            source.addListener(() -> lateThread.set(Thread.currentThread().getName()), MoreExecutors.directExecutor());
            assertEquals(Thread.currentThread().getName(), lateThread.get());
            System.out.println("16 direct: future done -> listener on catalog-setter -> set blocked -> release -> set returned; late=" + lateThread.get());
        } finally { release.countDown(); setter.join(5000); assertFalse(setter.isAlive()); }
    }

    @Test void transformedCancellationAndRejectionAreObservable() throws Exception {
        SettableFuture<String> source = SettableFuture.create();
        ListenableFuture<Integer> transformed = Futures.transform(source, String::length, MoreExecutors.directExecutor());
        assertTrue(transformed.cancel(true));
        assertTrue(source.isCancelled());
        ListenableFuture<Integer> rejected = Futures.transform(Futures.immediateFuture("SKU-1"), String::length,
                task -> { throw new RejectedExecutionException("full"); });
        assertInstanceOf(RejectedExecutionException.class,
                assertThrows(ExecutionException.class, () -> rejected.get(5, TimeUnit.SECONDS)).getCause());
        System.out.println("16 transform cancel propagates upstream; executor rejection -> failed output future");
    }

    @Test void taskFutureInterruptAndCompletableCancellationDiffer() throws Exception {
        ListeningExecutorService guava = MoreExecutors.listeningDecorator(Executors.newSingleThreadExecutor());
        ExecutorService standard = Executors.newSingleThreadExecutor();
        CountDownLatch started = new CountDownLatch(1), interrupted = new CountDownLatch(1);
        CountDownLatch modernStarted = new CountDownLatch(1), modernRelease = new CountDownLatch(1);
        CompletableFuture<Boolean> observedInterrupt = new CompletableFuture<>();
        try {
            ListenableFuture<String> task = guava.submit(() -> {
                started.countDown();
                try { new CountDownLatch(1).await(); }
                catch (InterruptedException e) { interrupted.countDown(); throw e; }
                return "unreachable";
            });
            assertTrue(started.await(5, TimeUnit.SECONDS));
            assertTrue(task.cancel(true));
            assertTrue(interrupted.await(5, TimeUnit.SECONDS));
            CompletableFuture<String> modern = CompletableFuture.supplyAsync(() -> {
                modernStarted.countDown();
                try { modernRelease.await(); observedInterrupt.complete(Thread.currentThread().isInterrupted()); }
                catch (InterruptedException e) { observedInterrupt.complete(true); Thread.currentThread().interrupt(); }
                return "done";
            }, standard);
            assertTrue(modernStarted.await(5, TimeUnit.SECONDS));
            assertTrue(modern.cancel(true));
            modernRelease.countDown();
            assertFalse(observedInterrupt.get(5, TimeUnit.SECONDS));
            System.out.println("16 cancel(true): Guava submitted blocking task interrupted; CompletableFuture supplier not interrupted");
        } finally {
            modernRelease.countDown(); guava.shutdownNow(); standard.shutdownNow();
            assertTrue(guava.awaitTermination(5, TimeUnit.SECONDS)); assertTrue(standard.awaitTermination(5, TimeUnit.SECONDS));
        }
    }
}
