from sphinx.application import Sphinx
from sphinx.util.docutils import SphinxDirective
from sphinx.addnodes import toctree as TocTreeNode
from docutils import nodes
from docutils.parsers.rst import directives
from docutils.writers.html5_polyglot import HTMLTranslator as html_translator
from jinja2 import Template
from importlib.resources import files
import json
import posixpath
import urllib.parse as urlparse
import os

__title__= 'sphinx-bootstrap-project-list'
__license__ = 'GPLv3'
__version__ = '1.0'
__author__ = 'Lucas Pires Camargo'
__url__ = 'https://camargo.eng.br'
__description__ = 'Sphinx extension for rendering nice-looking project lists using Bootstrap 5'
__keywords__ = 'documentation, sphinx, extension, bootstrap, html'

_THUMB_CACHE_DIR = '.bspl_thumbs'
_SKIP_EXTENSIONS = {'.svg', '.gif'}


def _make_thumb(src_path, max_size, cache_dir):
    """Return a path to a thumbnail of src_path, generating one if the image exceeds max_size.

    Returns src_path unchanged if the image is already small enough, is an
    unsupported format, or if Pillow is unavailable.
    """
    ext = os.path.splitext(src_path)[1].lower()
    if ext in _SKIP_EXTENSIONS:
        return src_path

    try:
        from PIL import Image
    except ImportError:
        print("[bspl] Pillow not installed, skipping thumbnail generation")
        return src_path

    try:
        with Image.open(src_path) as img:
            w, h = img.size
            if w <= max_size and h <= max_size:
                return src_path

            scale = max_size / max(w, h)
            new_w, new_h = int(w * scale), int(h * scale)

            os.makedirs(cache_dir, exist_ok=True)
            base = os.path.splitext(os.path.basename(src_path))[0]
            thumb_name = f"{base}_thumb_{new_w}x{new_h}{ext}"
            thumb_path = os.path.join(cache_dir, thumb_name)

            if not os.path.exists(thumb_path):
                img_resized = img.resize((new_w, new_h), Image.LANCZOS)
                save_kwargs = {}
                if ext in {'.png'}:
                    save_kwargs = {'compress_level': 9}
                elif ext in {'.jpg', '.jpeg'}:
                    save_kwargs = {'quality': 95, 'optimize': True}
                img_resized.save(thumb_path, **save_kwargs)
                print(f"[bspl] generated thumbnail {thumb_path} ({w}x{h} -> {new_w}x{new_h})")

            return thumb_path
    except Exception as e:
        print(f"[bspl] Warning: could not generate thumbnail for {src_path}: {e}")
        return src_path


class BSPLNode(nodes.General, nodes.Element):

    @staticmethod
    def html_visit(translator:html_translator, node):
        """
        Visit method for rendering the BSPLNode content.
        This method is called when the node is being processed for HTML output.
        It extracts project information from the node's children and renders it using a Jinja2 template.
        """
        projects=node.get('projects', {})

        # go over child nodes and extract image and link uris
        # store in projects dict
        for child in node.children:
            if isinstance(child, nodes.image):
                olduri = child['uri']
                if olduri in translator.builder.images:
                    child['uri'] = posixpath.join(
                        translator.builder.imgpath, urlparse.quote(translator.builder.images[olduri])
                    )
                proj_key = child.get('proj_key', None)
                if proj_key and proj_key in projects:
                    projects[proj_key]['image_path_rel'] = child['uri']
                    projects[proj_key]['image_alt'] = child.get('alt', 'Project Image for ' + proj_key)
                else:
                    print("[bspl] Warning: image node with proj_key", proj_key, "not found in projects dict")
            elif isinstance(child, nodes.TextElement) and len(child.children) == 1 and isinstance(child.children[0], nodes.reference):
                refnode = child.children[0]
                proj_key = refnode.get('proj_key', None)
                if proj_key and proj_key in projects:
                    projects[proj_key]['index_url'] = refnode['refuri']
                    projects[proj_key]['nice_title'] = refnode.astext()
                else:
                    print("[bspl] Warning: reference node with proj_key", proj_key, "not found in projects dict")
            else:
                print("[bspl] Warning: unhandled child node type", type(child), "in BSPLNode.html_visit")


        template_path = files(__package__).joinpath("templates/project_list.j2")
        template_path = str(template_path)
        with open(template_path, "r", encoding="utf-8") as f:
           template_str = f.read()
        template = Template(template_str)
        translator.body.append(
            template.render(
                projects=projects))

        # ignore children and don't even depart node
        # we are done
        raise nodes.SkipNode

    @staticmethod
    def html_depart(translator, node):
        raise RuntimeError("BSPLNode.html_depart should not be called, as we raise SkipNode in html_visit.")


def TextualVisit(writer, node):
    # only keep link children, more precisely the wrappers, they shall be rendered as-is
    all_children = list(node.children[:])
    node.children.clear()
    all_text_children = [ch for ch in all_children if isinstance(ch, nodes.TextElement)]
    node.children = all_text_children


def TextualDepart(writer, node):
    pass

