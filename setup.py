from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in life_slimming/__init__.py
from life_slimming import __version__ as version

setup(
	name="life_slimming",
	version=version,
	description="Life slimming",
	author="swathi",
	author_email="swathi.bollineni27@caratred.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
