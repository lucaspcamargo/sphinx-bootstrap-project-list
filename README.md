# Sphinx Bootstrap Project List

A tool for generating a Bootstrap-themed list of projects by consuming JSON data and rendering it through a customizable template.

## About

This project takes a JSON data source describing multiple projects and generates an OK-looking, Bootstrap-styled HTML list. This is what powers the project lists of my/this site. Talk about meta stuff.

## Features

- **JSON Data Source**: Specify the path or URL to your JSON file containing project information.
- **Images**: Meant to be used with images. Falls back to a global placeholder if not provided. Supports automatic thumbnail generation for large images (requires Pillow).
- **Internal or External Links**: Add external links or resources to each project entry.
- **Text Fallback**: Fallback to a list of links on non-HTML output.
- **Tech Stack Tags**: Optional `tech` array per project, rendered inline next to the last-updated date.

## Usage

To use the Sphinx Bootstrap Project List, add the following directive to your reStructuredText file:

```rst
.. bspl::
    :json: projects.json
```

More options to come, patches welcome always.

### Example JSON File

Below is an example `projects.json` file. The JSON is a dictionary where each key is a project ID, and the value is the project data:

```json
{
  "alpha": {
    "nice_title": "Project Alpha",
    "descr": "A sample project for demonstration.",
    "index_path": "https://github.com/example/project-alpha",
    "last_mod": "2025-08-03T03:41:52Z",
    "last_mod_fmt": "August 03, 2025",
    "tech": ["C++", "CMake"]
  },
  "beta": {
    "nice_title": "Beta Tool",
    "descr": "Another example project.",
    "index_path": "projects/beta.md",   
    "image_path": "projects/beta_logo.png",
    "last_mod": "2025-07-15T14:22:10Z",
    "last_mod_fmt": "July 15, 2025",
    "tech": ["Python", "Sphinx"]
  }
}
```

Paths are relative to the json file location, unless absolute. Can be a reference to another document, or a full url as well.

## Configuration

Add any of the following to your `conf.py`:

```python
bspl_default_image = '_static/default_project_image.png'
bspl_max_thumb_size = 400
```

- `bspl_default_image`: Path or URL to a fallback image for projects without a specified `image_path`.
- `bspl_max_thumb_size`: Maximum pixel size (in either dimension) before a thumbnail is generated. Defaults to `400`. Set to `0` to disable. Thumbnails are cached in a `.bspl_thumbs/` directory next to the JSON file and reused across builds. SVGs and remote images are never resized.

### Thumbnail generation

Thumbnail generation requires [Pillow](https://python-pillow.org/). Install it alongside the extension:

```
pip install sphinx-bootstrap-project-list[thumbs]
```

Or add `Pillow` directly to your project's dependencies. If Pillow is not installed, images are used as-is and a warning is printed at build time.

More options to come in the future, patches always welcome.

## License

This project is licensed under the GPL v3 License. See the LICENSE file for details.
