"""Authored project paths with a serializable lesson-page format."""

FOCUSES = {
    "organize": "Keep track of items or tasks",
    "calculate": "Calculate or summarize values",
    "text": "Clean up or transform text",
}

MATERIAL = {
    "organize": (
        ("Model one item", "Structs give related values a shared name. Begin with one text label and one boolean "
         "that records the item's state. The label and state can change independently.",
         'struct Item {\n    label: String,\n    done: bool,\n}',
         ("List two facts the app needs to remember about one item.",
          "Rename the fields to fit your project. Create two sample items in main and print their labels.")),
        ("Store items and update a state", "A Vec holds a list that can grow. A mutable borrow such as &mut Item "
         "lets a function update an existing value. The caller keeps ownership of the item.",
         "fn finish(item: &mut Item) {\n    item.done = true;\n}",
         ("Start with a vector of two items. Write a function that marks one item as complete.",
          "Print the list before and after the change. Verify the other item kept its original state.")),
        ("Verify item changes", "A user might refer to an item that does not exist. Vec::get_mut returns an Option "
         "that lets your program check whether the requested position exists before changing it.",
         'if let Some(item) = items.get_mut(index) {\n    finish(item);\n} else {\n    println!("No item at that position.");\n}',
         ("Try an existing position and a position outside the list.",
          "Write a test that completing one item leaves another item untouched.")),
    ),
    "calculate": (
        ("Represent a measurement", "Give numbers meaningful names and settle on a unit before doing arithmetic. "
         "For a small tool, you can represent whole units with a signed integer and use the same type in your functions.",
         "fn add_units(previous: i32, amount: i32) -> i32 {\n    previous + amount\n}",
         ("Name the values your project accepts and state their units.",
          "Try your function with a normal value, a zero, and a negative number if your project allows it.")),
        ("Summarize several values", "A slice borrows a sequence of values. A loop can read each value and update "
         "an accumulator. Predict the accumulator after each iteration to see how the summary is built.",
         "fn total(values: &[i32]) -> i32 {\n    let mut sum = 0;\n    for value in values {\n        sum += *value;\n    }\n    sum\n}",
         ("Collect three example values for your project and calculate the expected result by hand.",
          "Run your program with the same values, then remove every value and decide what the tool should report.")),
        ("Handle invalid values", "User input arrives as text. Parsing turns text into a number or returns an error. "
         "Handle the two outcomes before using the number in a calculation.",
         'match input.trim().parse::<i32>() {\n    Ok(value) => println!("{value}"),\n    Err(_) => println!("Enter a whole number."),\n}',
         ("Try a valid number, a blank input, and a word. Give the user a useful message for bad input.",
          "Test the result for a short, fixed list whose expected result you already know.")),
    ),
    "text": (
        ("Work with a piece of text", "A string slice, written &str, lets a function read text without owning it. "
         "The trim method returns a slice that omits leading and trailing whitespace.",
         "fn trimmed(text: &str) -> &str {\n    text.trim()\n}",
         ("Write one example of your project's input and desired output.",
          "Make a function perform just one change. Check that it gives the expected result on that example.")),
        ("Apply the change line by line", "Text can become a sequence of lines. A loop that handles one line at "
         "a time makes it easy to see which transformation produced each piece of output.",
         'for line in input.lines() {\n    println!("{}", trimmed(line));\n}',
         ("Create a short input with three lines drawn from your project idea.",
          "Print each result and decide whether your tool should retain or skip empty lines.")),
        ("Check unusual text", "A useful text tool has defined behavior for text that is empty or contains "
         "accented characters. Test those cases before building more features.",
         '#[test]\nfn keeps_accents() {\n    assert_eq!(trimmed("  café  "), "café");\n}',
         ("Add cases for blank text, leading whitespace, and an accented word.",
          "Run cargo test and use the first failure to decide which expectation or function to revise.")),
    ),
}

STAGES = (
    ("Represent the core data", ("types", "functions"), "functions", "A small Rust program that models one believable input."),
    ("Build the first useful behavior", ("borrowing", "control flow"), "data",
     "A command-line prototype that processes a small, known example."),
    ("Handle edge cases and verify the result", ("error handling", "tests"), "branches",
     "A repeatable way to run the prototype and check its normal and invalid inputs."),
)


def project_idea(idea, focus):
    idea = idea.strip()
    if not idea or len(idea) > 180:
        raise ValueError("Describe your idea in 1–180 characters.")
    if focus not in FOCUSES:
        raise ValueError("Choose what the first version should do.")
    return idea


def propose_path(idea, focus):
    idea = project_idea(idea, focus)
    pages = []
    for index, (stage, detail) in enumerate(zip(STAGES, MATERIAL[focus], strict=True), start=1):
        goal, concepts, reference, milestone = stage
        title, explanation, example, practice = detail
        pages.append({
            "id": f"project-{index}",
            "title": title,
            "goal": goal,
            "concepts": list(concepts),
            "explanation": explanation,
            "example": example,
            "steps": list(practice),
            "milestone": milestone,
            "reference": "data" if index == 1 and focus in {"organize", "text"} else reference,
        })
    return {"schema": 1, "idea": idea, "focus": focus, "pages": pages, "completed": []}


def propose_roadmap_path(idea, focus, stage, topics, extension):
    idea = project_idea(idea, focus)
    pages = [
        {"id": f"project-{topic.id}", "skill": topic.id, "skill_title": topic.title,
         "goal": topic.goal, "reference": "resources", "checks": list(topic.checks),
         "quick_reference": topic.quick_reference}
        for topic in topics
    ]
    return {"schema": 2, "idea": idea, "focus": focus, "milestone": stage.id,
            "prerequisite": stage.prerequisite, "extension": extension, "pages": pages, "completed": []}


def remedial_pages(key, item, *, authored):
    if authored:
        explanation = item.explanation
        example = f"{item.example_description} {item.walkthrough[0][1]}"
        code = item.example
        hint = item.hints[0]
        if item.cases:
            case = item.cases[-1]
            arguments = ", ".join(case.arguments)
            exercise = (f"Predict what your exercise should do for {arguments}, then run the lesson checks."
                        if arguments else "Choose a new greeting, predict the line it will print, then run the lesson checks.")
            criterion = ("The selected case agrees with your prediction and the lesson checks."
                         if arguments else "Your program prints one nonempty line in your own words.")
        else:
            exercise = "Try the last case in your Cargo project. Record what you observe before changing your code."
            criterion = item.editor_checks[-1]
    else:
        explanation, code = item.goal, ""
        example = f"Trace the ordinary case before editing. {item.checks[0]}"
        hint = item.quick_reference
        exercise = "Try the boundary case in your Cargo project. Predict the outcome before running it."
        criterion = item.checks[-1]
    return [
        {"id": f"{key}-trace", "title": f"Trace an example · {item.title}",
         "explanation": explanation, "example": example, "example_code": code,
         "exercise": "Trace a value from its input to the result. Predict what would change with a different input.",
         "hint": hint, "checks": ["State your prediction and explain how the example produces its result."]},
        {"id": f"{key}-try", "title": f"Try a small variation · {item.title}",
         "explanation": explanation, "example": example, "example_code": "",
         "exercise": exercise, "hint": hint, "checks": [criterion]},
    ]
