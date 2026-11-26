"""The authored Rust foundations and companion reference."""

from collections.abc import Callable
from dataclasses import dataclass

from .advanced import ADVANCED_ROADMAP, OPTIONAL_FFI
from .foundations import early_lessons, editor_lessons, foundation_milestones
from .roadmap import ROADMAP, Milestone, question


BOOK = "https://doc.rust-lang.org/book/"
CARGO = "https://doc.rust-lang.org/cargo/"
HELLO_WORLD = "Hello, world!"
HELLO_WORLD_PROGRAM = f'fn main() {{\n    println!("{HELLO_WORLD}");\n}}'


def is_custom_greeting(output: str) -> bool:
    message = output.strip()
    return bool(message) and message != HELLO_WORLD and output.splitlines() == [output]


@dataclass(frozen=True)
class Case:
    arguments: tuple[str, ...]
    expected: str
    accepts: Callable[[str], bool] | None = None

    def matches(self, output: str) -> bool:
        return self.accepts(output) if self.accepts is not None else output == self.expected


@dataclass(frozen=True)
class Lesson:
    id: str
    title: str
    question: str
    explanation: str
    example: str
    example_description: str
    exercise: str
    starter: str
    cases: tuple[Case, ...]
    reference: str
    hints: tuple[str, ...]
    solution: str | None
    solution_explanation: str | None
    flow: tuple[str, str, str]
    walkthrough: tuple[tuple[str, str], ...] = ()
    success_tip: str = ""
    editor_checks: tuple[str, ...] = ()


@dataclass(frozen=True)
class Chapter:
    id: str
    title: str
    summary: str
    sections: tuple[tuple[str, str], ...]
    example: str
    sources: tuple[tuple[str, str], ...]
    cheat_sheet: tuple[tuple[str, str], ...] = ()


