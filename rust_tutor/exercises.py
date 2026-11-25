"""A bounded interpreter for the Rust constructs used in the first milestone.

The parser accepts a small grammar. It never invokes a compiler, shell, or
executable, and its evaluator has no interface to files or the environment.
"""

from dataclasses import dataclass
import json
import re


class ExerciseError(ValueError):
    pass


TOKENS = re.compile(
    r'(?P<space>\s+|//[^\n]*)|(?P<string>"(?:[^"\\\n\r]|\\["\\nrt])*")|'
    r'(?P<integer>[0-9][0-9_]*)|(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)|'
    r"(?P<other>->|=>|==|!=|<=|>=|[+*/%<>=&'!\-(),:;{}])"
)
OPERATORS = {"==": 1, "!=": 1, "<": 1, "<=": 1, ">": 1, ">=": 1,
             "+": 2, "-": 2, "*": 3, "/": 3, "%": 3}
RESERVED = set("as async await break const continue crate dyn else enum extern false fn for if impl in let loop match "
               "mod move mut pub ref return self Self static struct super trait true type unsafe use where while "
               "abstract become box do final gen macro override priv try typeof unsized virtual yield _".split())
MIN_I32 = -(2 ** 31)
MAX_I32 = 2 ** 31 - 1


@dataclass(frozen=True)
class Token:
    value: str
    line: int


def tokenize(source):
    if len(source) > 12_000:
        raise ExerciseError("Keep this exercise under 12,000 characters.")
    tokens = []
    offset = 0
    line = 1
    while offset < len(source):
        token = TOKENS.match(source, offset)
        if token is None:
            raise ExerciseError(f"Line {line}: this character or string is outside the practice editor's Rust subset.")
        if token.lastgroup != "space":
            tokens.append(Token(token[0], line))
        line += token[0].count("\n")
        offset = token.end()
    if len(tokens) > 700:
        raise ExerciseError("Use a shorter program for this exercise.")
    return tokens + [Token("", line)]


def integer(value):
    if type(value) is not int:
        raise ExerciseError("This arithmetic operation expects two i32 integers.")
    if not MIN_I32 <= value <= MAX_I32:
        raise ExerciseError("The result is outside the i32 range.")
    return value


