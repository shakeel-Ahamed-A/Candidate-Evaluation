# Architecture

The system is deliberately staged so the four independent personas cannot inspect each other's conclusions before debate.

```text
                    JOB DESCRIPTION
                           |
                           v
RESUME A ------> PROFILE BUILDER A -----> IMMUTABLE PROFILE A ----+
TRANSCRIPT A -->                    +----> ROLE PROFILE            |
                                                               |
RESUME B ------> PROFILE BUILDER B -----> IMMUTABLE PROFILE B ----+
TRANSCRIPT B -->                    +----> ROLE PROFILE            |
                                                               |
             INDEPENDENT ISOLATION BOUNDARY (per candidate)    |
        +-------------+-------------+-------------+------------+
        |             |             |            |
        v             v             v            v
   Technical      HR/Culture   Hiring Manager  Skeptic
        |             |             |            |
        +-------------+-------------+-------------+
                              |
                     LOCKED EVALUATION PACKET
                              |
                              v
                     3-ROUND DEBATE ENGINE
                              |
                              v
                 NON-LINEAR DECISION ENGINE
                              |
                              v
                    FINAL CANDIDATE REPORT
```

All substantive opinions are evidence-grounded. The persisted profile has an SHA-256 integrity sidecar, and the orchestrator checks that digest before and after each independent agent call.
