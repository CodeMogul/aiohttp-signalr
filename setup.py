from setuptools import setup, find_packages

setup(
    name='aiosignalr',
    version='0.1',
    packages=find_packages(),

    author='Siddhesh Nachane <@codemogul>',
    author_email='siddhesh.nachane@outlook.com',
    description='Asynchronous Signal R Client Library using asyncio and aiohttp.',
    license='Apache 2',
    keywords='signalr python ',
    url='https://github.com/CodeMogul/aiosignalr-client',
    python_requires='>=3.5.0',
    install_requires='aiohttp>=2.3.6'
)