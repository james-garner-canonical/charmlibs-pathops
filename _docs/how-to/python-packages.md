(how-to-python-packages)=
# How to distribute charm libraries

While there are multiple ways to share code between charms,
including {doc}`charmcraft fetch-libs <charmcraft:reference/commands/fetch-libs>`,
this how-to focuses specifically on Python packages.

## When to use a Python package

If your library relies on any dependencies outside the Python standard library and the `ops` package, you should definitely use a Python package.

If a charm library seems like it will be difficult to manage as a single file, this is another strong sign that it should be a Python package.

For any new libraries that are not logically associated with a single charm,
including those that are used by both the charmed machine and Kubernetes versions of a piece of software,
consider if using a Python package will make your life easier.
This is especially likely to be the case if you are sharing multiple modules between machine and Kubernetes versions of a charm,
where the individual modules would not obviously be separate Python packages
-- in this case a single Python package will be easier to manage than multiple (perhaps interdependent) charmcraft libs.

The main case where charmcraft libs are likely to be a good alternative to a Python package is for relations.
In this case, the library is associated with a specific charm,
it is likely to be simple enough for a single file (as a lot of logic likely lives in the related charms),
and there is existing infrastructure and documentation supporting this pattern.
However, if the relation library relies on any additional dependencies,
it would still be better to make it a Python package.

## Naming and namespacing your Python package



## How to distribute your Python package

Distributing your package on PyPI has the most benefits.
However, you may find it useful to begin by distributing your package via a git url during development and internal use.

### PyPI

### Git
