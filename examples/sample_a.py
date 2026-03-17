"""Sample module A with mixed documentation and complexity."""


def calculate_average(numbers):
    """Calculate the arithmetic mean of a sequence of numbers.
    
    Args:
        numbers (Iterable[float | int]): An iterable containing numeric values.
    
    Returns:
        float: The arithmetic mean of the provided numbers. Returns 0.0 if the
            iterable is empty.
    
    Raises:
        TypeError: If `numbers` is not iterable or contains non‑numeric elements.
    """
    total = 0
    for n in numbers:
        total += n
    if len(numbers) == 0:
        return 0
    return total / len(numbers)


def add(a: int, b: int) -> int:
    """Add two integers.
    
    Args:
        a (int): First integer operand.
        b (int): Second integer operand.
    
    Returns:
        int: Sum of `a` and `b`.
    
    Raises:
        TypeError: If `a` or `b` is not an instance of `int`.
    """
    return a + b


def subtract(a: int, b: int) -> int:
    """Subtract two integers.
    
    Args:
        a (int): The minuend.
        b (int): The subtrahend.
    
    Returns:
        int: The result of `a - b`.
    
    Raises:
        TypeError: If `a` or `b` is not an integer.
    """
    return a - b


def max_of_three(a, b, c):
    """Return the maximum of three values.
    
    Args:
        a: First value to compare.
        b: Second value to compare.
        c: Third value to compare.
    
    Returns:
        The greatest of the three input values. If multiple values are equal and maximal,
        that value is returned.
    
    Raises:
        TypeError: If the values cannot be compared using the '>=' operator.
    """
    if a >= b and a >= c:
        return a
    if b >= a and b >= c:
        return b
    return c


def safe_divide(a, b):
    """Divides `a` by `b`, returning ``None`` when `b` is zero.
    
    Args:
        a (int | float): Numerator.
        b (int | float): Denominator.
    
    Returns:
        float: The result of ``a / b`` when ``b`` is not zero.
        None: If ``b`` is zero.
    
    Raises:
        TypeError: If ``a`` or ``b`` are not numeric types.
    """
    if b == 0:
        return None
    return a / b


class Processor:
    """Class description."""
    
    def process(self, data):
        """Process the given iterable, printing each non-None item.
        
        Args:
            data (Iterable[Any]): An iterable collection of items to be processed. Items
                that are ``None`` are ignored.
        
        Returns:
            None: This method does not return a value; it performs side‑effects by
            printing each valid item.
        
        Raises:
            TypeError: If ``data`` is not iterable.
        """
        for item in data:
            if item is None:
                continue
            print(item)
