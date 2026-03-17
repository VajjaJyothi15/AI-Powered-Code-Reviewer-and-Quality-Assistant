"""Module description."""

def generator_example(n):
    """Generates a sequence of integers from ``0`` up to ``n - 1``.
    
    Args:
        n (int): The number of integers to generate. Must be a non‑negative integer.
    
    Yields:
        int: The next integer in the sequence, starting at ``0`` and ending at ``n - 1``.
    
    Raises:
        TypeError: If ``n`` is not an integer.
        ValueError: If ``n`` is negative.
    """
    for i in range(n):
        yield i


def raises_example(x):
    """Compute description.
    
    Args:
        x (int): The input value.
    
    Returns:
        int: The input value multiplied by two.
    
    Raises:
        ValueError: If `x` is negative.
    """
    if x < 0:
        raise ValueError("negative")
    return x * 2


def greet(name: str, title: str | None = None) -> str:
    """Returns a greeting string.
    
    Args:
        name (str): The name of the person to greet.
        title (str, optional): An optional title to prepend to the name. If omitted or ``None``, only the name is used.
    
    Returns:
        str: A greeting message formatted as ``"Hello {title} {name}"`` when a title is provided, otherwise ``"Hello {name}"``.
    
    Raises:
        None: This function does not raise any exceptions.
    """
    if title:
        return f"Hello {title} {name}"
    return f"Hello {name}"


def is_even(n: int) -> bool:
    """Return ``True`` if the given integer is even, otherwise ``False``.
    
    Args:
        n (int): The integer to evaluate.
    
    Returns:
        bool: ``True`` if ``n`` is even, ``False`` otherwise.
    
    Raises:
        TypeError: If ``n`` is not an instance of ``int``.
    """
    return n % 2 == 0