class Parser:
    def __init__(self, source):
        self.tokens = tokenize(source)
        self.position = 0

    @property
    def current(self):
        return self.tokens[self.position]

    def accept(self, value):
        if self.current.value == value:
            self.position += 1
            return True
        return False

    def expect(self, *values):
        for value in values:
            if not self.accept(value):
                self.fail(f"expected {value!r}")

    def fail(self, message):
        raise ExerciseError(f"Line {self.current.line}: {message}.")

    def name(self):
        value = self.current.value
        if not re.fullmatch("[a-zA-Z_][a-zA-Z0-9_]*", value) or value in RESERVED:
            self.fail("expected a variable name")
        self.position += 1
        return value

    def string(self):
        value = self.current.value
        if not value.startswith('"'):
            self.fail("expected a quoted string")
        self.position += 1
        try:
            return json.loads(value)
        except ValueError:
            self.fail("this string escape is outside the practice subset")

    def program(self, lesson_id):
        self.accept("pub")
        if lesson_id == "first-program":
            self.expect("fn", "main", "(", ")", "{")
            lines = []
            while not self.accept("}"):
                self.expect("println", "!", "(")
                value = self.string()
                if "{" in value or "}" in value:
                    self.fail("this exercise accepts plain text in println!")
                lines.append(value)
                self.expect(")", ";")
            self.expect("")
            return (), ("literal", "\n".join(lines))
        function = "add" if lesson_id == "functions" else "calculate"
        self.expect("fn", function, "(")
        parameters = [self.name()]
        self.expect(":", "i32", ",")
        if function == "calculate":
            parameters.append(self.name())
            self.expect(":", "&", "str", ",")
        parameters.append(self.name())
        self.expect(":", "i32")
        self.accept(",")
        self.expect(")", "->")
        if function == "add":
            self.expect("i32")
        else:
            self.expect("Result", "<", "i32", ",", "&", "'", "static", "str", ">")
        if len(parameters) != len(set(parameters)):
            self.fail("each parameter needs a different name")
        body = self.block()
        self.expect("")
        return parameters, body

    def block(self):
        self.expect("{")
        bindings = []
        while self.accept("let"):
            name = self.name()
            self.expect("=")
            bindings.append((name, self.expression()))
            self.expect(";")
        returned = self.accept("return")
        result = self.expression()
        if returned:
            self.expect(";")
        self.expect("}")
        return ("block", bindings, result, returned)

    def expression(self, minimum=1):
        left = self.atom()
        while OPERATORS.get(self.current.value, 0) >= minimum:
            operator = self.current.value
            self.position += 1
            right = self.expression(OPERATORS[operator] + 1)
            left = ("operator", operator, left, right)
        return left

    def atom(self):
        value = self.current.value
        if self.accept("("):
            node = self.expression()
            self.expect(")")
            return node
        if self.accept("-"):
            if self.current.value.replace("_", "").isdigit():
                digits = self.current.value.replace("_", "")
                self.position += 1
                if len(digits) > 10:
                    self.fail("this integer is outside the i32 range")
                return "literal", integer(-int(digits))
            return "negate", self.atom()
        if self.accept("if"):
            condition = self.expression()
            yes = self.block()
            self.expect("else")
            alternative = self.atom() if self.current.value == "if" else self.block()
            return "if", condition, yes, alternative
        if self.accept("match"):
            subject = self.expression()
            self.expect("{")
            arms = []
            while not self.accept("}"):
                pattern = None if self.accept("_") else self.string()
                guard = self.expression() if self.accept("if") else ("literal", True)
                self.expect("=>")
                action = self.block() if self.current.value == "{" else self.expression()
                arms.append((pattern, guard, action))
                if not self.accept(",") and self.current.value != "}":
                    self.fail("expected a comma after this match arm")
            if not any(pattern is None and guard == ("literal", True) for pattern, guard, _ in arms):
                self.fail("include an unguarded _ arm to cover other operators")
            return "match", subject, arms
        if value.startswith('"'):
            return "literal", self.string()
        if value.replace("_", "").isdigit():
            self.position += 1
            digits = value.replace("_", "")
            if len(digits) > 10:
                self.fail("this integer is outside the i32 range")
            return "literal", integer(int(digits))
        if self.accept("true"):
            return "literal", True
        if self.accept("false"):
            return "literal", False
        if value in {"Ok", "Err"}:
            self.position += 1
            self.expect("(")
            item = self.expression()
            self.expect(")")
            return "result", value, item
        return "variable", self.name()


class Returned(Exception):
    def __init__(self, value):
        self.value = value


def is_true(value):
    if type(value) is not bool:
        raise ExerciseError("A condition must evaluate to true or false.")
    return value


def require_type(actual, expected):
    if actual == "&'static str" and expected == "&str":
        return
    if actual not in {expected, "never"}:
        raise ExerciseError(f"Expected {expected} but found {actual}. Check what the expression produces.")


def common_type(left, right):
    if left == "never":
        return right
    if {left, right} == {"&str", "&'static str"}:
        return "&str"
    require_type(right, left)
    return left


def expression_type(node, scope, return_type):
    def infer(child):
        return expression_type(child, scope, return_type)

    match node:
        case ("literal", value):
            return {bool: "bool", int: "i32", str: "&'static str"}[type(value)]
        case ("variable", name):
            if name not in scope:
                raise ExerciseError(f"The name {name!r} is outside the current scope.")
            return scope[name]
        case ("negate", child):
            require_type(infer(child), "i32")
            return "i32"
        case ("operator", symbol, left, right):
            left_type, right_type = infer(left), infer(right)
            if symbol in {"==", "!="}:
                common_type(left_type, right_type)
                return "bool"
            require_type(left_type, "i32")
            require_type(right_type, "i32")
            return "bool" if OPERATORS[symbol] == 1 else "i32"
        case ("block", bindings, result, returned):
            scope = scope.copy()
            for name, child in bindings:
                scope[name] = infer(child)
            result_type = infer(result)
            if returned:
                require_type(result_type, return_type)
                return "never"
            return result_type
        case ("if", condition, yes, no):
            require_type(infer(condition), "bool")
            return common_type(infer(yes), infer(no))
        case ("result", variant, child):
            require_type(infer(child), "i32" if variant == "Ok" else "&'static str")
            return "Result"
        case ("match", subject, arms):
            require_type(infer(subject), "&str")
            result_type = "never"
            for _pattern, guard, action in arms:
                require_type(infer(guard), "bool")
                result_type = common_type(result_type, infer(action))
            return result_type
    raise ExerciseError("This expression is outside the practice subset.")


