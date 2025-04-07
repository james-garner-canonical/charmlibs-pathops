# Charmlibs

```{toctree}
:maxdepth: 3
:hidden: false

reference/index
```

This is the documentation website for Charm Tech's charm library Python packages.

For more information, see also the [git repository](https://github.com/canonical/charmtech-charmlibs).

## Pathops

Pathops is a Python library providing a [pathlib](https://docs.python.org/3/library/pathlib.html)-like interface for [Juju](https://juju.is/) [Kubernetes Charms](https://documentation.ubuntu.com/juju/latest/reference/charm/#kubernetes) to interact with files in their workload container.
Interaction with remote files is performed via ContainerPath objects.
A PathProtocol class is provided for use with type annotations, and a LocalPath class is provided which implements this protocol for local files.
