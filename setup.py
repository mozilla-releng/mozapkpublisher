import os
from setuptools import setup, find_packages

project_dir = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(project_dir, 'version.txt')) as f:
    version = f.read().rstrip()

# We're using a pip style requirements file, which allows us to embed hashes
# of the packages in it. However, setuptools doesn't support parsing this type
# of file, so we need to strip those out before passing the requirements along
# to it.
with open(os.path.join(project_dir, 'requirements.txt')) as f:
    requirements = [
        line.split()[0]
        for line in f
        if not (line.startswith('#') or '--hash=' in line)
    ]

setup(
    name='mozapkpublisher',
    version=version,
    description='Scripts to get and push Firefox for Android to Google Play Store',
    author='Mozilla Release Engineering',
    author_email='release+python@mozilla.com',
    url='https://github.com/mozilla-releng/mozapkpublisher',
    packages=find_packages(),
    license='MPL2',
    install_requires=requirements,
    classifiers=(
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 3',
    ),
)
