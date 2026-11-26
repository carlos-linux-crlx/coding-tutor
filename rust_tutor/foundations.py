"""Offline explanations, walkthroughs, and exercises for the Rust foundations."""


def early_lessons(Lesson, Case):
    return (
        Lesson(
            "bindings", "Bindings and integer types",
            "How do you give a value a name and keep track of what kind of value it is?",
            "A let statement binds a name to a value. In let seats: i32 = 4, the annotation i32 names a "
            "signed whole-number type. Rust can often infer the type from how you use the value. Bindings "
            "are immutable by default. In a full Rust project, let mut lets you assign a new value of the "
            "same type. For now, give each step its own name.",
            "pub fn available(total: i32) -> i32 {\n    let reserved: i32 = 4;\n"
            "    let free = total - reserved;\n    free\n}",
            "When the caller supplies 12 as total, the result is 8.",
            "A shop keeps three notebooks on display. Complete stockroom so it returns how many are left "
            "in the stockroom, given the total. Use a binding to name the display count. The practice editor "
            "supplies total, which is always at least three. Try the boundary where every notebook is on display.",
            "pub fn stockroom(total: i32) -> i32 {\n    // Name the display count and compute what remains.\n    0\n}\n",
            (Case(("12",), "9"), Case(("3",), "0"), Case(("18",), "15")),
            "functions",
            ("Which quantity stays the same when total changes?",
             "After naming the display count, think about which amount you subtract from which.",
             "Leave the computed value as the final expression. End each let statement with a semicolon."),
            None, None, ("Name the count", "Compute what remains", "Read the result"),
            walkthrough=(
                ("Name a fixed value", "reserved stores 4. The : i32 annotation tells Rust the binding holds a signed integer."),
                ("Use the name in a calculation", "If total is 12, total - reserved gives 8. Rust infers that free "
                 "is also an i32 because the calculation uses two i32 values."),
                ("Read the final value", "The final line evaluates to whatever free holds. The practice editor "
                 "shows that value. Lesson 4 explains the function signature and return in detail."),
            ),
            success_tip="Explain which count comes from the caller and which count the program fixes.",
        ),
        Lesson(
            "expressions", "Expressions and operators",
            "How does Rust decide which part of a calculation to evaluate first?",
            "An expression produces a value. An operator takes values and computes something with them. "
            "Multiplication, division and remainder bind more tightly than addition and subtraction. "
            "Parentheses group an expression so you can show exactly which values go together. With "
            "integers, division drops the fractional part and % gives the remainder.",
            "pub fn envelope_count(letters: i32) -> i32 {\n    let extra = 2;\n"
            "    (letters + extra) * 3\n}",
            "With 4 letters and 2 extras for each of three tables, the function returns 18.",
            "Complete packed_lunches. Each of two buses needs as many lunches as there are passengers on "
            "that bus, plus one spare lunch per bus. The input is the passenger count on one bus. Calculate "
            "the total. Check the case where there are no passengers.",
            "pub fn packed_lunches(passengers: i32) -> i32 {\n    // Calculate the total for both buses.\n    0\n}\n",
            (Case(("6",), "14"), Case(("0",), "2"), Case(("1",), "4"), Case(("20",), "42")),
            "functions",
            ("Find the number of lunches needed for just one bus first.",
             "Use parentheses or a named intermediate value to keep the per-bus calculation together.",
             "Check zero passengers by hand. Are both spares counted?"),
            None, None, ("Group the inputs", "Evaluate each operation", "Check a boundary"),
            walkthrough=(
                ("Evaluate inside parentheses", "With letters equal to 4, letters + extra becomes 6."),
                ("Use that result", "Rust multiplies 6 by 3 and the final expression yields 18."),
                ("Compare another grouping", "Without parentheses, 4 + 2 * 3 gives 10. This would count "
                 "the extras three times while counting the ordinary letters once."),
            ),
        ),
    )


