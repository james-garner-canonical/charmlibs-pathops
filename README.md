# charmtech-charmlibs

This monorepo hosts the source code for Charm Tech's Python package charm libraries.
Currently the only library hosted here is [pathops](pathops/README.md).

# Contributing

This project uses [just](https://github.com/casey/just) as a task runner, backed by [uv](https://github.com/astral-sh/uv).

Consider installing them both like this:

```bash
sudo apt install pipx
pipx install uv
uv tool install rust-just
```

Then run `just` in this project for usage.
