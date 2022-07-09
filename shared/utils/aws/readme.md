## Timeit Utilities

The timeit functionalities provides time logging capabilities as a decorator.

To use the functionality there are 3 functions.

- A decorator `@timeit` to select which function to time
- `print_times()` function to log the times that it takes to run a function and other useful information
- `flush_times()` function that resets the statistics that the system keeps about the functions called


to use the decorator you can just set it on top of any function:

    @timeit
    def function_to_be_timed(arg1, arg2, *, arg_by_name ...):
        ...

This will print a log every time the function is been called, logging the time it took to run the function.

then if we want to log the times.
