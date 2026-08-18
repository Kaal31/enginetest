# EngineTest native runtime (experimental)

This directory is an experimental native layer for EngineTest's Luma-derived runtime work.

## Design

The native layer is deliberately **not** an engine selector and does not replace either engine's launcher/injection contract.

- Moon keeps its existing SLSsteam-moon injection path.
- Luma-derived functionality is loaded only where explicitly requested.
- Common native infrastructure is limited to safe runtime primitives that can be shared without owning engine-specific hook targets.
- No `dlclose()`/binary hot-unload is attempted. Live hook code may be referenced by Steam after installation.

## Current experimental pieces

`hook_runtime/` contains a small, dependency-light implementation of the part of LumaLinux's hook infrastructure that is safe to isolate: detection and relocation of an existing x86/x86-64 `E9 rel32` prologue when a trampoline is created by a second hooker.

It does **not** install hooks itself. The actual hook installation remains owned by the engine that requested it. This prevents EngineTest from becoming a third competing injector.

`runtime_watch/` contains the Linux runtime watcher used for hot configuration/key reload experiments. It watches the containing directory rather than relying on a single file inode, matching LumaLinux's important rename/replace-file behavior.

## LumaLinux provenance

The hook relocation logic is an adaptation of the algorithm in LumaLinux `src/lmhook.cpp`, which is GPLv3. This experimental code is therefore GPLv3-compatible and carries the required attribution in its source header.
