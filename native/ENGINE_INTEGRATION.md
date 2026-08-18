# Native engine integration boundary

This branch intentionally separates **engine-owned injection** from **shared runtime infrastructure**.

## Moon

Moon continues to own:

- SLSsteam-moon library and its loader/injection mechanism
- Moon-specific pattern/RVA resolution
- Moon-specific Steam hooks
- Moon-specific manifest/depot/license behavior

EngineTest must not reimplement these in a common injector.

## Luma-derived runtime

The Luma-derived work can provide reusable infrastructure:

1. Safe chained `E9 rel32` trampoline relocation.
2. Linux module discovery / late-load detection.
3. Directory-based runtime configuration/key watching.
4. Build fingerprinting and a future profile lookup layer.
5. Runtime reconciliation hooks that do not require unloading the native library.

Actual Luma-specific Steam hook targets remain an engine-owned layer.

## Hot reload

Safe hot reload means **state/configuration reload**, not `dlclose()` of a library containing live Steam detours.

A hook installed into a Steam function can leave the function's first bytes pointing at code in the hook library. Unloading that library while Steam can still execute the function is unsafe. Therefore this project does not expose an unload/reload operation for live native hook libraries.

Instead:

```text
Steam process
    |
    +-- native hook library remains loaded
    |
    +-- inotify watches config/key directory
    |
    +-- config/key change
    |       |
    |       +--> reload state
    |       +--> reconcile runtime state
    |
    +-- no Steam restart for state-only changes
```

A future true hook replacement mechanism must first restore every patched target to its original bytes, synchronize against concurrent execution, remove/retire trampolines safely, and only then unload the old module. That is deliberately out of scope for this experimental pass.

## Chained hook primitive

`native/hook_runtime/chained_jmp.*` is a small, testable adaptation of LumaLinux's `RelocateChainedJmp` algorithm. It only calculates the corrected `rel32`; the caller remains responsible for memory protection and for the actual hook library's trampoline lifecycle.

This keeps the common layer from taking ownership of Moon or Luma injection.