def editor_lessons(Lesson):
    return (
        Lesson(
            id="cargo-setup", title="Create, run, and test with Cargo",
            question="What does Cargo do with the Rust files you edit?",
            explanation="Cargo reads Cargo.toml, finds the package’s source files, and calls Rust’s compiler. "
            "A binary package starts in src/main.rs. On Ubuntu, follow the linked setup guide to install Rust "
            "and VS Code or VSCodium with rust-analyzer. Work in the project folder in your editor and terminal. "
            "If you know Python, think of a library crate as reusable code from a package. Cargo declares and "
            "builds dependencies. A Rust use statement brings a name into scope for this source file.",
            example="cargo new reminder\ncd reminder\ncargo check\ncargo run\ncargo test",
            example_description="Run each line in a terminal. Open the new reminder folder in your editor.",
            exercise="Create your own small Cargo program that tells you how many minutes remain in a timer. "
            "Write a minutes_left function that subtracts elapsed minutes from a total, then call it from main "
            "with 30 and 12 and print the result. Add a test for finishing exactly on time. To practice debugging, "
            "temporarily put a semicolon after the function’s final subtraction. Read the first error, then fix it. "
            "Declare elapsed with let mut, assign a new value to it, then run a second countdown. "
            "For a dependency exercise, look up itertools on crates.io. Read the join example for the matching "
            "version on docs.rs, confirm its Rust compatibility, maintenance and license, then use it to join two "
            "timer labels with a separator of your choice. With no internet, try the standard-library slice join "
            "instead and compare the approaches when you are online.",
            starter="fn main() {\n    let elapsed = 12;\n    println!(\"{}\", minutes_left(30, elapsed));\n}\n\n"
                    "fn minutes_left(total: i32, elapsed: i32) -> i32 {\n    // Return the remaining minutes.\n    0\n}\n",
            cases=(), reference="cargo",
            hints=("Check that the editor shows Cargo.toml alongside the src directory.",
                   "Call minutes_left from a function annotated with #[test] to check the boundary.",
                   "Use the file and line in the first compiler diagnostic to find the expression with the added semicolon."),
            solution=None, solution_explanation=None,
            flow=("Open the package", "Run and inspect", "Check behavior"),
            walkthrough=(
                ("Create and open the package", "cargo new writes Cargo.toml and src/main.rs. Use File → Open Folder "
                 "in your editor and select reminder. Check that the built-in terminal also points to reminder."),
                ("Check, then run", "cargo check reports type and syntax errors. cargo run builds an executable and "
                 "runs it. The starter message comes from the println! in src/main.rs."),
                ("Try an assignment", "Inside main, let mut remaining = 5; allows remaining = 4; later. "
                 "Printing the value after each statement shows the change. Try removing mut and read the diagnostic."),
                ("Add a test", "Add a small function annotated with #[test]. For example, a smoke test can contain "
                 "assert_eq!(2 + 3, 5). cargo test runs annotated tests and reports which assertions fail."),
                ("Decide if the crate helps", "The standard library can join a slice of string labels, so that case "
                 "needs no extra crate. To join an iterator of integers directly, look up itertools and check the "
                 "versioned docs and its manifest before adding it."),
                ("Try one documented API", 'Under [dependencies] in Cargo.toml write itertools = "0.14". '
                 'In src/main.rs place use itertools::Itertools; above main and put println!("{}", '
                 '[1, 2, 3].iter().join(" / ")); inside main. On a first build Cargo may need to download the crate. '
                 'cargo run prints 1 / 2 / 3. Remove the change if the standard library meets your project’s needs.'),
            ),
            editor_checks=("cargo run shows 18 for a 30-minute timer after 12 minutes.",
                           "cargo test passes a boundary assertion that minutes_left(30, 30) returns 0.",
                           "After adding a semicolon to the final subtraction, I read the diagnostic and fixed the error.",
                           "A second countdown reflects the newly assigned elapsed value.",
                           "Two labels appear joined once by my chosen separator, using a crate or the offline std version."),
        ),
        Lesson(
            id="ownership", title="Ownership, moves, and copies",
            question="Which name can you use after moving a value?",
            explanation="Rust uses ownership to track when a value’s resources can be released. A String owns "
            "its text buffer. Assigning it to another name moves ownership, and the old name can no longer be used. "
            "Small types such as i32 implement Copy, so assigning one of those leaves both names usable.",
            example='fn main() {\n    let draft = String::from("Plan the week");\n'
                    '    let reminder = draft;\n    println!("{reminder}");\n\n'
                    '    let count = 3;\n    let agenda_count = count;\n    println!("{count} {agenda_count}");\n}',
            example_description="The text is printed through its new owner. Both integer names remain usable.",
            exercise="Build a tiny packing note. Move a String with the name of an item from one binding to "
            "another and print it through its new owner. Copy an i32 quantity and print both counts. First, try "
            "printing through the old String binding too. Use cargo check to locate the move, then fix it.",
            starter="", cases=(), reference="ownership",
            hints=("Draw an arrow from the original binding to the new one when the String is assigned.",
                   "The diagnostic points both to the move and to the use that follows it.",
                   "Which of the names remains usable after the move? Keep the item text owned by one binding."),
            solution=None, solution_explanation=None,
            flow=("Identify the owner", "Move or copy", "Read the diagnostic"),
            walkthrough=(
                ("Create a String", "String::from makes an owned String. draft owns it after the let statement."),
                ("Transfer ownership", "Assigning draft to reminder transfers ownership. Printing reminder "
                 "works. Adding a print of draft after the move makes cargo check report a moved value."),
                ("Compare with a copy", "The assignment of count copies an integer. Both names can still be printed."),
            ),
            editor_checks=("The note runs and prints the moved item through its new owner.",
                           "The note prints both integer bindings with the same quantity.",
                           "I reproduced the moved-value diagnostic and identified both locations it points to."),
        ),
        Lesson(
            id="borrows", title="Borrow values with references and slices",
            question="How can a function use part of a value while the caller keeps ownership?",
            explanation="A reference lets a function use a value owned somewhere else. A shared reference "
            "such as &str lets the function read. An exclusive reference such as &mut String permits "
            "changes. A slice is a borrowed view into text or a sequence, and carries its length with it.",
            example='fn show(text: &str) {\n    println!("{text}");\n}\n\n'
                    'fn main() {\n    let title = String::from("Lunch list");\n'
                    '    show(title.trim());\n    println!("{title}");\n}',
            example_description="show reads the slice from trim. main can still read its String afterward.",
            exercise="Write count_items(items: &[i32]) -> usize so it reports how many entries are in a slice "
            "of stock counts. In main, create an array of three counts. Use your function on the first two "
            "entries and on an empty slice, then show that the original array still has three entries.",
            starter="", cases=(), reference="data",
            hints=("A slice can report its length with len().", "Try borrowing a range with &counts[..2].",
                   "The range ..0 borrows zero entries. The end index is excluded."),
            solution=None, solution_explanation=None,
            flow=("Keep an owner", "Borrow a view", "Use the owner again"),
            walkthrough=(
                ("Find the owner", "title owns the String. The signature of show requests a borrowed view of UTF-8 text."),
                ("Borrow the trimmed view", "trim returns an &str pointing into title’s text. show receives "
                 "that view, prints it, and returns."),
                ("Reuse the owner", "main can use title again because show had a reference. An integer slice "
                 "uses the same idea to view part of a sequence."),
            ),
            editor_checks=("The first-two slice reports 2 and the empty slice reports 0.",
                           "The original array remains usable and still contains all three entries."),
        ),
        Lesson(
            id="structs", title="Model an item with a struct",
            question="How can you keep the facts about one item together?",
            explanation="A struct gives related fields a shared type name. A field has a name and a type. "
            "Create a value by supplying the fields inside braces, then read a field with dot syntax. "
            "A function can borrow an entire struct and change selected fields through an exclusive reference.",
            example='struct Lamp {\n    room: String,\n    on: bool,\n}\n\n'
                    'fn switch_on(lamp: &mut Lamp) {\n    lamp.on = true;\n}\n\n'
                    'fn main() {\n    let mut lamp = Lamp { room: String::from("Hall"), on: false };\n'
                    '    switch_on(&mut lamp);\n    println!("{}: {}", lamp.room, lamp.on);\n}',
            example_description="The lamp keeps its room name and changes its state.",
            exercise="Model a library book with a title and a borrowed flag. Make two books, then write a "
            "function that marks one borrowed. Compare both states and write a test that checks the updated "
            "book’s title is still the same.",
            starter="", cases=(), reference="data",
            hints=("List the two fields and decide which Rust type fits each one.",
                   "Pass the book to be updated with &mut. The second book can stay outside the call.",
                   "Use one assertion for the flag and another for the title."),
            solution=None, solution_explanation=None,
            flow=("Group the fields", "Borrow one item", "Verify the change"),
            walkthrough=(
                ("Define the shape", "Lamp names two fields. Every Lamp has its own room and on values."),
                ("Construct one value", "The value in main starts in the hall with on set to false. "
                 "The binding is mutable so main can lend it to switch_on."),
                ("Change one field", "switch_on sets on through its exclusive reference. main keeps ownership "
                 "and can print both fields when the call returns."),
            ),
            editor_checks=("Marking the first book borrowed leaves the second book available.",
                           "A test shows the first book keeps its original title when its flag changes."),
        ),
        Lesson(
            id="option", title="Enums and optional values",
            question="How can a program represent an answer that may be absent?",
            explanation="An enum names a set of alternatives called variants. A value of Option<T> is "
            "either Some(value) containing a T, or None. A match can handle both alternatives and bind the "
            "value inside Some. Rust checks that the match covers every possibility.",
            example='fn next_task(tasks: &[&str]) {\n    match tasks.first() {\n'
                    '        Some(task) => println!("Next: {task}"),\n'
                    '        None => println!("No tasks"),\n    }\n}\n\n'
                    'fn main() {\n    next_task(&["Water plants"]);\n    next_task(&[]);\n}',
            example_description="The same function handles a populated slice and an empty one.",
            exercise="Write a small temperature program. Implement latest(readings: &[i32]) -> Option<i32>. "
            "Return the last reading when there is one, then have main show it or a clear no-readings message. "
            "Use tests for both states. Include zero as a real reading.",
            starter="", cases=(), reference="option",
            hints=("The last method on a slice returns an Option holding a reference to the final item.",
                   "A borrowed integer can be copied into a Some with *value, or you can use copied() on the Option.",
                   "Use None for an empty slice. Compare it with Some(0) in a test."),
            solution=None, solution_explanation=None,
            flow=("Inspect the option", "Handle both states", "Test presence and absence"),
            walkthrough=(
                ("Ask for the first item", "first() looks at the slice. It yields Some with a reference if "
                 "the slice has an item, or None when it is empty."),
                ("Unpack the present value", "Some(task) matches a present value and gives the branch a name "
                 "for its contents. The first call prints Water plants after the label."),
                ("Handle absence", "The second call matches None and prints No tasks. A legitimate item "
                 "stays distinct from an empty slice, even if that item looks like a default value."),
            ),
            editor_checks=("With multiple readings ending in 0, latest returns Some(0).",
                           "With no readings, latest returns None and the program shows its no-readings message."),
        ),
    )