class BSPLDirective(SphinxDirective):
    option_spec = {
        'json': str,
        'toctree-caption': directives.unchanged,
        'no-toctree': directives.flag,
    }

    has_content = True

    def run(self):
        env = self.state.document.settings.env
        json_file = self.options.get('json', None)
        if json_file:
            with open(json_file, 'r') as f:
                content = json.load(f)
        else:
            raise ValueError("No JSON file provided in options.")

        content = {k: v for k, v in content.items() if not v.get('hidden')}

        max_thumb_size = env.config.bspl_max_thumb_size
        json_dir = os.path.dirname(json_file)
        thumb_cache = os.path.join(json_dir, _THUMB_CACHE_DIR)

        # initialize image urls
        for k, v in content.items():
            v['image_path_rel'] = None
            v['index_path_rel'] = None
            v['nice_title'] = v.get('nice_title', k)
            v['descr'] = v.get('descr', 'No description available.')
            v['last_mod_fmt'] = v.get('last_mod_fmt', 'Unknown date')
            if 'image_path' not in v:
                v['image_path'] = env.config.bspl_default_image or '/_static/proj_default.png'
            if 'index_path' not in v:
                v['index_path'] = k + '.md'

        node = BSPLNode(content=content)


        # add necessary image and link nodes here
        # during rendering visit, use the generated urls
        for k,v in content.items():
            if 'image_path' in v:
                image_path = v['image_path']
                needs_img_node = True

                if image_path.startswith('http'):
                    # remote URL — use as-is, no pipeline
                    needs_img_node = False
                elif image_path.startswith('/'):
                    abs_image_path = os.path.join(env.srcdir, image_path.lstrip('/'))
                    thumb = _make_thumb(abs_image_path, max_thumb_size, thumb_cache)
                    if thumb != abs_image_path:
                        image_path = thumb  # thumbnail generated, needs pipeline
                    else:
                        # already in _static, reference directly to avoid pipeline collisions
                        needs_img_node = False
                else:
                    abs_image_path = os.path.join(json_dir, image_path)
                    image_path = _make_thumb(abs_image_path, max_thumb_size, thumb_cache)

                v['image_path_rel'] = image_path
                print("[bspl] image_path_rel for", k, "is", v['image_path_rel'], "(img_node:", needs_img_node, ")")
                if needs_img_node:
                    img_node = nodes.image(rawsource=v['image_path_rel'])
                    img_node['uri'] = v['image_path_rel']
                    img_node['alt'] = v.get('image_alt', 'Project Image for ' + k)
                    img_node["proj_key"] = k
                    node.append(img_node)
            if 'index_path' in v:
                index_path = v['index_path']
                if index_path.endswith('.md'):
                    index_path = index_path[:-3] + ".html"
                v['index_path_rel'] = os.path.join(os.path.dirname(json_file), index_path)
                print("[bspl] index_path_rel for", k, "is", v['index_path_rel'])
                link_node = nodes.reference(rawsource=v['index_path_rel'], text=v.get('nice_title', k), refuri=v['index_path_rel'])
                link_node['proj_key'] = k
                wrap_p = nodes.paragraph(proj_key=k)
                wrap_p.append(link_node)
                node.append(wrap_p)

        node['projects'] = content

        if 'no-toctree' in self.options:
            return [node]

        # emit a hidden toctree so Sphinx picks up project pages automatically
        # order matches the template: by last_mod descending
        sorted_items = sorted(content.items(), key=lambda kv: kv[1].get('last_mod', ''), reverse=True)
        toc_entries = []
        for k, v in sorted_items:
            index_path = v.get('index_path', '')
            if not index_path or index_path.startswith('http'):
                continue
            if index_path.endswith('.md'):
                index_path = index_path[:-3]
            abs_doc = os.path.normpath(os.path.join(json_dir, index_path))
            docname = os.path.relpath(abs_doc, env.srcdir).replace(os.sep, '/')
            toc_entries.append((None, docname))

        toc = TocTreeNode()
        toc['parent']       = env.docname
        toc['entries']      = toc_entries
        toc['includefiles'] = [e[1] for e in toc_entries]
        toc['maxdepth']     = 1
        toc['caption']      = self.options.get('toctree-caption', None)
        toc['hidden']       = True
        toc['glob']         = False
        toc['reversed']     = False
        toc['titlesonly']   = False
        toc['numbered']     = 0

        return [toc, node]


def setup(app:Sphinx):
    app.add_config_value("bspl_default_image", None, '')
    app.add_config_value("bspl_max_thumb_size", 400, '')
    app.add_directive('bspl', BSPLDirective)
    app.connect('builder-inited', lambda app: app.config.html_static_path.__iadd__(
        [str(files(__package__).joinpath('static'))]
    ))
    app.add_css_file('bspl.css')
    app.add_node(BSPLNode,
                 html=(BSPLNode.html_visit, BSPLNode.html_depart),
                 text=(TextualVisit, TextualDepart),
                 gemini=(TextualVisit, TextualDepart),
                 latex=(TextualVisit, TextualDepart),
    )

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