def operation(symbol, left, right):
    if symbol in {"==", "!="}:
        if type(left) is not type(right):
            raise ExerciseError("Compare values of the same type.")
        equal = left == right
        return equal if symbol == "==" else not equal
    left, right = integer(left), integer(right)
    match symbol:
        case "<":
            return left < right
        case ">":
            return left > right
        case "<=":
            return left <= right
        case ">=":
            return left >= right
        case "+":
            return integer(left + right)
        case "-":
            return integer(left - right)
        case "*":
            return integer(left * right)
    if right == 0:
        raise ExerciseError("Tried to divide by zero. Handle that input in a separate branch.")
    quotient = abs(left) // abs(right)
    if (left < 0) != (right < 0):
        quotient = -quotient
    integer(quotient)
    return quotient if symbol == "/" else left - quotient * right


def evaluate(node, scope):
    match node:
        case ("literal", value):
            return value
        case ("variable", name):
            if name not in scope:
                raise ExerciseError(f"The name {name!r} is outside the current scope.")
            return scope[name]
        case ("negate", child):
            return integer(-integer(evaluate(child, scope)))
        case ("operator", symbol, left, right):
            return operation(symbol, evaluate(left, scope), evaluate(right, scope))
        case ("block", bindings, result, returned):
            local = scope.copy()
            for name, child in bindings:
                local[name] = evaluate(child, local)
            value = evaluate(result, local)
            if returned:
                raise Returned(value)
            return value
        case ("if", condition, yes, no):
            return evaluate(yes if is_true(evaluate(condition, scope)) else no, scope)
        case ("result", variant, child):
            value = evaluate(child, scope)
            if variant == "Err" and type(value) is str:
                return variant, value
            if variant == "Ok":
                return variant, integer(value)
            raise ExerciseError("Err in this calculator expects a string.")
        case ("match", subject, arms):
            value = evaluate(subject, scope)
            if type(value) is not str:
                raise ExerciseError("This exercise expects match to examine the text operator.")
            for pattern, guard, action in arms:
                if pattern in (None, value) and is_true(evaluate(guard, scope)):
                    return evaluate(action, scope)
            raise ExerciseError("No match arm handled the given operator.")
    raise ExerciseError("This expression is outside the practice subset.")


def check(lesson, source, sample=False):
    try:
        parameters, body = Parser(source).program(lesson.id)
        if lesson.id == "functions":
            scope = dict.fromkeys(parameters, "i32")
            require_type(expression_type(body, scope, "i32"), "i32")
        elif lesson.id == "calculator":
            scope = dict(zip(parameters, ("i32", "&str", "i32")))
            require_type(expression_type(body, scope, "Result"), "Result")
        cases = lesson.cases[:1] if sample else lesson.cases
        results = []
        for case in cases:
            arguments = [
                value if lesson.id == "calculator" and i == 1 else int(value)
                for i, value in enumerate(case.arguments)
            ]
            try:
                value = evaluate(body, dict(zip(parameters, arguments)))
            except Returned as result:
                value = result.value
            if lesson.id == "functions":
                value = integer(value)
            if lesson.id == "calculator":
                if not isinstance(value, tuple):
                    raise ExerciseError("Return Ok(number) or Err(reason) from calculate.")
                variant, payload = value
                value = f"Error: {payload}" if variant == "Err" else payload
            results.append((case, str(value)))
        return results
    except RecursionError:
        raise ExerciseError("This expression is nested too deeply for the practice editor.") from None
