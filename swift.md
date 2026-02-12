# From Kotlin to macOS native: a 16-week mastery plan

**A backend engineer fluent in Kotlin, Spring Boot, and AWS can reach productive macOS development competence in roughly 16 weeks by leveraging deep structural similarities between Swift and Kotlin, then layering on platform-specific knowledge in deliberate phases.** The two languages share type inference, null-safety idioms, protocol/interface-oriented design, and closure syntax — meaning roughly 40% of Swift will feel immediately familiar. The critical gaps are value-type thinking (structs over classes), ARC memory management (no garbage collector), property wrappers and result builders (which power SwiftUI's declarative magic), and Swift's compiler-enforced actor concurrency model. This plan sequences those gaps into a milestone-driven curriculum, culminating in contributions to Ghostty — a **43,600-star** terminal emulator built in Zig with a Swift/AppKit/Metal macOS frontend.

Each phase ends with a concrete deliverable. The plan favors depth over breadth: you build understanding of *why* things work before moving to the next layer.

---

## Phase 1 — Swift through a Kotlin lens (weeks 1–3)

Your goal in phase 1 is not to "learn Swift" generically but to **remap your Kotlin mental model** to Swift's equivalent (or divergent) constructs, then master the three concepts that have no Kotlin parallel: value semantics, ARC, and result builders.

### Week 1: Language core and the value-type paradigm shift

Start with Apple's free *The Swift Programming Language* book (swift.org/documentation) — skim chapters on basics, control flow, and functions (these map directly from Kotlin), then slow down on **Structures and Classes**. This is the foundational paradigm shift. In Kotlin/JVM, everything lives on the heap as a reference. In Swift, `struct` is the default and preferred type — `Array`, `Dictionary`, `String`, `Int` are all structs, copied on assignment with copy-on-write optimization. Classes exist for identity semantics, Objective-C interop, and inheritance. Internalize the rule: **use structs unless you have a specific reason for a class.**

Pair the Apple book with chapters 1–10 of *Swift Programming: The Big Nerd Ranch Guide* (3rd edition, 2022, by Mikey Ward, ~$45). It's structured for experienced programmers and includes exercises that force active recall. Focus especially on:

- **Optionals vs Kotlin nullable types**: Swift's `Optional<T>` is an enum with `.some(T)` and `.none` cases. `if let`, `guard let`, and optional chaining (`?.`) map closely to Kotlin's `?.` and `?:`, but `guard let` has no Kotlin equivalent and is idiomatically essential. Force-unwrap (`!`) is Swift's `!!`.
- **Enums with associated values**: Swift enums carry heterogeneous data per case (`case .success(Data)`, `case .failure(Error)`). Kotlin approximates this with `sealed class` hierarchies but with more boilerplate and heap allocation. Swift enums are value types.
- **Error handling**: Swift uses `do { try ... } catch` with functions explicitly marked `throws`. This is closer to Java's checked exceptions than Kotlin's unchecked model. Swift 6 adds typed throws (`throws(NetworkError)`), enabling exhaustive catch blocks.

**Deliverable**: Rewrite a small Kotlin utility (e.g., a JSON config parser or a CLI tool) in Swift using Swift Package Manager. The project must use structs as primary data types, enums with associated values for error modeling, and `guard let` for control flow.

### Week 2: Protocols, generics, and memory management

Read the Protocols and Generics chapters of the Apple book carefully, then supplement with *Advanced Swift* by objc.io (5th edition, $49 ebook). This 517-page book is the single best resource for understanding Swift's type system at depth.

**Protocol-oriented programming** is Swift's equivalent of Kotlin's interface-oriented design, but more powerful. Key distinctions:

- **Protocol extensions** provide default implementations without the diamond inheritance problems of Kotlin interface defaults, because protocols don't carry state.
- **Associated types** (`protocol Container { associatedtype Item }`) make protocols generic. Kotlin has no equivalent — this is closer to Haskell's type classes.
- **Existential vs opaque types**: `any Protocol` (runtime type erasure, like Kotlin's `List<Protocol>`) vs `some Protocol` (compiler-known concrete type, no Kotlin equivalent). The `some` keyword is used pervasively in SwiftUI (`some View`).

**ARC (Automatic Reference Counting)** is the most operationally different concept from JVM garbage collection. There is no garbage collector; the compiler inserts retain/release calls. This means **deterministic deallocation** (objects are freed the instant their reference count hits zero) and no GC pauses — but you must manually break **retain cycles** using `weak` (optional reference, auto-nils) and `unowned` (non-optional, crashes if accessed after deallocation). The most common retain cycle: a closure capturing `self` strongly. Pattern: `{ [weak self] in guard let self else { return } }`.

**Deliverable**: Extend your week-1 project with a protocol-oriented plugin system. Define a protocol with associated types, write three conforming structs, and use protocol extensions for shared behavior. Add a class with a delegate pattern that uses `weak` references correctly.

### Week 3: Concurrency, property wrappers, and result builders

Swift's structured concurrency model (async/await, actors, Sendable) is conceptually similar to Kotlin coroutines but **compiler-enforced rather than library-based**. The mapping:

| Swift | Kotlin | Key difference |
|-------|--------|----------------|
| `async func fetch() -> Data` | `suspend fun fetch(): Data` | Swift marks the function; Kotlin marks the body |
| `await fetch()` | `fetch()` (in coroutine) | Syntactically explicit in Swift |
| `Task { ... }` | `launch { ... }` | Both create unstructured concurrent work |
| `async let a = ...; async let b = ...` | `val a = async { ... }` | Swift's syntax is more concise |
| `actor` keyword | Manual synchronization / Mutex | **Compile-time data isolation** — the compiler enforces that actor state is only accessed via `await` |
| `Sendable` protocol | No equivalent | Compiler checks that types crossing concurrency boundaries are thread-safe |
| `@MainActor` | `Dispatchers.Main` | Annotation vs runtime dispatcher — Swift enforces at compile time |

**Property wrappers** (`@propertyWrapper`) encapsulate reusable property access logic. They're analogous to Kotlin's delegated properties (`by lazy`, `by Delegates.observable()`) but more deeply integrated — SwiftUI's entire state system is built on them (`@State`, `@Binding`, `@Published`). Study the *Advanced Swift* chapter on property wrappers to understand the `wrappedValue` and `projectedValue` mechanics.

**Result builders** (`@resultBuilder`) enable SwiftUI's declarative DSL. Kotlin achieves similar DSLs via lambdas with receivers and type-safe builders, but Swift's result builders transform sequential statements into accumulated results at compile time. The `@ViewBuilder` result builder is why you can write `VStack { Text("A"); Text("B") }` without commas or array syntax.

Read Mitchell Hashimoto's blog post *"Ghostty and Useful Zig Patterns"* (mitchellh.com) this week — even though Zig is a later phase, understanding Ghostty's architecture early provides motivational context.

**Deliverable**: Build an async file-processing CLI tool that uses `actor` for thread-safe state management, `TaskGroup` for parallel processing, and Swift's `Result` type. Write a small `@propertyWrapper` that validates string inputs.

**Key resources for Phase 1**:
- *The Swift Programming Language* — free at docs.swift.org/swift-book
- *Swift Programming: The Big Nerd Ranch Guide* (3rd ed.) — ~$45
- *Advanced Swift* by objc.io (5th ed.) — $49
- Swift Forums (forums.swift.org) for questions

---

## Phase 2 — SwiftUI on macOS, not iOS (weeks 4–6)

Most SwiftUI tutorials target iOS. This phase curates macOS-specific resources exclusively and teaches the five macOS scene types that have no iOS equivalent.

### Week 4: Xcode, SwiftUI fundamentals, and macOS scene architecture

Set up a proper Xcode macOS project. Choose the **SwiftUI App** lifecycle template (`@main` struct conforming to `App`). Enable **Hardened Runtime** in Signing & Capabilities immediately — you'll need it for notarization later, and enabling it early catches compatibility issues. Configure your scheme for debug builds with **Address Sanitizer** enabled.

SwiftUI's macOS-specific scene types form the backbone of every Mac app:

- **`WindowGroup`** — Standard multi-window apps. Each window gets independent state. Supports native macOS tabbed windows automatically.
- **`Settings`** — The preferences window, triggered by ⌘, (macOS-only). Use `@AppStorage` for UserDefaults-backed preferences.
- **`MenuBarExtra`** — Menu bar utilities. Two styles: `.menu` (dropdown items) and `.window` (popover with arbitrary SwiftUI content). This is critical for productivity tools.
- **`DocumentGroup`** — Document-based apps using `FileDocument` (value type, simpler) or `ReferenceFileDocument` (reference type, supports undo).
- **`Window`** — Single unique windows (utility panels). New `UtilityWindow` scene type added in macOS 15.

State management follows two eras. For targeting **macOS 14+ (Sonoma)**, use the `@Observable` macro, which replaces the verbose `ObservableObject` + `@Published` + `@StateObject` pattern. With `@Observable`, all stored properties are automatically tracked, only views reading changed properties re-render, and you use plain `@State` for both value types and observable classes. For older targets, use `ObservableObject` with `@StateObject` (owning) and `@ObservedObject` (non-owning).

**Primary resource**: *Hacking with macOS: SwiftUI Edition* by Paul Hudson — the single best macOS-specific SwiftUI resource, with **18 standalone projects** covering multi-window environments, menu bars, Settings, filesystem access, drag-and-drop, and SwiftData. Updated for macOS Sonoma and Swift 5.10 with free Swift 6 updates. Available at hackingwithswift.com/store/hacking-with-macos (~$40).

**Supplementary resources**: Apple's official tutorial "Creating a macOS App" (developer.apple.com/tutorials/swiftui/creating-a-macos-app) walks through building the Landmarks app for macOS. Sarah Reichelt's *TrozWare* blog (troz.net) publishes an annual "SwiftUI for Mac" series since 2019 — the 2024 edition covers WWDC 2023–2024 features with GitHub sample projects. Grace Huang's *macOS App Development: The SwiftUI Way* (2nd ed., Leanpub) is another focused macOS-only book.

**Deliverable**: Build a three-pane macOS app (sidebar + list + detail) using `NavigationSplitView` with a `Settings` scene that persists user preferences via `@AppStorage`. The app should display and filter a local data set.

### Week 5: Navigation, tables, and the menu bar

macOS navigation differs fundamentally from iOS. There is no `NavigationStack` push/pop paradigm — instead, macOS uses **selection-driven** `NavigationSplitView` with two or three columns. Bind a `List(selection: $selectedItem)` in the sidebar to drive detail content. Style options matter: `.balanced` lets the sidebar push the detail pane; `.prominentDetail` does **not work on macOS** (an important gotcha).

SwiftUI's `Table` view is macOS-native, supporting multi-column layouts, sortable headers via `SortComparator` bindings, single and multi-row selection, context menus, and `DisclosureTableRow` for expandable hierarchies. This is far more capable than any iOS equivalent.

Build your first `MenuBarExtra` app this week. Use the `.window` style for richer content. Be aware of documented issues: `SettingsLink` doesn't work reliably inside `MenuBarExtra` because menu bar apps use `NSApplication.ActivationPolicy.accessory` (no dock icon), causing window management complications. The community library **SettingsAccess** (github.com/orchetect/SettingsAccess) provides a workaround. Peter Steinberger's blog post *"Showing Settings from macOS Menu Bar Items"* (steipete.me) documents these challenges in detail.

**Deliverable**: Build a menu bar utility that displays system information (CPU usage, memory, disk space) in a `MenuBarExtra` with `.window` style, and includes a sortable `Table` view of running processes.

### Week 6: Document-based apps and SwiftUI previews mastery

Document-based apps use `DocumentGroup` with either `FileDocument` (struct, simpler, for basic documents) or `ReferenceFileDocument` (class, supports undo via `UndoManager`, for complex documents). Both are limited compared to AppKit's `NSDocument` — you can't easily access the file URL or customize save behavior. Howard Oakley's analysis at eclecticlight.co provides an honest assessment of these limitations.

Master SwiftUI Previews for macOS this week. Use the `#Preview` macro (Swift 5.9+) for clean syntax, `@Previewable` for previews that need bindings, and `PreviewModifier` for reusable preview environments with mock data. Pin previews to see child view changes reflected in parent contexts. Store preview-only assets in the **Preview Content** folder (excluded from release builds).

Watch two essential WWDC sessions: *"Tailor macOS windows with SwiftUI"* (WWDC 2024) covers toolbar styling, container backgrounds, window placement, and minimize behavior. *"Discover Observation in SwiftUI"* (WWDC 2023) explains the `@Observable` migration in depth.

**Deliverable**: Build a Markdown editor as a document-based app using `DocumentGroup` and `FileDocument`. It should support creating, opening, editing, and saving `.md` files, with a live preview pane using `NavigationSplitView`. Include SwiftUI previews for every view with mock data.

**Key resources for Phase 2**:
- *Hacking with macOS: SwiftUI Edition* — ~$40
- *macOS App Development: The SwiftUI Way* (2nd ed.) — Leanpub
- TrozWare blog: troz.net/post/2024/swiftui-mac-2024/
- Nil Coalescing blog on macOS scene types: nilcoalescing.com/blog/ScenesTypesInASwiftUIMacApp/
- WWDC sessions (search at developer.apple.com/videos/)

---

## Phase 3 — Platform APIs that make productivity tools real (weeks 7–9)

This phase targets your immediate practical goals: file system integration and macOS notifications. You'll also learn sandboxing, which is the single most confusing aspect of macOS development for newcomers.

### Week 7: FileManager, sandboxing, and security-scoped bookmarks

**App Sandbox** is macOS's security boundary. Every Mac App Store app must be sandboxed; direct-distribution apps should be. A sandboxed app gets its own container at `~/Library/Containers/<bundle-id>/` with read/write access to Documents, Library, and Caches subdirectories. Access to *anything else* requires explicit entitlements or user action.

The critical entitlements for productivity tools:

- `com.apple.security.files.user-selected.read-write` — access files the user selects via `NSOpenPanel`/`NSSavePanel`
- `com.apple.security.files.bookmarks.app-scope` — persist file access across app launches
- `com.apple.security.files.downloads.read-write` — Downloads folder access
- `com.apple.security.network.client` — outgoing network connections

**Security-scoped bookmarks** solve the persistence problem. When a user selects a file via an open panel, your sandboxed app gets temporary access. On quit, that access is lost. To regain it on next launch: convert the URL to bookmark `Data` via `url.bookmarkData(options: .withSecurityScope)`, persist that data, then resolve it on launch with `URL(resolvingBookmarkData:options:.withSecurityScope, bookmarkDataIsStale:)`. You must bracket access with `url.startAccessingSecurityScopedResource()` and `url.stopAccessingSecurityScopedResource()`. Handle stale bookmarks by re-prompting the user.

`FileManager` is the primary file operations API. Key operations: `contentsOfDirectory(at:)`, `createDirectory(at:withIntermediateDirectories:)`, `copyItem(at:to:)`, `attributesOfItem(atPath:)` for metadata. Use `FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)` for app-specific storage.

**Deliverable**: Build a "Watched Folders" utility that lets users select folders via `NSOpenPanel`, persists access with security-scoped bookmarks, monitors those folders for changes using `DispatchSource.makeFileSystemObjectSource` or `FileManager`-based polling, and displays a real-time log of file changes.

### Week 8: Notifications, Spotlight, and background processes

The **UserNotifications** framework (macOS 10.14+) provides local and remote notifications. For productivity tools, local notifications are the primary concern. Request authorization with `UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound])`, then schedule notifications with time-based triggers (`UNTimeIntervalNotificationTrigger`) or calendar-based triggers (`UNCalendarNotificationTrigger`). Rich notifications support image/audio attachments via `UNNotificationAttachment` and actionable buttons via `UNNotificationAction` grouped into `UNNotificationCategory`. Handle user interactions through `UNUserNotificationCenterDelegate`.

**Core Spotlight** lets your app's content appear in macOS Spotlight searches. Create `CSSearchableItemAttributeSet` objects with title, description, and keywords, wrap them in `CSSearchableItem`, then index via `CSSearchableIndex.default().indexSearchableItems([item])`. When users click a Spotlight result, handle the `NSUserActivity` with `CSSearchableItemActionType` to deep-link into your app.

For background work, **SMAppService** (macOS 13+) is the modern API for registering Launch Agents. Place a launchd plist in `Contents/Library/LaunchAgents/` within your app bundle, then call `SMAppService.agent(plistName:).register()`. The system prompts for user approval and shows the agent in System Settings → General → Login Items.

**Deliverable**: Extend the Watched Folders app from week 7 with notification alerts when files change, Spotlight indexing of watched files (so users can find them via macOS search), and a "launch at login" toggle using `SMAppService`.

### Week 9: Building a complete productivity tool

Combine everything from weeks 7–8 into a polished **Pomodoro timer + task manager** menu bar app. This project exercises every macOS API learned so far:

- `MenuBarExtra` with `.window` style showing the timer and task list
- `Settings` scene for configuring work/break durations
- Local notifications for session start/end alerts
- File system integration to save/load task lists as JSON files with security-scoped bookmarks for custom save locations
- `@AppStorage` for lightweight preferences
- Spotlight indexing of tasks

This is your first "portfolio-worthy" macOS app. Spend time on polish: respect system appearance (light/dark mode via `@Environment(\.colorScheme)`), add keyboard shortcuts via `.keyboardShortcut()`, and implement proper menu bar items.

**Deliverable**: Ship-ready Pomodoro menu bar app with the features above. Create a DMG for distribution using `create-dmg` or a similar tool.

---

## Phase 4 — AppKit interop and distribution (weeks 10–12)

SwiftUI cannot do everything on macOS. AppKit has **30+ years of accumulated APIs**, and even Apple's own apps use a mix. This phase teaches you when and how to bridge the gap — knowledge that directly transfers to Ghostty contribution.

### Week 10: NSViewRepresentable and hosting SwiftUI in AppKit

The two bridging protocols are **NSViewRepresentable** (wrap an AppKit `NSView` for use in SwiftUI) and **NSHostingView/NSHostingController** (embed SwiftUI views inside AppKit). The WWDC 2022 session *"Use SwiftUI with AppKit"* is **required viewing** — it covers both directions with real examples from the Shortcuts app.

`NSViewRepresentable` requires implementing `makeNSView(context:)` (create the view once), `updateNSView(_:context:)` (update when SwiftUI state changes), and a `Coordinator` class for delegates and callbacks. The key insight: SwiftUI reuses the underlying `NSView` instance even when the representable struct is recreated during view updates — so initialization goes in `makeNSView`, not `updateNSView`.

You need AppKit when SwiftUI falls short. The most common cases for productivity tools:

- **Advanced text editing** — SwiftUI's `TextEditor` is limited; `NSTextView` offers full rich text, syntax highlighting, custom input handling
- **Fine-grained window management** — Programmatic window positioning, non-standard fullscreen, floating panels
- **Custom drag-and-drop** — AppKit's `NSDraggingDestination` is more capable
- **Mouse/trackpad events** — `NSEvent` provides pressure, gesture phase, and raw event data
- **Complex menu customization** — Dynamic menus, custom menu item views

The SwiftUI Lab (swiftui-lab.com) documents an advanced technique: wrapping SwiftUI → `NSHostingView` → `NSViewRepresentable` → back to SwiftUI, which gives you access to the underlying AppKit view hierarchy for features like `NSTrackingArea` mouse tracking.

**Deliverable**: Build a code snippet manager that uses `NSTextView` (wrapped via `NSViewRepresentable`) for syntax-highlighted editing, with a SwiftUI sidebar for organizing snippets by language/tag and a native macOS toolbar.

### Week 11: Advanced patterns and XPC services

**XPC (Cross-Process Communication)** is Apple's recommended IPC mechanism. It enables privilege separation — breaking your app into smaller processes with minimal permissions. If an XPC service crashes, the main app is unaffected, and `launchd` restarts the service automatically. Define a shared `@objc protocol`, create an XPC Service target in Xcode (lives in `Contents/XPCServices/`), implement `NSXPCListenerDelegate` on the service side, and connect from the app via `NSXPCConnection(serviceName:)`.

Study **Swift Package Manager** conventions for modularizing your codebase. Create local SPM packages for shared models, utilities, and business logic. This is the dominant pattern in production macOS apps — it improves build times (incremental compilation per module), enforces access control boundaries, and enables code sharing between app and XPC services.

Learn **Instruments profiling** this week. The workflow: Product → Profile (⌘I), select Time Profiler, record while performing a slow operation, then analyze with "Hide System Libraries" and "Invert Call Tree" enabled. The **Memory Graph Debugger** (Debug → Debug Memory Graph) is essential for finding retain cycles — a problem JVM developers rarely encounter.

**Deliverable**: Refactor your Pomodoro app (week 9) to use an XPC service for file monitoring (separating the long-running file watcher from the UI process). Profile the app with Time Profiler and Allocations to identify and fix any performance bottlenecks or memory issues.

### Week 12: Signing, notarization, and distribution

**Notarization** is Apple's automated malware scan required for all apps distributed outside the Mac App Store since macOS Catalina. macOS Sequoia further tightened requirements — the Control+click bypass no longer works. The workflow: code-sign with Hardened Runtime → create a ZIP or DMG → submit via `xcrun notarytool submit --wait` → staple the notarization ticket with `xcrun stapler staple`. Store credentials once with `xcrun notarytool store-credentials`.

For productivity tools, **direct distribution** is usually preferable over the Mac App Store. **59% of Mac developers earn more revenue outside the MAS.** Direct distribution offers free trials (not supported on MAS), flexible pricing, faster update cycles without App Review, and fewer sandboxing restrictions. Use the **Sparkle** framework (sparkle-project.org) for self-updating — it's the industry standard used by virtually every directly-distributed Mac app.

The MAS offers convenience (automatic updates, Apple ID licensing, discoverability) and may be worth publishing to as a secondary channel. Many developers publish on both.

**Deliverable**: Sign, notarize, and distribute your Pomodoro app via DMG with Sparkle auto-updates configured. Write a `Makefile` or shell script that automates the entire build → sign → notarize → staple → package pipeline.

---

## Phase 5 — The Ghostty contribution path (weeks 13–16)

Ghostty is a **~43,600-star**, MIT-licensed terminal emulator created by Mitchell Hashimoto (co-founder of HashiCorp). It uses Zig for its core engine and C API (`libghostty`), with a Swift/AppKit/SwiftUI macOS frontend and a GTK4 Linux frontend. The architecture is a clean separation: the core library handles terminal emulation, VT sequence parsing, and GPU rendering; the platform apps are consumers of this library.

### Week 13: Zig fundamentals for Ghostty

Zig is a systems language designed as a "better C" — manual memory management, no hidden control flow, native C interop, and **comptime** (compile-time code execution) as its signature feature. Ghostty uses comptime interfaces extensively to swap platform-specific implementations at compile time with zero runtime overhead.

Start with Karl Seguin's *Learning Zig* (openmymind.net/learning_zig, free) — it's written for experienced developers and covers the language in a weekend. Then work through **Ziglings** (codeberg.org/ziglings/exercises) — learn-by-fixing exercises modeled on Rustlings. Focus on:

- **Memory management**: Explicit allocator passing, `defer`/`errdefer` for cleanup (analogous to Kotlin's `use` blocks but more pervasive)
- **Error unions**: `!` return types with `try`/`catch` — similar to Swift's error handling
- **Comptime**: Zig's most powerful feature. Functions can run at compile time, enabling generic programming without runtime cost. Read Hashimoto's *"Ghostty and Useful Zig Patterns"* talk (mitchellh.com/writing/ghostty-and-useful-zig-patterns) — it explains exactly how Ghostty uses comptime interfaces for the app runtime (`apprt`), renderer, and font backends
- **C interop**: `@cImport` for consuming C headers; Ghostty exposes its API through `include/ghostty.h`

Set up the Ghostty development environment: install Nix, enter the dev shell (`nix develop`), build Ghostty (`zig build`), and run tests (`zig build test`). Nix is the **only officially supported** build environment. On macOS, you'll also need Xcode for the Swift frontend.

**Deliverable**: Complete Ziglings. Build a small Zig library with a C API, then consume it from a Swift macOS app via an XCFramework — replicating Ghostty's architecture pattern in miniature.

### Week 14: Ghostty codebase deep dive

Read the codebase systematically. The key directories:

- **`src/apprt/`** — The application runtime abstraction. `embedded.zig` is the macOS entry point that exposes the C API consumed by Swift. `gtk.zig` is the Linux equivalent. Understanding this abstraction is essential.
- **`src/terminal/Terminal.zig`** — The core terminal state machine. VT sequence parsing, screen buffer management, scrollback.
- **`src/renderer/Metal.zig`** — The Metal renderer. Cell-based text rendering with GPU shaders. Ligature support without CPU fallback.
- **`src/font/`** — Font discovery (CoreText on macOS, FreeType/HarfBuzz on Linux), shaping, and caching.
- **`macos/Sources/`** — The Swift frontend. `Ghostty.App.swift` manages the application lifecycle, `SurfaceView_AppKit.swift` is the AppKit view hosting the terminal surface, and `Features/` contains SwiftUI views.

Read Mitchell's devlogs (mitchellh.com/ghostty) for architectural context. The video *"Making a Terminal Emulator Really, Really Fast"* (YouTube, ~50 min) explains the rendering pipeline and performance decisions.

**Deliverable**: Write a detailed architectural document of Ghostty's macOS rendering pipeline — from keypress to pixel — tracing through the Zig core, C API boundary, Swift app runtime, and Metal renderer. This exercise forces deep comprehension.

### Week 15: First contribution — translations, docs, or shell integration

Join the **Ghostty Discord** (discord.gg/ghostty, ~29,500 members) and introduce yourself. Read `CONTRIBUTING.md` carefully — Ghostty uses a **vouch-based system** where maintainers must comment `!vouch` on an issue you've opened before you can contribute. Issues tagged **"contributor friendly"** are recommended for newcomers.

Start with low-risk contributions that don't require deep Zig or rendering knowledge:

- **Translations** — Have their own Translator's Guide and can be submitted directly without issue triage
- **Shell integration scripts** — Bash, Zsh, Fish scripts in `src/shell-integration/` are relatively self-contained
- **Documentation improvements** — Configuration documentation, README clarifications
- **macOS frontend issues** — SwiftUI/AppKit issues in `macos/Sources/` leverage your Phase 1–4 skills directly

Every PR must **disclose AI tool usage** (~50% of Ghostty PRs include disclosure). This policy exists for reviewer quality assessment, not to ban AI.

**Deliverable**: Submit your first PR to Ghostty — a translation, documentation fix, or shell integration improvement.

### Week 16: Meaningful macOS-layer contribution

Target a macOS-specific issue that combines your Zig understanding with your Swift/AppKit skills. The `macos/Sources/Features/` directory contains SwiftUI views for settings, quick terminal, and other GUI features. The `SurfaceView_AppKit.swift` file is a rich `NSView` subclass handling keyboard input, mouse events, IME (Input Method Editor), and Metal rendering surface management — the exact AppKit interop skills from Phase 4.

Possible contribution areas:

- **Settings GUI improvements** — The Settings window uses SwiftUI and is actively being expanded
- **Window management features** — Tab behavior, split panes, window restoration
- **Accessibility** — VoiceOver support, keyboard navigation
- **Quick Look / Services integration** — macOS-specific features
- **Input handling fixes** — IME bugs are a major source of issues in terminal emulators

**Deliverable**: Submit a meaningful PR addressing a "contributor friendly" macOS-layer issue. Even if it's not merged by week 16, having an open PR with substantive review feedback demonstrates competence and establishes you in the community.

---

## How Swift and Kotlin actually compare, at a glance

Understanding these mappings accelerates the entire plan. Keep this as a reference.

| Concept | Kotlin | Swift | Migration note |
|---------|--------|-------|----------------|
| Null safety | `Type?` / `?.` / `?:` / `!!` | `Optional<Type>` / `?.` / `??` / `!` / `if let` / `guard let` | Nearly identical. Learn `guard let` (no Kotlin equivalent). |
| Data modeling | `data class` (reference type) | `struct` (value type) | **Paradigm shift.** Default to struct. |
| Sum types | `sealed class` + subclasses | `enum` with associated values | Swift enums are more concise and are value types. |
| Interface/protocol | `interface` + default methods | `protocol` + extensions + associated types | Swift protocols are more powerful. Learn `some` vs `any`. |
| Async | `suspend` / coroutines (library) | `async/await` / actors (language-level) | Similar feel, but Swift enforces thread safety at compile time. |
| Memory | JVM garbage collection | ARC (reference counting) | Must learn `weak`/`unowned` and retain cycle avoidance. |
| DSL builders | Lambdas with receivers | Result builders (`@resultBuilder`) | Different mechanism, similar outcome. |
| Dependency injection | Constructor injection / Hilt | `@Environment` / protocol-based | SwiftUI's `@Environment` replaces DI frameworks for UI code. |

---

## The resource stack, prioritized

Rather than a sprawling list, here are the **essential resources** in the order you should use them, with clear purpose for each.

**Books** (in sequence):
1. *The Swift Programming Language* (Apple, free) — Language reference. Skim familiar parts, deep-read Swift-specific chapters.
2. *Advanced Swift* (objc.io, $49) — Deep understanding of type system, concurrency, memory. Read alongside Phase 1.
3. *Hacking with macOS: SwiftUI Edition* (Paul Hudson, ~$40) — macOS-specific projects. Primary resource for Phase 2.
4. *macOS App Development: The SwiftUI Way* (Grace Huang, Leanpub) — Supplementary macOS-focused book.
5. *Learning Zig* (Karl Seguin, free) — Zig fundamentals for Phase 5.

**Video courses**:
1. Stanford CS193p Spring 2025 (free, YouTube) — SwiftUI fundamentals. iOS-focused but concepts transfer directly.
2. WWDC 2022: *"Use SwiftUI with AppKit"* — Required for Phase 4.
3. WWDC 2024: *"Tailor macOS windows with SwiftUI"* — macOS window management.
4. WWDC 2023: *"Discover Observation in SwiftUI"* — @Observable migration.

**Blogs** (bookmark these):
- **TrozWare** (troz.net) — Annual "SwiftUI for Mac" series, GitHub samples
- **Nil Coalescing** (nilcoalescing.com) — macOS scene types, @Observable deep dives. Author is ex-Apple SwiftUI team.
- **Hacking with Swift** (hackingwithswift.com) — Massive free tutorial library
- **SwiftUI Lab** (swiftui-lab.com) — Advanced techniques, AppKit interop patterns
- **Eclectic Light Company** (eclecticlight.co) — Honest macOS development analysis
- **Mitchell Hashimoto's blog** (mitchellh.com) — Ghostty architecture, Zig patterns

**Community**: Swift Forums (forums.swift.org), Ghostty Discord (discord.gg/ghostty), Hacking with Swift forums

---

## Conclusion: the architectural intuition you're building

This plan is structured to build layers of understanding, not just capability. By week 6, you'll understand *why* SwiftUI uses value types for views (they're cheap to recreate, enabling the diffing algorithm), *why* `some View` uses opaque return types (compile-time type erasure preserves performance while hiding complexity), and *why* `@State` works differently from `@Observable` (property wrapper storage semantics vs macro-generated observation tracking). By week 12, you'll understand *why* AppKit still matters (30 years of API surface that SwiftUI hasn't replicated), *why* sandboxing complicates file access (defense-in-depth against malicious code), and *why* direct distribution often wins for productivity tools (flexibility, margins, and update velocity).

The Ghostty contribution goal is not just motivational — it validates a specific skill combination. Ghostty's architecture (Zig core → C API → Swift/AppKit consumer) is the most sophisticated macOS development pattern in the open-source ecosystem. Understanding that boundary — how a systems-language library exposes functionality through a C ABI to a Swift app that renders with Metal and manages windows with AppKit — gives you architectural insight that transfers to any serious macOS project. The 16 weeks get you there.