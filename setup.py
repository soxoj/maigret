from setuptools import (
    setup,
    find_packages,
)


with open('README.md') as fh:
    long_description = fh.read()
    long_description.replace('./', 'https://raw.githubusercontent.com/soxoj/maigret/main/')

setup(name='maigret',
      version='0.1.0',
      description='Collect a dossier on a person by username from a huge number of sites',
      long_description=long_description,
      long_description_content_type="text/markdown",
      url='https://github.com/soxoj/maigret',
      entry_points={'console_scripts': ['maigret = maigret.cli:run']},
      packages=find_packages(),
      author='Soxoj',
      author_email='soxoj@protonmail.com',
      license='MIT',
      zip_safe=False)
