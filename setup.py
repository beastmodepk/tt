from setuptools import setup

setup(
    name="declarative_config",
    version="1.0",
    description="declarative config for product listings",
    author="Josh Peters",
    author_email="jpeters@redhat.com",
    packages=['declarative_config'],
    entry_points={
        'console_scripts': [
            'declarative_config=declarative_config.declarative_config:main'
        ],
    },
    install_requires=["Cerberus", "PyGreSQL", "PyYAML"],
    data_files=[
        (
            "",
            [
                "yaml_schema.yaml",
                "declarative_config/declarative_config.py",
                "db_connections.conf",
            ],
        )
    ],
)
