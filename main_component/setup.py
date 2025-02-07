from setuptools import setup, find_packages

setup(
    name="main_component",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.68.0,<0.69.0",
        "uvicorn>=0.15.0,<0.16.0",
        "python-dotenv>=0.19.0",
        "redis>=4.0.0",
        "pymysql>=1.0.2",
    ],
)
