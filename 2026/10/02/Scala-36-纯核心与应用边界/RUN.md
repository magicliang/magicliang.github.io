# Chapter 36 rerun
Status: LAB_VERIFIED. Scala3.3.7 / CLI1.9.1 / JDK21.0.11.
Set SCALA_LAB_JAVA_HOME; optionally SCALA_LAB_CLI_JAR.
```bash
python3 examples/scala-lab/run.py chapter 36 --run-id local-ch36
python3 examples/scala-lab/modules/36/run.py --run-id local-ch36-module
```
Source: examples/scala-lab/snippets/36/Chapter36.scala; module runner creates real temporary CSV-like fixtures and executes four subprocesses.
Final pure entry: evidence/20261002-ch36-r2/. Final CLI: evidence/20261002-ch36-module-r3/ under examples/scala-lab.
normal: exit0, stdout accepted=2 total=500, stderr resource=closed.
invalid: exit2, line1 quantity and line2 format errors, resource=closed.
quote-failure: exit3, no successful stdout, quote-error and resource=closed.
missing-file: exit4, io-error and resource=not-acquired.
Each JSON contains exact command/cwd/exit/stdout/stderr. The code distinguishes acquired/closeAttempted/closed, setting closed only after close returns. Source.close failure is not injected in this chapter; Chapter33 covers explicit release exceptions. No input size cap, full CSV quoting, real network, retry or cancellation is claimed.

