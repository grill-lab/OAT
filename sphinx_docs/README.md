# OAT Sphinx documentation

This container generates HTML documentation for OAT based on docstrings in the source code. It relies on the widely used [Sphinx](https://www.sphinx-doc.org/en/master/) package.

Currently it should build documentation for:
 * external_functionalities
 * functionalities
 * neural_functionalities
 * orchestrator
 * shared 
 * offline

Sphinx can generate basic outlines of packages/modules/methods, but it's much more effective when there are docstrings in the code that can be extracted and shown in the HTML pages. For this to work well there needs to be a consistent style for docstrings across the system. I'd suggest we use the [Google style](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html), so for example if you're documenting a typical method it would look like this:


```python
 def example_method(self, param1, param2):
    """Class methods are similar to regular functions.

    Note:
        Do not include the `self` parameter in the ``Args`` section.

    Args:
        param1: The first parameter.
        param2: The second parameter.

    Returns:
        True if successful, False otherwise.

    """
    return True
```

Docstrings can also be added to modules and classes, see the style guide link for more examples!

## Instructions

Build as usual:
```bash
docker compose build sphinx_docs
```

Running with the default parameters:

```bash
docker compose run sphinx_docs
```

Cleaning and building:
```bash
docker compose run sphinx_docs clean html
```

To view the generated documentation go to `sphinx_docs/_build/html/index.html`.
