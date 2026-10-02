# Chapter 30 rerun
Status: LAB_VERIFIED. Scala3.3.7 / CLI1.9.1 / JDK21.0.11.
Set SCALA_LAB_JAVA_HOME; module supports SCALA_LAB_CLI_JAR.
```bash
python3 examples/scala-lab/run.py chapter 30 --run-id local-ch30
python3 examples/scala-lab/run.py negative 30 --run-id local-ch30
python3 examples/scala-lab/modules/30/run.py --run-id local-ch30-module
```
Sources: snippets/30, negative/30, modules/30 under examples/scala-lab.
Evidence: evidence/20261002-ch30/ and evidence/20261002-ch30-module/ under that lab.
Module explicitly runs javac-library -> scalac-library -> javac-client -> java-client, checks class hashes and javap static signatures. ExplicitNulls.scala runs with -Yexplicit-nulls; default examples remain on default null mode. Raw commands, exit codes, output are stored per stage. Normal shared-view, snapshot, SAM, null/NPE/None assertions and explicit-null compile rejection are distinct checks.