INITIAL_LESSONS = (
    Lesson(
        "first-program", "Your first Rust program",
        "How does a Rust program print a message?",
        "Read this complete Rust program before you edit anything. It has one function and prints one line.",
        HELLO_WORLD_PROGRAM,
        "This program prints Hello, world! on its own line.",
        "Change the message between the double quotes to a short phrase of your choice. Keep the program printing "
        "one nonempty line. Predict what it will show, choose Run sample to see the result, then choose Check exercise.",
        HELLO_WORLD_PROGRAM + "\n",
        (Case((), "One nonempty line with a message different from the example.", is_custom_greeting),),
        "execution",
        ("Which part of the example appears on the screen? Look for the place where that text is written.",
         "Change only the text inside the double quotes. Keep both quotes and the rest of the line in place.",
         "Use Run sample to compare the line on screen with your prediction. Check that your message is different "
         "from the example and stays on one line."),
        None, None,
        ("Compile the source", "Run the program", "Read the output"),
        walkthrough=(
            ("Start with fn main()", "fn declares a function, a named group of instructions. main is the program’s "
             "entry point. When you run the program, Rust starts there. The empty parentheses mean main takes no inputs."),
            ("Read the body", "The opening and closing braces mark the body of main. The indented line between them is "
             "the instruction that runs. The semicolon ends that instruction."),
            ("Call the println! macro", "println! prints a line of text. The exclamation mark after println tells Rust "
             "you are calling a macro. While compiling, Rust expands the macro into the code that writes the line."),
            ("Find the string literal", "The double quotes surround a string literal, which is text written directly "
             "in the program. The output contains the text inside the quotes, including the exclamation mark in the message."),
            ("Compile, then run", "The compiler checks the source code and turns it into an executable. Running that "
             "executable starts main, and the instruction inside main writes the message to the terminal."),
        ),
        success_tip="Your program printed the message you chose. Point to the part of your code that determined the output.",
    ),
    Lesson(
        "functions", "Functions and return values",
        "Where does a function's result come from?",
        "A variable gives a value a name. A function can take named inputs, called parameters, and return a result. "
        "The type i32 represents a signed 32-bit integer. In a function with -> i32, Rust checks that the returned "
        "value has that type. A final expression without a semicolon supplies the result. A semicolon makes it a statement instead.",
        "fn double(value: i32) -> i32 {\n    value * 2\n}",
        "On a call to double(5), Rust binds value to 5 and returns 10 from the final expression.",
        "Complete add so that it returns the sum of its two inputs. The exercise provides main and prints your "
        "return value. Try Run with the sample, then Check to try other pairs, including negative numbers.",
        "pub fn add(left: i32, right: i32) -> i32 {\n    // Return the sum of left and right.\n    0\n}\n",
        (Case(("2", "3"), "5"), Case(("-4", "9"), "5"), Case(("0", "-7"), "-7")),
        "functions",
        ("Which two names already contain the values you need?",
         "Use the + operator on the two parameters.",
         "Make the sum the final expression. Check whether there is a semicolon after it."),
        "pub fn add(left: i32, right: i32) -> i32 {\n    left + right\n}",
        "The caller supplies both integers. The final expression evaluates to their sum, which Rust returns as an i32.",
        ("Pass two integers", "Evaluate the body", "Return their sum"),
        walkthrough=(
            ("Read the signature", "double takes one integer. The arrow says the caller gets an i32 back."),
            ("Follow a call", "In double(5), the parameter value receives 5. Inside the body, value * 2 evaluates to 10."),
            ("Return to the caller", "The last expression has no semicolon. Its value is the function’s result. "
             "When a caller uses double(5) + 1, the addition uses 10, giving 11."),
        ),
    ),
    Lesson(
        "calculator", "Build a tiny calculator",
        "How does a program choose an operation and handle a bad request?",
        "An if expression chooses one of two branches based on a true or false condition. "
        "A match expression compares a value against patterns in order and evaluates the first matching arm. "
        "Use a final _ arm for input you did not recognize. A Result is either Ok with a value or Err with a reason. "
        "A calculator can use Result to send a number or explain why it could not produce one. "
        "Integer division truncates toward zero, and division by zero needs to be handled before trying the division.",
        'fn temperature_label(degrees: i32) -> &\'static str {\n'
        '    if degrees < 0 {\n        "below freezing"\n    } else {\n        "at or above freezing"\n    }\n}',
        "The value returned depends on the condition. Read &'static str here as a piece of fixed program text.",
        "Complete calculate for +, -, *, and / on small signed integers. Return Err(\"division by zero\") when "
        "dividing by zero and Err(\"unknown operation\") for any other operation. The runner prints the result or "
        "prefixes an error with Error:. Try tracing the two division branches before you run the checks.",
        'pub fn calculate(left: i32, op: &str, right: i32) -> Result<i32, &' + "'static str> {\n"
        '    match op {\n        "+" => Ok(left + right),\n'
        '        // Handle subtraction, multiplication and division.\n        _ => Err("unknown operation"),\n    }\n}\n',
        (Case(("8", "+", "3"), "11"), Case(("-3", "-", "7"), "-10"), Case(("-3", "*", "-4"), "12"),
         Case(("-7", "/", "2"), "-3"), Case(("4", "/", "0"), "Error: division by zero"),
         Case(("7", "%", "2"), "Error: unknown operation"), Case(("0", "/", "5"), "0")),
        "branches",
        ("List the possible outcomes before writing code. When should the result contain a number?",
         "Add match arms for subtraction and multiplication, each returning Ok with the computed number.",
         "Handle a zero divisor before ordinary division. You can use a match guard or an if inside the division arm."),
        'pub fn calculate(left: i32, op: &str, right: i32) -> Result<i32, &' + "'static str> {\n"
        '    match op {\n        "+" => Ok(left + right),\n        "-" => Ok(left - right),\n'
        '        "*" => Ok(left * right),\n        "/" if right == 0 => Err("division by zero"),\n'
        '        "/" => Ok(left / right),\n        _ => Err("unknown operation"),\n    }\n}',
        "The guard on the first division arm is checked before the ordinary division arm. If right is zero, "
        "the guarded arm returns an error. Otherwise the next arm performs division. The catch-all handles unsupported operators.",
        ("Read the operator", "Choose a branch", "Return a value or error"),
        walkthrough=(
            ("Evaluate the comparison", "With -3 as input, degrees < 0 is true. Rust evaluates the first branch "
             "and returns its text."),
            ("Try the boundary", "With 0 as input, the comparison is false. The else branch supplies the result. "
             "Both branches produce text, so the whole if expression has a text result."),
            ("Apply the same idea to more cases", "A calculator chooses between several operators using match. "
             "Within the division case, use a condition to distinguish zero from a usable divisor."),
        ),
    ),
)

