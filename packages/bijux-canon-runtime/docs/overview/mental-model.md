# mental-model  

**Scope:** Core execution mental model.  
**Audience:** New readers.  
**Guarantees:** One shared mental model.  
**Non-Goals:** Implementation detail.  
Why: This doc exists to record its single responsibility for review.  

## Overview  
Think of a run as a flow that decomposes into ordered steps, each emitting events that become artifacts, and those artifacts define replay.  

```
Flow → Steps → Events → Artifacts → Replay
```

If you can explain that chain, you can explain the system.  
