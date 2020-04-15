import setuptools

with open("README.md") as f:
    long_description = f.read()

with open("version.txt", "r", encoding="utf8") as f:
    v_num = f.read().strip()

setuptools.setup(
    name="story-time",
    version=v_num,
    description="Digital Diary written in wxPython",
    packages=setuptools.find_packages(exclude=["docs", "tests"]),
    include_package_data=True,
    package_data={"story_time": ["*.png", "*.txt"],},
    url="https://github.com/chbauman/StoryTime",
    author="Christian Baumann",
    author_email="chris.python.notifyer@gmail.com",
    license="MIT",
    long_description=long_description,
    long_description_content_type="text/markdown",
    python_requires=">=3.6",
    install_requires=["wxPython", "opencv-python", "numpy", "Pillow", "six",],
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
        "Operating System :: OS Independent",
        "Topic :: Utilities",
    ],
    entry_points={"console_scripts": ["story-time=story_time.main:main"],},
)