def foundation_milestones(Milestone, question):
    return (
        Milestone(
            "foundations-start", "First programs", "", "A small program prints or computes a predictable result.",
            ("first-program", "bindings", "expressions"),
            (
                question("first-program", "first-program", "What happens before an executable can print?",
                         "The compiler processes the Rust source.", "The terminal creates a function.", "The executable edits its source."),
                question("print-macro", "first-program", "What does the ! in println! tell you?",
                         "This calls a macro.", "The line prints twice.", "Printing is optional."),
                question("binding-type", "bindings", "What does i32 tell you about let days: i32 = 7?",
                         "days holds a signed whole number.", "days contains text.", "days can be reassigned."),
                question("operator-order", "expressions", "What does 2 + 3 * 4 evaluate to?",
                         "14", "20", "24"),
                question("grouped-expression", "expressions", "What does (2 + 3) * 4 evaluate to?",
                         "20", "14", "24"),
            ),
            sheet=(("Entry point", 'fn main() { println!("Hello"); } · main starts the program.'),
                   ("Bindings", "let size: i32 = 5; · let mut size = 5; permits later assignment."),
                   ("Operators", "x + y, x - y, x * y, x / y, x % y. Use parentheses to group expressions."),
                   ("Types", "i32 signed whole number · usize size/index · bool true/false · &str borrowed text.")),
        ),
        Milestone(
            "foundations-tools", "Functions, decisions, and tools", "foundations-start",
            "A calculator and a real Cargo program with a boundary test.",
            ("functions", "calculator", "cargo-setup"),
            (
                question("functions", "functions", "What supplies the result in the body { value * 2 }?",
                         "The final expression.", "The parameter’s type.", "The function name."),
                question("parameters", "functions", "Given double(value: i32), which assignment happens at double(6)?",
                         "The parameter value receives 6.", "The function name becomes 6.", "The caller receives 6 as its input."),
                question("calculator", "calculator", "Why check a divisor before performing division?",
                         "To report zero as a recoverable error.", "Every arm needs two branches.", "match accepts only positive numbers."),
                question("cargo-run", "cargo-setup", "Which command builds and starts a Cargo binary?",
                         "cargo run", "cargo check", "cargo test"),
                question("cargo-dependency", "cargo-setup", "Where do you declare a dependency version?",
                         "Cargo.toml", "A use statement", "A Rust comment"),
            ),
            sheet=(("Function result", "fn double(n: i32) -> i32 { n * 2 } · the final expression supplies the result."),
                   ("Decisions", "if n == 0 { ... } else { ... } · match op { ... } · _ covers remaining inputs."),
                   ("Cargo", "cargo check · cargo run · cargo test · src/main.rs is the binary entry point."),
                   ("Dependencies", "Declare version in Cargo.toml. Bring an API into scope with use."),
                   ("Tool use", "Read the first diagnostic. Test the normal case and a boundary.")),
        ),
        Milestone(
            "foundations-data", "Ownership and data", "foundations-tools",
            "A small program models data, borrows it safely, and handles an absent value.",
            ("ownership", "borrows", "structs", "option"),
            (
                question("string-move", "ownership", "What happens to the old binding after its String is moved?",
                         "The old binding can no longer be used.", "Both bindings now own the String.", "The text becomes empty."),
                question("int-copy", "ownership", "Why can both i32 bindings remain usable after assignment?",
                         "i32 implements Copy.", "All values move but i32 ignores errors.", "Both now own the same heap allocation."),
                question("borrow-read", "borrows", "What access does an &str provide?",
                         "Read a borrowed UTF-8 text slice.", "Own and change any string.", "Move a vector."),
                question("struct-field", "structs", "What does book.title name?",
                         "The title field of book.", "A module called book.", "Every field in the struct."),
                question("option-empty", "option", "Which distinguishes no reading from a reading of zero?",
                         "None versus Some(0).", "Two spellings of zero.", "An empty print statement."),
            ),
            sheet=(("Ownership", "Assigning String moves ownership. Assigning i32 copies the value."),
                   ("References", "&value lends read access. &mut value lends exclusive changing access."),
                   ("Slices", "&[T] is a borrowed sequence. &items[..2] borrows up to, but excludes, index 2."),
                   ("Structs", "struct Item { done: bool } · item.done selects a field."),
                   ("Options", "Option<T> is Some(T) or None. A match can handle both.")),
        ),
    )