CHAPTERS = (
    Chapter("execution", "Source, compilation, and output", "Follow a Rust program from text to a running process.",
            (("Source code", "A .rs file describes what the program should do. Rust's compiler checks it and, "
              "for an executable target, produces a binary your computer can run."),
             ("Program entry", "The main function is where your executable begins. A block groups instructions "
              "inside braces. The program leaves main after executing its final instruction."),
             ("Read the result", "Standard output is the channel for ordinary program output. Compiler diagnostics "
              "come from building the program. If you see a diagnostic, start with the first error and its file and line."),
             ("Try it", "Remove a quote from a string, build again, and inspect where the compiler points. Restore "
              "the quote and verify that you can see the expected text.")),
            'fn main() {\n    println!("Hello, Rust!");\n}',
            (("The Rust Book · Hello, World!", BOOK + "ch01-02-hello-world.html"),),
            (("Program entry", "fn main() { ... } starts a binary."), ("Print one line", 'println!("message");'))),
    Chapter("functions", "Values, types, and functions", "Name values, pass them to functions, and read the result.",
            (("Bindings", "A let statement binds a name to a value. Rust can often infer its type. Add mut when you need "
              "to assign a different value to the same binding."),
             ("Parameters and return types", "A parameter declaration specifies the expected type, such as amount: i32. "
              "The arrow names the return type. Rust checks each call against the function signature."),
             ("Expressions and statements", "Expressions produce values. The final expression in a block can supply the "
              "block's value. When a semicolon turns that expression into a statement, the block can instead evaluate to unit."),
             ("Try it", "Add a semicolon after amount + 1 in the example. Read the compiler's type mismatch, "
              "then remove the semicolon and predict the result for amount equal to zero.")),
            "fn next(amount: i32) -> i32 {\n    amount + 1\n}",
            (("The Rust Book · Variables and Mutability", BOOK + "ch03-01-variables-and-mutability.html"),
             ("The Rust Book · Functions", BOOK + "ch03-03-how-functions-work.html")),
            (("Bindings", "let name: i32 = 5; · let mut name = 5; allows assignment."),
             ("Types", "i32 signed integer · usize index or size · bool true/false · &str borrowed text."),
             ("Arithmetic", "+ - * / % · use parentheses to show grouping. Integer division truncates toward zero."),
             ("Return", "fn double(n: i32) -> i32 { n * 2 } · leave the result expression without a semicolon."))),
    Chapter("branches", "Branching and recoverable errors", "Choose behavior based on input and report errors with Result.",
            (("Choosing a branch", "An if expression takes a boolean. A match checks patterns from top to bottom. "
              "A catch-all pattern, written _, handles remaining values. Each reachable branch must return a compatible type."),
             ("Handling failure", "Result<T, E> is an enum. Ok contains the success payload of type T. Err contains the "
              "failure payload of type E. The caller can use match to decide how to respond to each outcome."),
             ("Borrowed text", "An &str views UTF-8 text owned elsewhere. A string literal such as \"empty label\" "
              "can be borrowed for the program's whole lifetime, which is why its type is &'static str."),
             ("Try it", "Call first_label with an empty label and with a nonempty label. For each call, predict "
              "which path runs and which variant it returns.")),
            "fn first_label(label: &str) -> Result<&str, &'static str> {\n"
            '    if label.is_empty() {\n        Err("empty label")\n    } else {\n        Ok(label)\n    }\n}',
            (("The Rust Book · Match", BOOK + "ch06-02-match.html"),
             ("The Rust Book · Recoverable Errors with Result", BOOK + "ch09-02-recoverable-errors-with-result.html")),
            (("Compare", "== != < <= > >= produce bool."), ("Choose", "if condition { ... } else { ... }"),
             ("Match", "pattern => expression · _ covers remaining cases."),
             ("Result", "Ok(value) is success. Err(reason) reports a recoverable failure."))),
    Chapter("data", "Structured data, borrowing, and lists", "Group related values and share access to them with functions.",
            (("Structs", "A struct gives related pieces of data a name and each field its own type. A struct for a task "
              "might have a String label and a bool that records completion."),
             ("References", "A shared reference lets a function read a value while its owner keeps it. An exclusive "
              "reference, written &mut, lets a function change the borrowed value. The borrow ends before the owner "
              "uses the value again."),
             ("Lists and slices", "A Vec owns a growing list. A slice borrows a contiguous portion of a list. For example, "
              "&[i32] lets a function work with a list of integers without taking it over."),
             ("Try it", "Create two items in a vector. Borrow the first one, change its completion flag, and print both "
              "items after the borrow ends. Explain which value changed and who still owns it.")),
            "struct Task {\n    label: String,\n    done: bool,\n}\n\n"
            "fn finish(task: &mut Task) {\n    task.done = true;\n}",
            (("The Rust Book · Defining and Instantiating Structs", BOOK + "ch05-01-defining-structs.html"),
             ("The Rust Book · References and Borrowing", BOOK + "ch04-02-references-and-borrowing.html"),
             ("The Rust Book · Storing Lists of Values with Vectors", BOOK + "ch08-01-vectors.html")),
            (("Read borrow", "&value lends shared access."), ("Change borrow", "&mut value lends exclusive access."),
             ("Slice", "&[T] is a view of a sequence. &text is often usable where &str is expected for a String."),
             ("Fields", "item.done reads a struct field. Changing a field requires mutable access."))),
    Chapter("cargo", "Working in a Rust project", "Create and run a real project outside the lesson editor.",
            (("Ubuntu setup", "Use the official Rust installation guide to set up rustup. Open a new terminal and check "
              "rustc --version and cargo --version. Install a system linker such as the one provided by build-essential "
              "if the Rust guide calls for it or a build reports that cc is missing."),
             ("Open a project", "Install VS Code or VSCodium from its official site and add the rust-analyzer extension. "
              "In a terminal, run cargo new practice. Open the new practice directory in the editor. Cargo.toml describes "
              "the package, and src/main.rs contains the starting program."),
             ("Build, run, and test", "From the project folder, cargo check checks code without producing a runnable binary. "
              "Use cargo run to build and launch it. Use cargo test to execute tests. An assertion compares observed "
              "behavior with what you expected."),
             ("Debug and launch", "Start with a reproducible input and read the first compiler diagnostic or failing test. "
              "You can print intermediate values with dbg! while investigating. To start the program again, run cargo run "
              "from the project folder or invoke the executable from target/debug after a successful cargo build."),
             ("Use a crate", "Find packages on crates.io and read the corresponding version’s API examples on docs.rs. "
              "Start by checking std. If a crate helps, review documentation, supported Rust versions, recent maintenance, "
              "and license. Enter its version requirement under [dependencies] in Cargo.toml and use the documented API.")),
            "cargo new practice\ncd practice\ncargo check\ncargo run\ncargo test",
            (("Official Rust installation", "https://rust-lang.org/tools/install/"),
             ("VS Code on Linux", "https://code.visualstudio.com/docs/setup/linux"),
             ("VSCodium installation", "https://vscodium.com/#install"),
             ("The Cargo Book · First Steps", CARGO + "getting-started/first-steps.html"),
             ("The Cargo Book · Specifying Dependencies", CARGO + "reference/specifying-dependencies.html")),
            (("Create a project", "cargo new practice · open the practice folder containing Cargo.toml."),
             ("Build and run", "cargo check · cargo run · cargo test."),
             ("Dependencies", '[dependencies] in Cargo.toml · itertools = "0.14" · use itertools::Itertools;'),
             ("Keep a version record", "Cargo.lock records the versions Cargo selected."))),
    Chapter("ownership", "Ownership, moves, and copies", "Track who owns a value and when it is dropped.",
            (("Move a value", "Assigning an owned String to another binding transfers ownership. The old name "
              "stops being usable. The String is released when its current owner goes out of scope."),
             ("Copy or borrow", "An i32 implements Copy, so assignment copies it. Use a reference to share access "
              "without moving. Use clone only when you deliberately need a second independent owned value.")),
            'let original = String::from("note");\nlet new_owner = original;\nprintln!("{new_owner}");',
            (("The Rust Book · What Is Ownership?", BOOK + "ch04-01-what-is-ownership.html"),),
            (("Move", "let second = first; moves a String."), ("Copy", "let second = first; copies an i32."),
             ("Lend", "&first borrows the value while its owner remains responsible for it."))),
    Chapter("option", "Enums and Option", "Give related alternatives names and handle every case.",
            (("Variants", "An enum value has one variant at a time. A variant can hold data, as Some(value) does."),
             ("Absence", "Use None for absence. A number such as zero can still be a real value as Some(0)."),
             ("Match", "Match Some(value) to bind its contents. Include a branch for None.")),
            'match readings.last() {\n    Some(value) => println!("{value}"),\n    None => println!("No readings"),\n}',
            (("The Rust Book · Defining an Enum", BOOK + "ch06-01-defining-an-enum.html"),
             ("Standard library · Option", "https://doc.rust-lang.org/std/option/enum.Option.html")),
            (("Optional value", "Option<T> is Some(T) or None."), ("Inspect", "match item { Some(value) => ..., None => ... }"))),
    Chapter("resources", "Learning resources and tools", "Choose a reliable source for the task in front of you.",
            (("Learn a concept", "Use the Rust Book for explanations and Rust by Example for short examples."),
             ("Look up an API", "Use the standard-library docs first. Search crates.io for dependencies and open the "
              "matching version on docs.rs before copying an example."),
             ("Use editor and terminal tools", "rust-analyzer helps navigate code and shows diagnostics. rustfmt "
              "formats code. Clippy gives suggestions to consider alongside your behavior checks."),
             ("Experiment", "Rust Playground can run small public examples online. Use your local editor for private code.")),
            "cargo fmt\ncargo clippy\ncargo test",
            (("The Rust Programming Language", BOOK), ("Rust by Example", "https://doc.rust-lang.org/rust-by-example/"),
             ("Rust standard library", "https://doc.rust-lang.org/std/"), ("The Cargo Book", CARGO),
             ("crates.io registry", "https://crates.io/"), ("docs.rs crate documentation", "https://docs.rs/"),
             ("rust-analyzer manual", "https://rust-analyzer.github.io/book/"),
             ("Clippy documentation", "https://doc.rust-lang.org/clippy/"),
             ("rustfmt project", "https://github.com/rust-lang/rustfmt"),
             ("Rust Playground", "https://play.rust-lang.org/")),
            (("Find", "Rust Book for concepts · Rust by Example for examples · std for built-in APIs."),
             ("Check crates", "crates.io for discovery · docs.rs for the versioned API · review license and maintenance."),
             ("Tools", "cargo fmt formats · cargo clippy suggests improvements · cargo test checks behavior."))),
)

LESSONS = (INITIAL_LESSONS[0], *early_lessons(Lesson, Case), *INITIAL_LESSONS[1:], *editor_lessons(Lesson))
COURSES = {"rust": {"title": "Rust", "lessons": LESSONS, "chapters": CHAPTERS,
                   "milestones": (*foundation_milestones(Milestone, question), *ROADMAP),
                   "advanced_milestones": ADVANCED_ROADMAP, "optional_references": (OPTIONAL_FFI,)}}
