# Charmlibs

```{toctree}
:maxdepth: 3
:hidden: false

how-to/index
reference/index
```

This is the documentation website for Charm Tech's charm library Python packages.

For guidance on distributing charm libraries as Python packages, check out the {ref}`how to <how-to-python-package>`.

## Pathops

Pathops is a Python library providing
a {doc}`pathlib <python:library/pathlib>`-like interface
for [Juju](https://juju.is/) {ref}`Kubernetes Charms <juju:kubernetes-charm>`
to interact with files in their workload container.
Interaction with remote files is performed via [ContainerPath](pathops.ContainerPath) objects.
A [PathProtocol](pathops.PathProtocol) class is provided for use with type annotations,
and a [LocalPath](pathops.LocalPath) class is provided which implements this protocol for local files.

Available on [PyPI](https://pypi.org/project/charmlibs-pathops). Check out the reference documentation [here](pathops).
