def generator_example(n):
    for i in range(n):
        yield i


def raises_example(x):
    if x < 0:
        raise ValueError("negative")
    return x * 2


def greet(name: str, title: str | None = None) -> str:
    """Return a greeting."""
    if title:
        return f"Hello {title} {name}"
    return f"Hello {name}"


def is_even(n: int) -> bool:
    """Return True if n is even."""
    return n % 2 == 0
