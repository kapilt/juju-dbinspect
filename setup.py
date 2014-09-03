from setuptools import setup, find_packages

setup(name='juju-dbinspect',
      version="0.1.6",
      classifiers=[
          'Intended Audience :: Developers',
          'Programming Language :: Python',
          'Operating System :: OS Independent'],
      author='Kapil Thangavelu',
      author_email='kapil.foss@gmail.com',
      description="Juju database introspection",
      long_description=open("README.rst").read(),
      url='https://github.com/kapilt/juju-dbinspect',
      license='BSD',
      packages=find_packages(),
      install_requires=["PyYAML", "pymongo"],
      entry_points={
          "console_scripts": [
              'juju-db = juju_dbinspect.cli:main']},
      )
