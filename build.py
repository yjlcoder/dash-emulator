#   -*- coding: utf-8 -*-
from pybuilder.core import use_plugin, init, Project

use_plugin("python.core")
use_plugin("python.unittest")
use_plugin("python.flake8")
use_plugin("python.coverage")
use_plugin("python.distutils")
use_plugin("python.install_dependencies")

name = "dash-emulator"
default_task = "publish"


@init
def set_properties(project: Project):
    project.depends_on_requirements('requirements.txt')
    project.set_property('coverage_threshold_warn', 0)
