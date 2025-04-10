(how-to-python-package)=
# How to distribute charm libraries

This guide details when and how you should create your charm libraries as Python packages
(as opposed to {doc}`charmcraft-style charm libs <charmcraft:reference/commands/fetch-libs>`).


(when-to-python-package)=
## When to use a Python package

You should use a Python package for your charm library if:

- The library relies on any dependencies other than `ops` and the Python standard library.

- The library will be difficult to manage as a single file.

- The library isn't logically associated with a single charm.

- You need to share modules between the machine and Kubernetes versions of a charm.

For a relation library,
it may still be worthwhile to use a charmcraft lib,
since the library may be associated with a single charm,
and there is existing infrastructure and documentation supporting this pattern.
However, the reasons listed above should take priority even in this case.


(python-package-name)=
## Naming and namespacing your Python package

For charm libraries intended for public use and distributed as Python packages,
the library should be a [namespace package](https://packaging.python.org/en/latest/guides/packaging-namespace-packages/)
using the `charmlibs` namespace.
The distribution package name should be `charmlibs-$libname`,
imported as `from charmlibs import $libname`.

If you have a dedicated repository for the charmlib, we recommend naming it `charmlibs-$libname`.
For repositories containing several libraries, consider `$teamname-charmlibs`.

Do use `charmlibs` namespace if your library is intended for public use.
Don't use the `ops` or `charm` namespaces for your libraries.
It will be easier for charmers to follow your code if the `ops` namespace is reserved for the `ops` package.
Likewise, the `charms` namespace is best left for charmcraft managed libs.

If your library should only be used by your own charms, you don't need to publish it to PyPI.
In this case, you don't need to use the `charmlibs` namespace either,
but feel free to do so if it's helpful.
The next section suggests alternative distribution methods for this case.

````{tip}
To make a namespace package,
nest your package in an empty directory with the namespace name,
in this case `charmlibs`.
For example, the file structure for your library might look like this:
```
src/
  charmlibs/
    $libname/
      __init__.py
      ...
tests/
  unit/
  integration/
pyproject.toml
```
The `charmlibs` folder should not contain an `__init__.py` file.
Likewise, there is no need to install an actual package named `charmlibs`
-- this package does exist on PyPI,
but solely to reserve the package name as a namespace for charm libraries,
and to make charm library documentation easier to find.
````


(python-package-distribution)=
## How to distribute your Python package

Distributing your package on PyPI allows your users to use dependency ranges,
improves discoverability,
and makes it easier for users to install your library.
However, it requires some additional work to publish,
and is most appropriate if your library is intended for public use.
You may find it useful to begin by distributing your package via a git url during development and team internal use.
Using a git dependency
or skipping distribution in favour of packing the local files with your charm
may be appropriate if your library is purely for your own charms,
and is not intended for external users.


(python-package-distribution-pypi)=
### PyPI

To publish your library on PyPI,
set up [trusted publishing](https://docs.pypi.org/trusted-publishers/) on PyPI,
and create a Github workflow triggered by a version tag.
For example:

<!-- TODO: use exact commits hashes in this workflow example -->
```yaml
# .github/workflows/publish.yaml
on:
  push:
    tags:
      - 'v*.*.*'
jobs:
  build-n-publish:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv build
      - uses: pypa/gh-action-pypi-publish@release/v1
```

Make sure that your repository only allows trusted contributors write access.
The team manager and another truster team member should be the package owners on PyPI,
using their Canonical email addresses.
Make sure to also claim your package on [Test PyPI](https://test.pypi.org/),
and setup a workflow for publishing there.
All team members can be owners on Test PyPI.

A major benefit of publishing on PyPI is that users of your library can specify version ranges in their dependencies.
Therefore, if you’re going to publish on PyPI, we highly recommend that you use semantic versioning for your library.

A non-dev/alpha/beta/etc qualified 1.x release to PyPI signifies that your library is ready for public consumption.
You should also communicate this through the ["Development Status" Trove classifier](https://pypi.org/classifiers/) in your `pyproject.toml`.


(python-package-distribution-git)=
### Git

You can get started by distributing your library as a Python package with very little friction using GitHub.
This is good for prototyping, or when first transitioning from a charmcraft-style library to a Python package,
and may be a good fit for libraries that are intended for team-internal use.
Once you’re done prototyping and the library is ready for external users, you’ll want to start using PyPI instead.

Git dependencies are limited in that they don’t allow for sophisticated dependency resolution.
You can only specify an exact reference (tag, commit, or branch).
You can’t specify a version range.
This is problematic if your library has dependencies,
as having to request a specific version of your library makes it more likely that any dependency clashes will require manual intervention.
It becomes even more problematic if your library may be depended on by other charm libraries.
Requesting an exact hash or a branch tip may be sufficient for team-internal projects and prototyping,
but proper versioning support is critical when sharing your library more widely,
which will require promoting your package to PyPI.
Tools that scan for security vulnerabilities may also struggle with such dependencies.

You’ll need to include `git` in your charm’s build dependencies to use a GitHub-hosted library in your charm:

```yaml
parts:
  charm:
    build-packages: [git]
```

Then you can specify the dependency in your requirements like this:

```
ops @ git+https://github.com/canonical/operator@main
```

You can specify any branch, tag, or commit after the `@`.
If you leave it off, it will default to `@main`.

If your package is in a subdirectory of your repository
(for example if you use a monorepo,
or collect your libraries into a single repository
-- or if you’re just developing in an existing repository while prototyping):

```
ops-testing @ git+https://github.com/canonical/operator@main#subdirectory=testing
```

In `pyproject.toml`, quote the entire string above in your dependencies list,
or use `uv add git+...` to have `uv` add `charmlibs-pathops` to your dependencies list,
and the git referece to `tool.uv.sources`.
For `poetry` see [here](https://python-poetry.org/docs/dependency-specification/#git-dependencies).


(python-package-distribution-local)=
### Local Files

If you're developing a Python package in the same repository as your charm(s),
it may be simplest to skip distribution and use the local files when packing the charm.
This way, assuming a freshly checked out copy of the repository,
the git commit fully specifies the contents of both your charm code and the package.
For example, if you had the following structure:

```
$repo/
    $charm/
        src/charm.py
        pyproject.toml
    $package/
        src/charmlibs/$libname/__init__.py
        pyproject.toml
```

Then you could leave `$package` out of your `$charm/pyproject.toml` during development.
When it comes time to pack `$charm` for release or integration testing, you could do something like this:

```bash
cd $repo
cp -r ./$charm ./pack-$charm
cp -r ./$package ./pack-$charm/
cd ./pack-$charm
uv add ./$package
charmcraft pack
```

To provision virtual environments for development (including linting and unit testing) we can use editable installs.
For a `$repo` wide virtual environment for conveniently working on both `$package` and `$charm`, you could do this:
```bash
cd $repo
uv venv
uv pip install -e ./$charm -e ./$package
```
Using editable installs ensures that the virtual environment reflects all changes made to either `$charm` or `$package`.
You can then point your editor to the python interpreter in `.venv`, or [activate it manually](https://docs.python.org/3/library/venv.html#how-venvs-work).
To create a virtual environment with a specific python version, use the `--python` flag or define it in a `$repo` level `pyproject.toml`.
If you take this approach, a `$repo` level `pyproject.toml` is a good place to put your common dev dependencies like `ruff` and `codespell`.
You can remove the created `.venv` directory to start afresh.

If you wanted a virtual environment for `$charm` specifically, you could do:
```bash
cd $charm
uv sync  # install deps from $charm/pyproject.toml
uv pip install -e ../$package
```
Since `$package` doesn't depend on `$charm`, its development virtual environment doesn't require any special commands, just a `uv sync`.

The approach should be the same if you have multiple charms, (for example `$charm-kubernetes` and `$charm-machine`), or multiple packages.


(python-package-deps)=
## Dependencies

Your library is not required to depend on `ops`.
If you do require `ops` as a dependency, specify `ops>=2.X,<3`,
where 2.X is the lowest `ops` version that you support,
and 3 is the next major version of `ops`,
protecting your library from breaking changes.
When creating a new library, it’s fine to declare the latest `ops` release as the minimum supported version,
as charms are encouraged to always use the latest version of `ops`.

For other dependencies, ideally follow a similar approach:
`>=` the lowest version that you need, `<` the next potential (or actual) breaking version.
Keeping these dependencies permissive increases the number of charms that will be able to use your library.
