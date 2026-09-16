"""Local launcher: registers this hyphenated folder as the importable
package `ad_spy_agent` so the relative imports work, then starts the worker."""
import importlib.util
import os
import sys

PKG_DIR = os.path.dirname(os.path.abspath(__file__))

spec = importlib.util.spec_from_file_location(
    "ad_spy_agent",
    os.path.join(PKG_DIR, "__init__.py"),
    submodule_search_locations=[PKG_DIR],
)
module = importlib.util.module_from_spec(spec)
sys.modules["ad_spy_agent"] = module
spec.loader.exec_module(module)

from ad_spy_agent.worker import main_loop

main_loop()
