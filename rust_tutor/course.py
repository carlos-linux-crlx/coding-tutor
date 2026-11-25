"""The first Rust milestone and its companion reference."""

from dataclasses import dataclass


BOOK = "https://doc.rust-lang.org/book/"
CARGO = "https://doc.rust-lang.org/cargo/"

@dataclass(frozen=True)
class Case:
    arguments: tuple[str, ...]
    expected: str


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
    solution: str
    solution_explanation: str
    flow: tuple[str, str, str]


@dataclass(frozen=True)
class Chapter:
    id: str
    title: str
    summary: str
    sections: tuple[tuple[str, str], ...]
    example: str
    sources: tuple[tuple[str, str], ...]


LESSONS = (
    Lesson(
        "first-program", "Your first Rust program",
        "What happens between writing Rust and seeing a line of output?",
        "A Rust file is source code. The compiler checks it and turns it into an executable. "
        "When you run the executable, Rust enters the function called main. Its instructions execute in order. "
        "Here, println! writes a line to standard output. The exclamation mark identifies it as a macro. "
        "Type the example or change one string and predict what will appear before you run it.",
        'fn main() {\n    println!("The program is running.");\n}',
        "The quoted text is data. The program prints that text without the surrounding quotes.",
        "Make the program print two lines in this order: Hello, Rust! and I wrote my first program. "
        "Use Run to see the output, then Check to compare it with the exercise requirements.",
        'fn main() {\n    println!("Hello!");\n}\n',
        (Case((), "Hello, Rust!\nI wrote my first program."),),
        "execution",
        ("Find the function named main. That is where your two instructions go.",
         "Give println! the exact text for each line, including punctuation.",
         "Add a second println! call under the first. Read the instructions from top to bottom."),
        'fn main() {\n    println!("Hello, Rust!");\n    println!("I wrote my first program.");\n}',
        "Each call writes one line. main executes the first call before the second, so the terminal shows the lines in order.",
        ("Edit the source", "Compile the program", "Read the output"),
    ),
    Lesson(
        "functions", "Values and functions",
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
    ),
    Lesson(
        "calculator", "Build a tiny calculator",
        "How does a program choose an operation and handle a bad request?",
        "A match expression compares a value against patterns in order and evaluates the first matching arm. "
        "Use a final _ arm for input you did not recognize. A Result is either Ok with a value or Err with a reason. "
        "A calculator can use Result to send a number or explain why it could not produce one. "
        "Integer division truncates toward zero, and division by zero needs to be handled before trying the division.",
        'fn operation_name(op: &str) -> &str {\n    match op {\n        "+" => "add",\n        _ => "unknown",\n    }\n}',
        "The value returned depends on the arm that matched. &str is a borrowed view of text.",
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
            (("The Rust Book · Hello, World!", BOOK + "ch01-02-hello-world.html"),)),
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
             ("The Rust Book · Functions", BOOK + "ch03-03-how-functions-work.html"))),
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
             ("The Rust Book · Recoverable Errors with Result", BOOK + "ch09-02-recoverable-errors-with-result.html"))),
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
             ("The Rust Book · Storing Lists of Values with Vectors", BOOK + "ch08-01-vectors.html"))),
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
              "from the project folder or invoke the executable from target/debug after a successful cargo build.")),
            "cargo new practice\ncd practice\ncargo check\ncargo run\ncargo test",
            (("Official Rust installation", "https://rust-lang.org/tools/install/"),
             ("VS Code on Linux", "https://code.visualstudio.com/docs/setup/linux"),
             ("VSCodium installation", "https://vscodium.com/#install"),
             ("The Cargo Book · First Steps", CARGO + "getting-started/first-steps.html"))),
)

QUIZ = (
    ("first-program", "What happens before the executable can print anything?",
     ("The compiler processes the Rust source.", "The executable changes the source file.", "The terminal creates a Rust function."), 0,
     "The compiler checks and translates the source. Printing happens when the resulting executable runs."),
    ("functions", "What supplies the return value in the body { value * 2 }?",
     ("The parameter's type.", "The final expression.", "The name of the function."), 1,
     "The final expression evaluates to a value. In this example Rust returns that value to the caller."),
    ("calculator", "Why should the calculator inspect the divisor before dividing?",
     ("match only works with positive numbers.", "Every answer requires two branches.", "It can report zero as a recoverable error."), 2,
     "With a zero divisor, returning Err gives the caller a meaningful outcome without attempting the division."),
)

COURSES = {"rust": {"title": "Rust", "lessons": LESSONS, "chapters": CHAPTERS, "quiz": QUIZ}}
