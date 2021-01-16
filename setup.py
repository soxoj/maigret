from setuptools import (
    setup,
    find_packages,
)


with open('README.md') as fh:
    readme = fh.read()
    long_description = readme.replace('./', 'https://raw.githubusercontent.com/soxoj/maigret/main/')

with open('requirements.txt') as rf:
    requires = rf.read().splitlines()

setup(name='maigret',
      version='0.1.11',
      description='Collect a dossier on a person by username from a huge number of sites',
      long_description=long_description,
      long_description_content_type="text/markdown",
      url='https://github.com/soxoj/maigret',
      install_requires=requires,
      entry_points={'console_scripts': ['maigret = maigret.maigret:run']},
      packages=find_packages(),
      include_package_data=True,
      author='Soxoj',
      author_email='soxoj@protonmail.com',
      license='MIT',
      zip_safe=False)
