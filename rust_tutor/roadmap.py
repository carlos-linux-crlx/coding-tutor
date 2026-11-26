"""Stable lesson IDs, milestone prerequisites, and evidence criteria."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Question:
    id: str
    topic: str
    prompt: str
    answer: str
    alternatives: tuple[str, ...]


@dataclass(frozen=True)
class Topic:
    id: str
    title: str
    goal: str
    quick_reference: str
    checks: tuple[str, str]
    concept: Question
    transfer: Question


@dataclass(frozen=True)
class Milestone:
    id: str
    title: str
    prerequisite: str
    endpoint: str
    topics: tuple[str, ...] = ()
    questions: tuple[Question, ...] = ()
    outline: tuple[Topic, ...] = ()
    sheet: tuple[tuple[str, str], ...] = ()
    sources: tuple[tuple[str, str], ...] = ()

    @property
    def cheat_sheet(self):
        return self.sheet or tuple((topic.title, topic.quick_reference) for topic in self.outline)

    @property
    def skill_ids(self):
        return self.topics or tuple(topic.id for topic in self.outline)


def question(key, topic, prompt, answer, *alternatives):
    return Question(key, topic, prompt, answer, alternatives)


def topic(key, title, goal, quick_reference, normal, boundary, concept, transfer):
    return Topic(key, title, goal, quick_reference, (normal, boundary),
                 question(key, key, *concept), question(f"{key}-transfer", key, *transfer))


ROADMAP = (
    Milestone("control-errors", "Logic, loops, and recoverable errors", "foundations-data",
              "A small validator that processes several inputs and explains invalid ones.", outline=(
        topic("boolean", "Boolean logic", "Combine conditions, then trace which operands are evaluated.",
              "Use && for two required conditions, || for alternatives, and ! to invert.",
              "An input that meets both requirements is accepted.", "Failure of either required condition rejects an item.",
              ("What must be true for a && b to be true?", "Both operands", "Either operand", "Neither operand"),
              ("When does Rust skip the right operand of &&?", "When the left operand is false", "When the left operand is true", "On every call")),
        topic("loops", "Repeat work with loops", "Trace repeated work with for and use a stopping condition with while.",
              "for item in items { ... } visits each item. while condition { ... } reevaluates its condition.",
              "Three inputs are visited in order.", "A loop with an initially false condition performs no work.",
              ("Which construct naturally walks a sequence?", "for", "use", "match by itself"),
              ("How often is a while condition checked?", "Before each possible iteration", "Only once after the body", "Only when the program exits")),
        topic("error-basics", "Handle a recoverable error", "Use Result to separate success from failures the caller can handle.",
              "Match Ok(value) and Err(reason). Handle expected bad input deliberately.",
              "A valid numeric string produces the matching number.", "An invalid string displays feedback and the program continues.",
              ("Which variant of Result holds an error?", "Err", "None", "Some"),
              ("Why use an error outcome for predictable invalid input?", "The caller can decide what to do next", "It conceals failed input", "It replaces every test")),
    )),
    Milestone("collections", "Collections and text", "control-errors", "A command-line inventory summary.", outline=(
        topic("vectors", "Vectors and loops", "Collect related readings in a Vec and trace a for loop.",
              "let mut values = Vec::new(); values.push(5); for v in &values { ... }",
              "Three inputs appear in input order.", "An empty vector prints no item rows.",
              ("What does Vec own?", "A growable sequence", "A string slice", "One fixed integer"),
              ("How many times does a for loop visit an empty vector?", "Zero", "Once", "It depends on capacity")),
        topic("strings", "Strings, UTF-8, and text slices", "Distinguish byte lengths from character counts.",
              "text.len() counts bytes. text.chars().count() counts Unicode scalar values. text.trim() borrows.",
              "Display both lengths for café.", "Trim surrounding whitespace while keeping the accented letter.",
              ("What does String::len count?", "Bytes", "Characters", "Words"),
              ("Which API walks Unicode scalar values?", "chars()", "bytes()", "capacity()")),
        topic("maps", "Hash maps and counting", "Use keys to aggregate repeated values.",
              "HashMap<K, V> · get(&key) returns Option<&V>. entry(key).or_insert(0) creates a default.",
              "Two occurrences of the same label produce one entry with count 2.", "A missing label reports count 0.",
              ("What locates a value in a HashMap?", "Its key", "Its insertion position", "Its printed length"),
              ("What can get return for an absent key?", "None", "Some(0)", "An empty map")),
    )),
    Milestone("iteration", "Iteration and data summaries", "collections", "A report that filters and totals inventory rows.", outline=(
        topic("iterators", "Iterator adapters", "Trace the flow of items through map and filter.",
              "iter() borrows; into_iter() on a Vec consumes it. map transforms and filter selects; collect drives both.",
              "Filter out zero counts and double the remaining values.", "An empty input produces an empty report.",
              ("Which adapter transforms each item?", "map", "filter", "count"),
              ("When does a chain of lazy adapters do its work?", "When it is consumed", "When the Vec is declared", "Only at compile time")),
        topic("aggregation", "Sort and aggregate data", "Separate choosing an order from computing a total.",
              "values.sort(); · values.iter().sum::<i32>() · sorting keeps duplicates.",
              "Unsorted counts yield the expected sorted report and sum.", "Repeated counts remain in the report.",
              ("What does sum consume?", "An iterator of values", "A sort order", "A string capacity"),
              ("What should happen to duplicate counts during sorting?", "Both are retained", "One is removed", "They always become a single total")),
        topic("methods", "Methods and impl blocks", "Put behavior next to the type it operates on.",
              "impl Item { fn mark(&mut self) { ... } } · &self reads, &mut self can change the original.",
              "Two inventory items format their own fields.", "Updating one item leaves the other unchanged.",
              ("Which receiver can change the original item?", "&mut self", "&self", "&str"),
              ("Where do you define inherent methods for a struct?", "An impl block for the type", "A match arm", "Cargo.lock")),
    )),
    Milestone("package-design", "Modules, packages, and dependencies", "iteration", "A small reusable library and command-line front end.", outline=(
        topic("modules", "Modules and visibility", "Keep internal helpers private and expose a small public interface.",
              "mod inventory; declares a module. use crate::inventory::Item; brings Item into scope. pub controls visibility.",
              "A sibling module can call an intended public entry point.", "An attempted external call to a private helper fails to compile.",
              ("What does pub control?", "Visibility", "Ownership", "Test order"),
              ("What can a private helper change without breaking callers that use only the public API?", "Its internal implementation", "The public return type without notice", "The package version automatically")),
        topic("package-targets", "Library and binary targets", "Separate reusable behavior from launching the program.",
              "src/lib.rs exposes library behavior; src/main.rs launches the program.",
              "The binary calls behavior from the package library.", "A test can call the library without launching the binary.",
              ("Which default source file defines a library target?", "src/lib.rs", "src/main.rs", "Cargo.lock"),
              ("Where should program startup and argument collection normally live?", "The binary entry point", "The lockfile", "A private style rule")),
        topic("dependencies", "Choose and manage crates", "Compare a standard-library approach with a crate; check docs, compatibility, maintenance, and license.",
              "Cargo.toml declares allowed versions. Cargo.lock records resolved versions. Check need, docs, compatibility, updates, and license.",
              "Build and run a documented dependency version from Cargo.toml.", "Run a std-only version of the same small operation and compare its output.",
              ("What records resolved dependency versions?", "Cargo.lock", "src/main.rs", "A use statement"),
              ("Why might a std-only approach be preferable for a simple task?", "It avoids an unnecessary dependency", "std APIs cannot change behavior", "It disables Cargo")),
    )),
    Milestone("reliability", "Errors, automated tests, and debugging", "package-design", "A parser with useful diagnostics and a repeatable check suite.", outline=(
        topic("result-errors", "Result and the question-mark operator", "Propagate errors and interpret them at an application boundary.",
              "Result<T, E> = Ok(T) or Err(E). let value = operation()?; propagates a compatible error.",
              "Valid text parses to the expected value.", "Malformed text gives a useful error instead of a panic.",
              ("What does ? do with Err in a compatible function?", "Returns the error early", "Prints the result", "Turns Err into Ok"),
              ("Where can a CLI turn a parse error into a message?", "At the application boundary", "Only inside Cargo.toml", "Inside a successful conversion")),
        topic("unit-tests", "Unit tests and boundary cases", "Write assertions for both normal behavior and edge cases.",
              "#[test] fn empty_input() { ... } · assert_eq!(actual, expected);",
              "A known valid input passes an assertion.", "An invalid or boundary input has a separate assertion.",
              ("What compares actual and expected values?", "assert_eq!", "println!", "use"),
              ("What makes an empty-input test valuable?", "It checks a boundary independently", "It replaces every normal case", "It verifies formatting only")),
        topic("debugging", "Integration tests and debugging", "Reproduce a failure through the public API and isolate the first wrong value.",
              "tests/ uses public APIs. Reproduce, inspect the first wrong value, then rerun the check.",
              "An integration test exercises a public operation.", "An intentionally failing test identifies the input and observed result.",
              ("What should an integration test normally exercise?", "Public behavior", "Private variable names", "Only compiler flags"),
              ("What should you record before debugging a failure?", "The smallest reproducible input", "The prettiest solution", "A different random input each time")),
    )),
    Milestone("abstraction", "Generics, traits, and lifetimes", "reliability", "A library that summarizes two data types behind one API.", outline=(
        topic("generics", "Generic functions and types", "Use a type parameter where the same logic works across types.",
              "struct Entry<T> { value: T } · a type parameter keeps the same structure usable across types.",
              "Call the same implementation with integers.", "Call the same implementation with text values.",
              ("What is T in a generic function declaration?", "A type parameter", "A text value", "A process ID"),
              ("What does a caller normally supply for an inferred type parameter?", "A value whose type Rust can infer", "A file path", "A new compiler")),
        topic("traits", "Traits and bounds", "Describe required behavior using a trait and implement it for two types.",
              "fn show<T: Display>(value: T) { ... } · the bound specifies required behavior.",
              "Two types produce their own output through the same trait-based function.", "A type lacking the trait produces a bound diagnostic.",
              ("What does a trait bound require?", "A type implementing the trait", "A particular variable name", "A dynamic library"),
              ("Why use Display as a bound for a formatting helper?", "It can request a user-facing representation", "It allocates on every call by definition", "It makes all types identical")),
        topic("lifetimes", "Lifetime relationships", "Describe how an output reference is tied to borrowed input.",
              "fn view<'a>(text: &'a str) -> &'a str · result borrows from the input’s lifetime.",
              "An output reference is used while its owner is alive.", "Attempting to return a reference to a local String is rejected.",
              ("What does a lifetime annotation describe?", "A relationship between reference validity periods", "How to extend ownership automatically", "A timeout"),
              ("Can an annotation keep a local String alive after its function returns?", "No, the owner still goes out of scope", "Yes, if you name the lifetime", "Yes, if the text is empty")),
    )),
    Milestone("cli-input", "Command-line inputs and files", "abstraction", "A stock-list command that reads a file and reports useful errors.", outline=(
        topic("cli-args", "Arguments, help, and exit status", "Translate user-supplied arguments into typed options.",
              "std::env::args() yields Unicode arguments. Use args_os() for paths that may not be Unicode.",
              "A valid path and option reach the requested action.", "A missing argument shows usage and signals failure.",
              ("What should a nonzero exit status usually mean?", "The command failed", "The output was styled", "The command used stdin"),
              ("What should happen before indexing an argument list?", "Check that the argument exists", "Discard all flags", "Print the full file")),
        topic("file-read", "Read files and handle I/O errors", "Use Path and Result to read caller-selected files.",
              "std::fs::read_to_string(path) returns Result<String>. Handle missing files and non-UTF-8 input.",
              "A small input file produces its expected rows.", "A nonexistent path gives an understandable error.",
              ("What does reading a missing file return?", "An error result", "An empty success every time", "A random line"),
              ("What type represents a filesystem path in std?", "Path", "HashMap", "Duration")),
        topic("file-write", "Write output and protect inputs", "Export a report to a deliberate output location.",
              "std::fs::write(path, bytes) may replace a file. For new-only writes, use OpenOptions::create_new.",
              "A report written to a fresh path contains the expected content.", "When output points to protected input, the original content stays intact.",
              ("What should an export check before overwriting?", "Whether overwriting is intended", "Whether the path name is short", "Whether the report is sorted"),
              ("Why test a write error?", "To verify the command explains failed persistence", "To guarantee data always fits", "To skip read tests")),
    )),
    Milestone("cli-project", "A complete file-based CLI", "cli-input", "A local inventory app with round-trip storage and a release build.", outline=(
        topic("formats", "Choose a record format", "Parse and format structured records, using a documented format.",
              "parse(encode(value)) should recover the value. Specify escaping, malformed cases, and empty inputs.",
              "Saving then reading a valid record preserves its fields.", "A malformed record reports enough context to fix it.",
              ("What does a round-trip test compare?", "The original value with the decoded value", "Two build times", "Compiler versions"),
              ("What should happen to malformed records?", "Report the problem deliberately", "Treat them automatically as correct", "Delete the source file")),
        topic("cli-project-tests", "Test the CLI end to end", "Use small temporary inputs to verify outputs and exit codes.",
              "Inspect stdout, stderr, and exit status with a temporary fixture. Check success and failure separately.",
              "A fixture file yields the expected report and success code.", "Invalid arguments yield an error and a nonzero exit code.",
              ("What can a CLI integration test observe?", "Output and exit status", "Only private field names", "Only editor settings"),
              ("Why use temporary inputs?", "Keep tests repeatable and user files untouched", "Make Rust skip compilation", "Hide the outcome")),
        topic("release-build", "Format, lint, build, and launch", "Use rustfmt and Clippy, then build and run the release binary.",
              "cargo fmt · cargo clippy · cargo build --release · launch the binary from target/release.",
              "The release executable handles a known fixture.", "Running without required inputs still gives the documented error.",
              ("Which command applies Rust formatting?", "cargo fmt", "cargo test", "cargo new"),
              ("What does a Clippy suggestion tell you?", "A potential improvement to review", "Every behavior is correct", "The command already failed its tests")),
    )),
    Milestone("backend-basics", "Networking and local HTTP", "cli-project", "A loopback-only service exposing one inventory route.", outline=(
        topic("loopback", "Clients, servers, addresses, and ports", "Trace a request to a server on the same machine.",
              "127.0.0.1:PORT · address identifies the host and the port identifies the listener.",
              "A client at 127.0.0.1 reaches the intended listening port.", "Connecting to an unused port reports a connection failure.",
              ("What does 127.0.0.1 refer to?", "The local machine", "Every device on the LAN", "The crate registry"),
              ("What distinguishes two local services on the same address?", "Their port numbers", "Their Rust edition", "Their test file names")),
        topic("http", "HTTP requests, routes, and responses", "Map a request method and path to a handler and response.",
              "GET /items → 200 with data; missing path → 404. Route by both method and path.",
              "GET on a known path returns the expected body and 200.", "An unknown path returns 404.",
              ("What does a route usually match?", "A method and path", "A filename extension only", "A lockfile entry"),
              ("What does HTTP 404 represent?", "The requested resource was not found", "The request succeeded", "The port number changed")),
        topic("json-api", "JSON bodies and validation", "Decode input into types and report invalid requests consistently.",
              "Decode JSON → validate fields → mutate state. Invalid request input belongs in a 4xx response.",
              "A valid JSON request adds an item and returns its data.", "An invalid required field yields a clear 4xx response.",
              ("What should run before saving request data?", "Decoding and validation", "Formatting the README", "Ignoring missing fields"),
              ("What family of HTTP statuses describes bad client input?", "4xx", "2xx", "1xx")),
    )),
    Milestone("backend-project", "Backend state and verification", "backend-basics", "A tested local inventory API with a clear startup and shutdown procedure.", outline=(
        topic("async", "Async tasks and I/O", "Follow what happens while a handler awaits a network or storage operation.",
              "async fn produces a future. .await may suspend the task until the future can continue.",
              "A request returns successfully after awaiting its result.", "While a slow request waits, a fast route can respond.",
              ("What does await let an async task do?", "Suspend while waiting for work", "Turn every operation into a dedicated thread", "Skip error handling"),
              ("Why avoid long blocking work on an async executor thread?", "It can delay unrelated tasks", "It changes JSON syntax", "It renames the route")),
        topic("backend-state", "Shared state and persistence", "Define explicit ownership of service state and save data across restarts.",
              "A single state interface coordinates access; persistence survives restart.",
              "An item added from one request is visible to a later request.", "An item saved before restart is still present afterward.",
              ("Why put shared state behind a controlled interface?", "To coordinate access and preserve invariants", "To avoid needing a server", "To make fields global by default"),
              ("Which observation demonstrates persistence?", "Saved data survives a restart", "Two handlers print the same title", "A response has one header")),
        topic("backend-tests", "Test a local API", "Verify successful and failing requests with isolated sample data.",
              "Give tests isolated state; assert the HTTP status, response, and post-request state.",
              "A test creates and retrieves one item.", "A test confirms bad input leaves state unchanged.",
              ("What should an API test inspect after bad input?", "The response and relevant state", "Only whitespace in source", "Only which editor is open"),
              ("Why give each test isolated state?", "To prevent one test from changing another’s result", "To disable assertions", "To make ports public")),
    )),
    Milestone("gui-basics", "Desktop UI fundamentals", "backend-project", "A small desktop window that edits and displays an inventory item.", outline=(
        topic("gui-events", "Widgets and event callbacks", "Connect one event to one focused update.",
              "Signal → callback → state update → view refresh. Keep callbacks focused.",
              "Pressing the action button updates its output.", "Opening the window without interaction leaves the initial state intact.",
              ("What invokes a GUI callback?", "An event or signal", "A dependency lock", "A type annotation"),
              ("When should a button handler change the state?", "When its relevant action runs", "Continuously while idle", "Before the window exists")),
        topic("gui-layout", "Layout, keyboard, and accessibility", "Choose meaningful labels and preserve navigation as the window changes size.",
              "Use named widgets, visible focus, and a layout that adapts to available space.",
              "Essential controls remain readable at two window sizes.", "A keyboard user can reach and activate the primary action.",
              ("What helps assistive technology identify a control?", "A meaningful accessible label", "Its pixel position", "Its source filename"),
              ("What should resizing preserve?", "Access to essential controls", "Exactly the same pixel widths", "The package lock order")),
        topic("gui-state", "Connect the view to the model", "Separate displayed state and business rules.",
              "Widgets reflect model state; reusable rules live in the model or service.",
              "Editing one item updates its visible row.", "An invalid edit leaves the model intact and shows feedback.",
              ("Where should rules shared by a CLI and GUI live?", "In the shared model or service", "Only in a click callback", "In the theme"),
              ("What should the view do when valid model state changes?", "Reflect the new state", "Discard it immediately", "Restart the operating system")),
    )),
    Milestone("gui-project", "Complete the desktop app", "gui-basics", "A desktop inventory tool with saved data and a responsive window.", outline=(
        topic("gui-storage", "Persistence and application boundaries", "Reuse the file format and keep I/O failures visible.",
              "Read saved state on launch. Keep unsaved edits visible if the save fails.",
              "Closing and reopening restores saved items.", "A failed save gives feedback and preserves the in-memory edit.",
              ("What should the UI report if saving fails?", "A clear failure and usable next step", "Silent success", "A random item"),
              ("Why reuse established storage logic?", "The same rules stay verified across interfaces", "It eliminates every file permission", "It prevents data from changing")),
        topic("gui-responsive", "Responsive work and cancellation", "Keep lengthy work off the UI thread and report its outcome.",
              "Worker runs blocking work. UI handles events. Apply results only when the work is still wanted.",
              "During a simulated long load, the window remains responsive.", "Canceling a load keeps the previous visible state.",
              ("Where should lengthy blocking work run?", "Off the UI thread", "In the paint handler", "On every keypress without a limit"),
              ("What should users see after canceling?", "A consistent state and clear status", "Half-written data", "An unresponsive window")),
        topic("gui-launch", "Package, open, and diagnose a desktop app", "Make a release build discoverable and give it a clear launch path.",
              "Build → package → launch → verify assets and dependencies from the packaged entry point.",
              "The app opens from the intended launcher.", "A missing dependency or file gives a diagnostic that identifies the cause.",
              ("Why check the packaged entry point?", "Packaging can change paths or dependencies", "It makes tests unnecessary", "It changes the Rust syntax"),
              ("What should a startup diagnostic identify?", "The failing operation or dependency", "Only the background color", "Every private method")),
    )),
    Milestone("deployment", "Deploy and maintain a local app", "gui-project",
              "A versioned local build that installs, starts, and diagnoses problems.", outline=(
        topic("configuration", "Configuration and defaults", "Choose explicit settings and meaningful defaults.",
              "Use defaults for omitted settings. Validate supplied configuration before starting the app.",
              "An omitted setting uses its documented default.", "An invalid setting identifies the problem before starting.",
              ("What should a default do?", "Provide predictable behavior for an omitted setting", "Hide invalid input", "Override every user setting"),
              ("When should required configuration be validated?", "Before depending on it", "Only after an unrelated crash", "After deleting it")),
        topic("diagnostics", "Application diagnostics", "Record useful local diagnostics and reproduce a failure from them.",
              "Record the failed operation and enough context to reproduce it. Keep private data out of logs.",
              "A reproducible failure identifies its operation and cause.", "Diagnostics omit the fixture’s private values.",
              ("What makes an error message actionable?", "It identifies what failed and a way to investigate", "It prints every private value", "It always says unknown"),
              ("What belongs in a log after a read fails?", "The operation and useful nonprivate context", "All password text", "Only the current time")),
        topic("distribution", "Version and distribute a local build", "Build and document a versioned artifact and its requirements.",
              "Record the version, runtime requirements, start command, and checksum for the release artifact.",
              "A fresh install follows the documented launch procedure.", "The artifact checksum matches the published value.",
              ("What does a file checksum let someone compare?", "Received bytes with the expected artifact", "Their quiz score with yours", "The app’s memory use"),
              ("Why list runtime requirements?", "A user can tell what the built app needs to launch", "It ensures all systems already have them", "It replaces a launch check")),
    )),
    Milestone("capstone", "Capstone and handoff", "deployment", "A useful personal project with a tested core and a runnable interface.", outline=(
        topic("capstone-design", "Scope your own useful app", "Choose a small user problem, an interface, and observable acceptance criteria.",
              "Define input, expected output, and one failure case before building the first version.",
              "A documented normal workflow produces the promised result.", "A documented edge case has an intentional result.",
              ("What makes a criterion useful?", "You can observe whether the behavior happened", "It names a fashionable crate", "It requires only a color preference"),
              ("What should you decide before expanding the app?", "The smallest useful workflow", "The total number of dependencies", "Every possible launch icon")),
        topic("capstone-delivery", "Deliver, revisit, and explain", "Ship a runnable version, verify the core concepts it uses, and record how to improve it.",
              "Document run and test commands. Add a regression case for a specific behavior.",
              "A second run from the documented instructions reproduces a working example.", "A regression case shows a previously broken behavior remains fixed.",
              ("What should the handoff include?", "How to run, test, and explain the program", "Only a screenshot", "Only a list of type names"),
              ("What makes a regression case valuable?", "It catches a specific behavior breaking again", "It grades formatting", "It hides failures")),
        topic("capstone-review", "Review tradeoffs and next steps", "Explain your design decisions using observed behavior and choose one follow-up.",
              "Compare an alternative against your criteria. Add a separate acceptance check for any planned change.",
              "The project demonstration covers each promised core behavior.", "A documented tradeoff leads to one measurable improvement task.",
              ("What evidence is most useful in a design review?", "Observed behavior tied to criteria", "The number of files by itself", "One screenshot without context"),
              ("What makes an improvement task verifiable?", "It has an observable success criterion", "It only asks for better code", "It drops the original requirements")),
    )),
)
