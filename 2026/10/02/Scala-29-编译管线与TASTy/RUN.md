# Chapter 29 rerun
Status: LAB_VERIFIED. Scala 3.3.7 / Scala CLI 1.9.1 / sbt 1.11.7 / Corretto 21.0.11.
Set SCALA_LAB_JAVA_HOME to JDK 21. SCALA_LAB_CLI_JAR optionally selects the frozen CLI JAR.

```bash
python3 examples/scala-lab/run.py chapter 29 --run-id local-ch29
python3 examples/scala-lab/run.py negative 29 --run-id local-ch29
python3 examples/scala-lab/modules/29/run.py --run-id local-ch29-module
```

Source: snippets/29, negative/29 and modules/29 under examples/scala-lab.
Evidence: examples/scala-lab/evidence/20261002-ch29/29.json/.log and negative-29-*; full final module evidence examples/scala-lab/evidence/20261002-ch29-module-r2/.
The module copies the two-project build to a temporary directory, runs clean compile and output42, body change output63, signature-change rejection, adapted output63, then phases/trees/TASTy/javap. Each scenario has command/cwd/exit JSON and raw log. incremental.json records app hashes and compile lines. tasty.json records nonempty emitted TASTy metadata; no complete TASTy decoding is claimed. Shared download/tool caches remain in use during the clean project build.

