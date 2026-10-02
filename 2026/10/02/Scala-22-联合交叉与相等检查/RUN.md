# Chapter 22 rerun

Status: LAB_VERIFIED (Scala 3.3.7, Scala CLI 1.9.1, JDK 21.0.11-amzn).

From repository root:

```bash
export SCALA_LAB_JAVA_HOME=/Users/magicliang/.sdkman/candidates/java/21.0.11-amzn
python3 examples/scala-lab/run.py chapter 22 --run-id local-ch22
python3 examples/scala-lab/run.py negative 22 --run-id local-ch22
```

Source: examples/scala-lab/snippets/22/Chapter22.scala.
Negative cases: examples/scala-lab/negative/22/{intersection,strict-equality,union-member}.

Captured original command/exit/output: examples/scala-lab/evidence/20261002-ch22/22.json and 22.log; negative-22-*.json and .log.
Expected: positive exit 0 with assertions; each negative exit nonzero and all case.json patterns matched. strict-equality separately enables -language:strictEquality.

No claim of universal generic runtime discrimination or deep immutability is made.
