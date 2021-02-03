"""Pypi package module namespce wrapper.

We do this automation based importing to take all Epicyon modules in under this
package namespace in one go. This way we do not have to maintain a module list
here just for the Pypi packaging effort and package builds will automatically
pick up new modules as we go forward.
"""

from pathlib import Path
from pkgutil import walk_packages

__all__ = []

package_root = str(Path(".").parent.absolute())

for loader, module_name, is_pkg in walk_packages([package_root]):
    __all__.append(module_name)

    if module_name == "epicyon":
        continue

    _module = loader.find_module(module_name).load_module(module_name)
    globals()[module_name] = _module
