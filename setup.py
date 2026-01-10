from setuptools import setup

# Leer README para la descripción larga
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="zram-swap-manager-pro",
    version="1.0.0",
    author="Aegis Project",
    description="Gestor profesional de Zram y Swap para Linux con GUI moderna",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/a94752568-ux/zram-swap-manager",
    # Se listan los módulos individuales ya que la estructura es plana
    py_modules=["zram_swap_manager", "system_manager", "views", "config", "utils", "optimizer"],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Topic :: System :: Systems Administration",
    ],
    python_requires=">=3.8",
    install_requires=[
        "customtkinter>=5.0.0",
        "psutil>=5.9.0",
        "matplotlib>=3.0.0",
    ],
    entry_points={
        "console_scripts": [
            "zram-pro=zram_swap_manager:main",
        ],
    },
)