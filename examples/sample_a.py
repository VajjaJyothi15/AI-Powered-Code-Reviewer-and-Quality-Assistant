"""Sample module A with mixed documentation and complexity."""


def calculate_average(numbers):
    total = 0
    for n in numbers:
        total += n
    if len(numbers) == 0:
        return 0
    return total / len(numbers)


def add(a: int, b: int) -> int:
    return a + b


def subtract(a: int, b: int) -> int:
    """Subtract two numbers."""
    return a - b


def max_of_three(a, b, c):
    """Return the maximum of three values."""
    if a >= b and a >= c:
        return a
    if b >= a and b >= c:
        return b
    return c


def safe_divide(a, b):
    """Divide a by b, returning None for division by zero."""
    if b == 0:
        return None
    return a / b


class Processor:
    def process(self, data):
        for item in data:
            if item is None:
                continue
            print(item)
