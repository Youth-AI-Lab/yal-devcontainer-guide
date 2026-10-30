# The guide, followed by a machine

The workflow [`guide.yml`](../.github/workflows/guide.yml) follows the Linux part of this guide on a
fresh machine of GitHub, at each change and every Monday (the Dev Containers tools and Docker change
without us), for each of the three repositories that use the image of the workshops.

| System | State |
|---|---|
| Linux (Ubuntu 24.04 and 26.04) | tested by the workflow, from part 1 step 2 (Docker is already installed on GitHub's machines); green on GitHub on 29 October 2026 for the three repositories |
| macOS | not possible here: GitHub's macOS machines cannot run Docker; to test by hand |
| Windows | not possible here: GitHub's Windows machines have no Docker Desktop; to test by hand |

## How it works

**The commands of the guide** run as they are written in [`README.md`](../README.md). A marker, an
HTML comment that GitHub does not show, says which code blocks to run, and what the reader should
see:

```html
<!-- ci linux stage=cli check="devcontainer --version" expect="0.89.0" -->
```

- `linux`: the version of the guide this block belongs to;
- `stage=`: [`run_guide.py`](run_guide.py) runs the blocks of one stage in order, in one shell, as in
  one terminal: `check` (Docker and `iptable_nat`, part 1), `cli` (the command line, part 3), `open`
  (download and open a repository), `inside` (a command in the container), `delete` (part 7);
- `check="..."`: a command that the text asks the reader to type after the block;
- `expect="..."`: a text that the output must contain ("What you should see").

Only one thing changes in the commands (`SUBSTITUTIONS` in `run_guide.py`): the guide opens the
workshop kit and says "for a workshop or a guide, change the name of the repository"; `CI_REPO` does
it, so the workflow opens six of the nine repositories: workshops 1 and 5 (the smallest and the largest),
the kit, and the three guides.

After `inside`, the workflow waits for the Docker inside the container (it starts a
few seconds after the container), then checks that it runs a container: the steps in VS Code's
windows are not checked, but this is what `openwebui` needs.

To run the stages by hand, give them the same `CI_WORKDIR` (`export CI_WORKDIR=$(mktemp -d)`), so that
`inside` and `delete` find what `open` downloaded. The stage `check` needs `sudo` without a password.

## When you change the guide

- **A command**: change it in `README.md`; the workflow runs the new one. Keep the marker just before
  its code block.
- **A new block to run**: add a marker before it.

## What it does not check

The install of Docker and VS Code (part 1, steps 1 and 4), the steps in VS Code's windows, macOS,
Windows, `openwebui start` with a key, and a group on a network. Check these by hand on a real
computer, as in the [About](../README.md#about) section.

> [!NOTE]
> The stage `delete` deletes only the container, the volume and the copy of the image of the
> repository it opened (by its folder), then the image of the workshops: no other container.
